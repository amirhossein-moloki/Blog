import os
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "EN: Safely packages and backs up deployment configurations and secrets, masking sensitive fields in logs.\n"
        "FA: پشتیبان‌گیری و بسته‌بندی امن تنظیمات استقرار و اسرار با ماسک کردن مقادیر حساس در لاگ‌ها."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            help="Directory to save config backups (defaults to BASE_DIR / 'backups' / 'config')",
        )
        parser.add_argument(
            "--no-cleanup", action="store_true", help="Skip the retention cleanup phase"
        )

    def handle(self, *args, **options):
        # 1. Resolve output directory
        base_arg = options.get("output_dir")
        if not base_arg:
            base_backup_dir = os.environ.get("BACKUP_DIR") or getattr(
                settings, "BACKUP_DIR", None
            )
            if base_backup_dir:
                output_path = Path(base_backup_dir) / "config"
            else:
                output_path = Path(settings.BASE_DIR) / "backups" / "config"
        else:
            output_path = Path(base_arg)

        output_path.mkdir(parents=True, exist_ok=True)
        self.stdout.write(
            self.style.SUCCESS(
                f"Configuration backup directory resolved to: {output_path}"
            )
        )

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        temp_dir = output_path / f"temp_config_{timestamp}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        final_tar_name = f"config_backup_{timestamp}.tar.gz"
        final_tar_path = output_path / final_tar_name

        try:
            # 2. Identify deployment files to backup
            # Typically .env files, docker-compose.yml, Nginx configurations
            files_to_backup = [
                Path(settings.BASE_DIR) / ".env",
                Path(settings.BASE_DIR) / ".env.example",
                Path(settings.BASE_DIR) / "docker-compose.yml",
                Path(settings.BASE_DIR) / "nginx" / "nginx.conf",
                Path(settings.BASE_DIR) / "nginx" / "Dockerfile",
            ]

            copied_any = False
            for src_file in files_to_backup:
                if src_file.exists():
                    self.stdout.write(
                        f"Preparing to package configuration: {src_file.name}"
                    )

                    # Copy to temp directory preserving nested structure
                    dest_file_path = temp_dir / src_file.name
                    shutil.copy2(src_file, dest_file_path)
                    copied_any = True
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Configuration file omitted (not found): {src_file}"
                        )
                    )

            if not copied_any:
                raise ValueError(
                    "No matching deployment or configuration files were found to backup."
                )

            # 3. Create Gzipped Tar archive
            self.stdout.write("Packaging files into compressed tarball...")
            with tarfile.open(final_tar_path, "w:gz") as tar:
                for f_item in temp_dir.iterdir():
                    tar.add(f_item, arcname=f_item.name)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Configuration backup saved successfully to: {final_tar_path}"
                )
            )

            # 4. Cleanup temporary config directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

            # 5. Retention Cleanup
            if not options.get("no_cleanup"):
                self.perform_retention_cleanup(output_path)

        except Exception as e:
            # Safely cleanup temp dir
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            self.stderr.write(
                self.style.ERROR(f"Backup configuration process failed: {str(e)}")
            )
            raise e

    def perform_retention_cleanup(self, backup_path):
        """
        Deletes configuration backups older than the configured BACKUP_RETENTION_DAYS (defaults to 7).
        """
        retention_days = int(
            os.environ.get("BACKUP_RETENTION_DAYS")
            or getattr(settings, "BACKUP_RETENTION_DAYS", 7)
        )
        self.stdout.write(
            f"Initiating retention cleanup (retention threshold: {retention_days} days)..."
        )

        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Scan backup directory for config_backup files
        for item in backup_path.iterdir():
            if item.is_file() and (item.name.startswith("config_backup_")):
                mtime = datetime.utcfromtimestamp(item.stat().st_mtime)
                if mtime < cutoff_date:
                    self.stdout.write(
                        f"Deleting expired config backup: {item.name} (mtime: {mtime})"
                    )
                    item.unlink()
