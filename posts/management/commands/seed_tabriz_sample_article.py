"""
EN: Management command to create/update the sample draft article "بهترین گیم‌نت‌های تبریز"
    connected via Bayesian auto-ranking mode without duplicating mutable center data.
FA: دستور مدیریتی برای ایجاد/به‌روزرسانی مقاله نمونه پیش‌نویس «بهترین گیم‌نت‌های تبریز»
    متصل به رتبه‌بندی خودکار Bayesian سایرا بدون کپی کردن اطلاعات متغیر مراکز.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from posts.models import Article, ArticleTranslation, AuthorProfile, Category


class Command(BaseCommand):
    help = "Create/update draft sample article 'بهترین گیم‌نت‌های تبریز' linked to Sayra rankings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--publish",
            action="store_true",
            default=False,
            help="Explicitly publish the article (defaults to draft for pre-launch review).",
        )
        parser.add_argument("--city", default="تبریز", help="Target city filter")
        parser.add_argument("--min-reviews", type=int, default=3)
        parser.add_argument("--bayesian-m", type=float, default=3.0)
        parser.add_argument("--limit", type=int, default=10)

    def handle(self, *args, **options):
        user_model = get_user_model()
        city = str(options["city"]).strip() or "تبریز"
        min_reviews = max(0, int(options["min_reviews"]))
        bayesian_m = max(0.1, float(options["bayesian_m"]))
        limit = max(1, min(50, int(options["limit"])))
        target_status = "published" if options.get("publish") else "draft"

        slug = "best-gaming-centers-tabriz"
        title = "بهترین گیم‌نت‌های تبریز"
        excerpt = (
            "معرفی و رتبه‌بندی هوشمند بهترین گیم‌نت‌های فعال و احراز هویت‌شده تبریز بر اساس "
            "امتیاز واقعی کاربران، تعداد نظرات معتبر و فرمول Bayesian Average سایرا."
        )
        content_blocks = [
            {
                "id": "intro-heading",
                "type": "heading",
                "data": {"text": "معیارهای رتبه‌بندی بهترین گیم‌نت‌های تبریز", "level": 2},
                "settings": {},
                "meta": {},
            },
            {
                "id": "intro-paragraph",
                "type": "paragraph",
                "data": {
                    "text": (
                        "فهرست گیم‌نت‌های این صفحه به‌صورت پویا از سامانه رزرو و احراز هویت سایرا "
                        "دریافت می‌شود. تنها مراکزی که فعال بوده و احراز هویت آن‌ها تأیید شده است "
                        "در خروجی عمومی قرار می‌گیرند. رتبه‌بندی با فرمول میانگین بیزی "
                        "(Bayesian Average) بر پایه نظرات ثبت‌شده برای رزروهای تکمیل‌شده محاسبه می‌شود "
                        "و مراکز تازه‌ثبت‌شده با نظرات کمتر از حد نصاب در بخش مجزا نمایش داده می‌شوند."
                    )
                },
                "settings": {},
                "meta": {},
            },
        ]

        with transaction.atomic():
            user, _ = user_model.objects.get_or_create(
                username="sayra_editorial",
                defaults={"email": "editorial@sayra-booking.ir", "is_staff": False},
            )
            author_profile, _ = AuthorProfile.objects.get_or_create(
                user=user,
                defaults={"display_name": "تحریریه سایرا"},
            )
            category, _ = Category.objects.get_or_create(
                slug="city-guides",
                defaults={"name": "راهنمای شهرها"},
            )

            existing_trans = (
                ArticleTranslation.objects.select_related("article")
                .filter(slug=slug, language_code="fa")
                .first()
            )
            if existing_trans:
                article = existing_trans.article
                article.category = category
                article.status = target_status
                article.visibility = "public"
                article.gaming_center_mode = "auto_ranking"
                article.ranking_city = city
                article.ranking_limit = limit
                article.ranking_min_reviews = min_reviews
                article.ranking_bayesian_m = bayesian_m
                article.ranking_sort = "bayesian"
                article.include_newly_registered = True
                article.save()
                existing_trans.title = title
                existing_trans.excerpt = excerpt
                existing_trans.short_description = excerpt
                existing_trans.content_blocks = content_blocks
                existing_trans.seo_title = "بهترین گیم‌نت‌های تبریز | مقایسه و رزرو آنلاین در سایرا"
                existing_trans.seo_description = excerpt
                existing_trans.save()
                action_label = "Updated"
            else:
                article = Article.objects.create(
                    author=author_profile,
                    category=category,
                    status=target_status,
                    visibility="public",
                    gaming_center_mode="auto_ranking",
                    ranking_city=city,
                    ranking_limit=limit,
                    ranking_min_reviews=min_reviews,
                    ranking_bayesian_m=bayesian_m,
                    ranking_sort="bayesian",
                    include_newly_registered=True,
                )
                ArticleTranslation.objects.create(
                    article=article,
                    language_code="fa",
                    slug=slug,
                    title=title,
                    excerpt=excerpt,
                    short_description=excerpt,
                    content_blocks=content_blocks,
                    seo_title="بهترین گیم‌نت‌های تبریز | مقایسه و رزرو آنلاین در سایرا",
                    seo_description=excerpt,
                )
                action_label = "Created"

        self.stdout.write(
            self.style.SUCCESS(
                f"{action_label} Article #{article.id} (slug={slug}, status={article.status}, "
                f"mode={article.gaming_center_mode}, city={article.ranking_city}, "
                f"m={article.ranking_bayesian_m}, min_reviews={article.ranking_min_reviews})"
            )
        )
