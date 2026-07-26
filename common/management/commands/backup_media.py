import hashlib
import json
import os
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

try:
    import boto3

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


class Command(BaseCommand):
    help = (
        "EN: Backs up the media directory streamingly and incrementally supporting local and S3-compatible storage with deleted object protection.\n"
        "FA: پشتیبان‌گیری جریانی و افزایشی از رسانه‌ها با پشتیبانی از ذخیره‌سازی محلی و S3 سازگار همراه با محافظت از اشیاء حذف شده."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            help="Directory to sync media backups (defaults to BASE_DIR / 'backups' / 'media')",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Force strict SHA-256 checksum comparison on all files regardless of size/mtime matches",
        )

    def calculate_sha256(self, file_path):
        """
        Calculates SHA-256 checksum of a file to detect changes/corruption.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def is_s3_storage(self):
        """
        Detects if S3 storage backend is configured.
        """
        storage_backend = getattr(settings, "STORAGE_BACKEND", "local")
        if storage_backend == "s3":
            return True
        if os.environ.get("AWS_STORAGE_BUCKET_NAME") or getattr(
            settings, "AWS_STORAGE_BUCKET_NAME", None
        ):
            return True
        storages_config = getattr(settings, "STORAGES", {})
        default_backend = storages_config.get("default", {}).get("BACKEND", "")
        if "s3" in default_backend.lower():
            return True
        return False

    def handle(self, *args, **options):
        # 1. Resolve source and target directories
        source_dir = Path(settings.MEDIA_ROOT)
        if not source_dir.exists():
            source_dir.mkdir(parents=True, exist_ok=True)
            self.stdout.write(f"Created empty source media directory at {source_dir}")

        target_arg = options.get("output_dir")
        if not target_arg:
            base_backup_dir = os.environ.get("BACKUP_DIR") or getattr(
                settings, "BACKUP_DIR", None
            )
            if base_backup_dir:
                target_dir = Path(base_backup_dir) / "media"
            else:
                target_dir = Path(settings.BASE_DIR) / "backups" / "media"
        else:
            target_dir = Path(target_arg)

        target_dir.mkdir(parents=True, exist_ok=True)
        self.stdout.write(
            self.style.SUCCESS(f"Media backup sync resolved to target: {target_dir}")
        )

        strict_mode = options.get("strict", False)

        # Setup stats
        copied_files = 0
        skipped_files = 0
        failed_files = 0
        total_files = 0

        # 2. Dynamic Storage Backend Detection
        use_s3 = self.is_s3_storage()

        if use_s3:
            self.stdout.write(
                "S3-compatible storage backend detected. Starting upload sync to secure off-site S3 storage..."
            )
            if not HAS_BOTO3:
                raise ImportError(
                    "boto3 package is required for S3 synchronization but not installed."
                )

            # Resolve S3 connection credentials
            bucket_name = os.environ.get("AWS_STORAGE_BUCKET_NAME") or getattr(
                settings, "AWS_STORAGE_BUCKET_NAME", None
            )
            if not bucket_name:
                raise ValueError(
                    "S3 bucket name is not configured. Specify AWS_STORAGE_BUCKET_NAME."
                )

            from common.bdr.s3_backup_provider import S3BackupProvider

            provider = S3BackupProvider()

            # Retrieve existing backup objects in S3
            existing_backups = {}
            try:
                self.stdout.write(
                    f" -> Accessing S3/compatible bucket: '{bucket_name}'..."
                )
                backups_list = provider.list_backups(prefix="media/")
                for b in backups_list:
                    key = b["Key"]
                    if key.endswith(".enc"):
                        # Extract original relative path by removing 'media/' prefix and '.enc' suffix
                        orig_rel_path = key[len("media/") : -len(".enc")]
                    else:
                        orig_rel_path = key[len("media/") :]
                    existing_backups[orig_rel_path] = b
                    total_files += 1
            except Exception as e:
                self.stderr.write(
                    self.style.WARNING(
                        f"Failed to list S3 backups: {e}. Assuming empty S3 backup storage."
                    )
                )

            # Push incremental changes to S3
            for root, _, files in os.walk(source_dir):
                for filename in files:
                    source_file_path = Path(root) / filename
                    relative_path = source_file_path.relative_to(source_dir)
                    s3_key = f"media/{relative_path.as_posix()}.enc"

                    try:
                        should_upload = True
                        source_stat = source_file_path.stat()
                        orig_size = source_stat.st_size
                        orig_mtime = source_stat.st_mtime
                        orig_sha = self.calculate_sha256(source_file_path)

                        if relative_path.as_posix() in existing_backups:
                            existing = existing_backups[relative_path.as_posix()]
                            metadata = existing.get("Metadata", {})

                            s3_orig_size = metadata.get("original-size")
                            s3_orig_mtime = metadata.get("original-mtime")
                            s3_orig_sha256 = metadata.get("original-sha256")

                            if (
                                s3_orig_size == str(orig_size)
                                and s3_orig_sha256 == orig_sha
                            ):
                                if not strict_mode:
                                    if (
                                        s3_orig_mtime
                                        and abs(float(s3_orig_mtime) - orig_mtime) < 2.0
                                    ):
                                        should_upload = False
                                else:
                                    should_upload = False

                        if should_upload:
                            self.stdout.write(
                                f"Compressing, encrypting, and uploading to S3: {relative_path}..."
                            )
                            manifest = provider.upload_backup(
                                source_file_path,
                                s3_key,
                                metadata={
                                    "original-size": orig_size,
                                    "original-mtime": orig_mtime,
                                    "original-sha256": orig_sha,
                                },
                            )
                            self.stdout.write(
                                f" -> Upload Integrity Manifest: {json.dumps(manifest)}"
                            )
                            copied_files += 1
                        else:
                            skipped_files += 1

                    except Exception as e:
                        self.stderr.write(
                            self.style.ERROR(
                                f"Failed to upload media object '{relative_path}' to S3: {str(e)}"
                            )
                        )
                        failed_files += 1

            # Deleted Object Protection: Keep files in S3 if deleted locally
            for orig_rel_path in existing_backups:
                source_counterpart = source_dir / orig_rel_path
                if not source_counterpart.exists():
                    self.stdout.write(
                        self.style.SUCCESS(
                            f" [PROTECTED] -> S3 backup file '{orig_rel_path}' is protected from deletion (not in source directory)."
                        )
                    )

        else:
            self.stdout.write(
                "Local storage backend detected. Starting local incremental sync..."
            )
            # 3. Incremental Local Sync logic
            for root, _, files in os.walk(source_dir):
                for filename in files:
                    total_files += 1
                    source_file_path = Path(root) / filename
                    relative_path = source_file_path.relative_to(source_dir)
                    target_file_path = target_dir / relative_path

                    try:
                        target_file_path.parent.mkdir(parents=True, exist_ok=True)
                        should_copy = True

                        if target_file_path.exists():
                            source_stat = source_file_path.stat()
                            target_stat = target_file_path.stat()

                            # Primary check: size and modification time match
                            if source_stat.st_size == target_stat.st_size:
                                if not strict_mode:
                                    if (
                                        abs(source_stat.st_mtime - target_stat.st_mtime)
                                        < 2.0
                                    ):
                                        should_copy = False
                                else:
                                    src_sha = self.calculate_sha256(source_file_path)
                                    tgt_sha = self.calculate_sha256(target_file_path)
                                    if src_sha == tgt_sha:
                                        should_copy = False

                        if should_copy:
                            self.stdout.write(f"Syncing: {relative_path}...")
                            shutil.copy2(source_file_path, target_file_path)
                            copied_files += 1
                        else:
                            skipped_files += 1

                    except Exception as e:
                        self.stderr.write(
                            self.style.ERROR(
                                f"Failed to copy '{relative_path}': {str(e)}"
                            )
                        )
                        failed_files += 1

            # Deleted Object Protection: Local version
            # If a local file exists under target_dir but not in source_dir, we KEEP it in backup!
            for root, _, files in os.walk(target_dir):
                for filename in files:
                    local_path = Path(root) / filename
                    relative_path = local_path.relative_to(target_dir)
                    source_counterpart = source_dir / relative_path
                    if not source_counterpart.exists():
                        self.stdout.write(
                            self.style.SUCCESS(
                                f" [PROTECTED] -> Local backup file '{relative_path}' is protected from deletion (not in source directory)."
                            )
                        )

        # Print detailed report
        self.stdout.write("\n--- Backup Sync Summary ---")
        self.stdout.write(f"Total Source Files: {total_files}")
        self.stdout.write(f"Copied:             {copied_files}")
        self.stdout.write(f"Skipped (Current):   {skipped_files}")
        self.stdout.write(f"Failed Transfers:   {failed_files}")
        self.stdout.write("---------------------------\n")

        if failed_files > 0:
            from datetime import datetime

            from common.bdr_metrics import update_sre_metric

            update_sre_metric("last_failed_media_backup", datetime.utcnow().isoformat())
            update_sre_metric("media_backup_status", "FAILED")
            raise RuntimeError(
                f"Media backup sync finished with errors. Failed transfers: {failed_files}"
            )
        else:
            from datetime import datetime

            from common.bdr_metrics import update_sre_metric

            update_sre_metric(
                "last_successful_media_backup", datetime.utcnow().isoformat()
            )
            update_sre_metric("media_backup_status", "SUCCESS")
            update_sre_metric("media_backup_copied_files", copied_files)
            update_sre_metric("media_backup_skipped_files", skipped_files)
            self.stdout.write(
                self.style.SUCCESS(
                    "Media incremental synchronization completed successfully!"
                )
            )
