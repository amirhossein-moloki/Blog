"""
EN: Version-based, tag-based, and dependency-graph-based cache invalidation trackers.
FA: ردیاب‌های ابطال کش بر اساس نسخه، برچسب‌های منطقی و گراف وابستگی‌ها بدون استفاده از وایلدکارت.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class InvalidationManager:
    """
    EN: Manages logical cache versions, tags, and dependency graphs.
    FA: مدیریت نسخه‌های منطقی کش، برچسب‌ها و گراف وابستگی‌ها را بر عهده دارد.
    """

    # EN: Dependency graph representation
    # FA: نمایش گراف وابستگی‌ها
    # Example: Homepage depends on latest_articles, popular_articles, categories
    DEPENDENCY_GRAPH: Dict[str, List[str]] = {
        "homepage": ["latest_articles", "popular_articles", "categories"],
        "article_detail": ["comments", "author", "category", "tags"],
    }

    def __init__(self, cache_client: Any) -> None:
        """
        EN: Initializes the InvalidationManager with a cache engine.
        FA: مقداردهی اولیه مدیریت ابطال با یک موتور کش.
        """
        self.cache_client = cache_client

    def _get_version_key(self, group: str) -> str:
        """
        EN: Returns the cache key for storing version information.
        FA: کلید کش مربوط به ذخیره اطلاعات نسخه را بازمی‌گرداند.
        """
        return f"project:v1:sys_version:{group}"

    def _get_tag_key(self, tag: str) -> str:
        """
        EN: Returns the cache key for storing tag version information.
        FA: کلید کش مربوط به ذخیره اطلاعات نسخه تگ را بازمی‌گرداند.
        """
        return f"project:v1:sys_tag:{tag}"

    def get_version(self, group: str) -> int:
        """
        EN: Retrieves the current version of a group, defaulting to 1.
        FA: نسخه فعلی یک گروه را دریافت می‌کند. در صورت عدم وجود، پیش‌فرض ۱ است.
        """
        key = self._get_version_key(group)
        try:
            val = self.cache_client.get(key)
            if val is not None:
                return int(val)
        except Exception as e:
            logger.warning(f"Error getting cache version for group {group}: {e}")
        return 1

    def increment_version(self, group: str) -> int:
        """
        EN: Increments the version of a group. Triggers dependency invalidation.
        FA: نسخه یک گروه را افزایش می‌دهد و ابطال وابستگی‌های آن را آغاز می‌کند.
        """
        key = self._get_version_key(group)
        new_version = 1
        try:
            # EN: Use atomic INCR if Redis, otherwise fallback to read-then-write
            # FA: استفاده از INCR اتمیک در ردیس، در غیر این‌صورت به صورت خواندن و نوشتن دستی
            if hasattr(self.cache_client, "incr"):
                try:
                    new_version = self.cache_client.incr(key)
                except Exception:
                    val = self.cache_client.get(key)
                    new_version = (int(val) if val else 1) + 1
                    self.cache_client.set(key, new_version)
            else:
                val = self.cache_client.get(key)
                new_version = (int(val) if val else 1) + 1
                self.cache_client.set(key, new_version)
        except Exception as e:
            logger.error(
                f"Failed to increment cache version for {group}: {e}", exc_info=True
            )
            new_version = 2  # EN: Safe fallback

        # EN: Invalidate parent dependencies in the graph
        # FA: ابطال وابستگی‌های والد در گراف
        self._invalidate_dependencies(group)
        return new_version

    def get_tag_version(self, tag: str) -> int:
        """
        EN: Retrieves the current version of a logical tag.
        FA: نسخه فعلی یک تگ منطقی را دریافت می‌کند.
        """
        key = self._get_tag_key(tag)
        try:
            val = self.cache_client.get(key)
            if val is not None:
                return int(val)
        except Exception as e:
            logger.warning(f"Error getting tag version for {tag}: {e}")
        return 1

    def get_versions_batch(
        self, group: Optional[str], tags: List[str]
    ) -> Tuple[int, Dict[str, int]]:
        """
        EN: Retrieves group version and all tag versions in a single MGET/get_many round trip.
        FA: نسخه گروه و تمام برچسب‌ها را در یک درخواست دسته‌ای (get_many/MGET) دریافت می‌کند.
        """
        group_key = self._get_version_key(group) if group else None
        tag_keys = {tag: self._get_tag_key(tag) for tag in tags}
        keys: List[str] = []
        if group_key:
            keys.append(group_key)
        keys.extend(tag_keys.values())

        if not keys:
            return 1, {}

        values_map: Dict[str, Any] = {}
        try:
            if hasattr(self.cache_client, "get_many"):
                values_map = self.cache_client.get_many(keys) or {}
            else:
                for key in keys:
                    val = self.cache_client.get(key)
                    if val is not None:
                        values_map[key] = val
        except Exception as e:
            logger.warning(f"Error batch-fetching cache versions: {e}")
            return 1, {tag: 1 for tag in tags}

        group_version = 1
        if group_key and values_map.get(group_key) is not None:
            try:
                group_version = int(values_map[group_key])
            except (TypeError, ValueError):
                group_version = 1

        tag_versions: Dict[str, int] = {}
        for tag, tag_key in tag_keys.items():
            raw_val = values_map.get(tag_key)
            if raw_val is not None:
                try:
                    tag_versions[tag] = int(raw_val)
                    continue
                except (TypeError, ValueError):
                    pass
            tag_versions[tag] = 1

        return group_version, tag_versions

    def invalidate_tag(self, tag: str) -> int:
        """
        EN: Increments the version of a tag, effectively invalidating all caches depending on it.
        FA: نسخه یک تگ را افزایش می‌دهد که منجر به ابطال تمام کش‌های وابسته به آن می‌شود.
        """
        key = self._get_tag_key(tag)
        new_version = 1
        try:
            if hasattr(self.cache_client, "incr"):
                try:
                    new_version = self.cache_client.incr(key)
                except Exception:
                    val = self.cache_client.get(key)
                    new_version = (int(val) if val else 1) + 1
                    self.cache_client.set(key, new_version)
            else:
                val = self.cache_client.get(key)
                new_version = (int(val) if val else 1) + 1
                self.cache_client.set(key, new_version)
        except Exception as e:
            logger.error(f"Failed to invalidate tag {tag}: {e}", exc_info=True)
            new_version = 2

        # EN: If tag is a dependency of another group, invalidate that group too
        # FA: اگر تگ وابستگی گروه دیگری است، آن گروه را نیز ابطال کن
        self._invalidate_dependencies(tag)
        return new_version

    def _invalidate_dependencies(self, child_item: str) -> None:
        """
        EN: Evaluates the dependency graph and invalidates any parent node depending on child_item.
        FA: گراف وابستگی را ارزیابی کرده و هر گره والدی که به child_item وابسته است را ابطال می‌کند.
        """
        for parent, children in self.DEPENDENCY_GRAPH.items():
            if child_item in children:
                logger.info(
                    f"Dependency triggered: invalidating parent '{parent}' because child '{child_item}' changed."
                )
                # EN: Increment parent's version to invalidate parent cache
                # FA: افزایش نسخه والد جهت ابطال کش والد
                self.increment_version(parent)
