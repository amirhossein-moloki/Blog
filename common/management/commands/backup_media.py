import hashlib
import os
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "EN: Backs up the media directory incrementally to prevent performance issues and ensure storage consistency.\n"
        "FA: پشتیبان‌گیری افزایشی از دایرکتوری رسانه‌ها برای جلوگیری از مشکلات کارایی و اطمینان از یکپارچگی ذخیره‌سازی."
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

        # Hook structure for S3-compatible cloud storage
        storage_backend = getattr(settings, "STORAGE_BACKEND", "local")
        if storage_backend == "s3":
            self.stdout.write(
                "WARNING: Django storage is configured to S3. Future-proof hook point for S3-compatible cloud storage APIs."
            )

        # 2. Incremental Sync logic
        # Traverse all files under MEDIA_ROOT
        for root, _, files in os.walk(source_dir):
            for filename in files:
                total_files += 1
                source_file_path = Path(root) / filename
                relative_path = source_file_path.relative_to(source_dir)
                target_file_path = target_dir / relative_path

                try:
                    # Ensure parent directory exists in backup location
                    target_file_path.parent.mkdir(parents=True, exist_ok=True)

                    should_copy = True
                    if target_file_path.exists():
                        source_stat = source_file_path.stat()
                        target_stat = target_file_path.stat()

                        # Primary check: size and modification time match
                        if source_stat.st_size == target_stat.st_size:
                            # If strict_mode is requested, or if mtimes are significantly different, verify with hash
                            if not strict_mode:
                                # Standard fast-sync path (preserves disk I/O): match sizes and mtimes
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
                        self.style.ERROR(f"Failed to copy '{relative_path}': {str(e)}")
                    )
                    failed_files += 1

        # Print detailed report
        self.stdout.write("\n--- Backup Sync Summary ---")
        self.stdout.write(f"Total Source Files: {total_files}")
        self.stdout.write(f"Copied:             {copied_files}")
        self.stdout.write(f"Skipped (Current):   {skipped_files}")
        self.stdout.write(f"Failed Transfers:   {failed_files}")
        self.stdout.write("---------------------------\n")

        if failed_files > 0:
            raise RuntimeError(
                f"Media backup sync finished with errors. Failed transfers: {failed_files}"
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Media incremental synchronization completed successfully!"
                )
            )
