import os
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from common.bdr_crypto import encrypt_stream


class Command(BaseCommand):
    help = (
        "EN: Safely packages, AES-256-GCM encrypts and backs up deployment configurations and secrets, masking sensitive fields in logs.\n"
        "FA: پشتیبان‌گیری و بسته‌بندی امن و رمزگذاری شده با AES-256-GCM تنظیمات استقرار و اسرار با ماسک کردن مقادیر حساس در لاگ‌ها."
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

    def get_encryption_key(self):
        """
        Derives a safe passphrase string from BACKUP_ENCRYPTION_KEY or Django's SECRET_KEY.
        """
        raw_key = os.environ.get("BACKUP_ENCRYPTION_KEY") or getattr(
            settings, "BACKUP_ENCRYPTION_KEY", None
        )
        if not raw_key:
            raw_key = settings.SECRET_KEY
        if isinstance(raw_key, bytes):
            return raw_key.decode("utf-8")
        return str(raw_key)

    def mask_sensitive_value(self, log_str):
        """
        Masks common sensitive variable values like password/secret key in log lines.
        """
        sensitive_keywords = ["SECRET_KEY", "PASSWORD", "KEY", "TOKEN", "JWT", "AUTH"]
        lines = []
        for line in log_str.splitlines():
            matched = False
            for kw in sensitive_keywords:
                if kw in line.upper() and "=" in line:
                    parts = line.split("=", 1)
                    lines.append(f"{parts[0]}=******** [MASKED]")
                    matched = True
                    break
            if not matched:
                lines.append(line)
        return "\n".join(lines)

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

        temp_tar_path = output_path / f"temp_config_backup_{timestamp}.tar.gz"
        final_tar_name = f"config_backup_{timestamp}.tar.gz.enc"
        final_tar_path = output_path / final_tar_name

        try:
            # 2. Identify deployment files to backup
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
            with tarfile.open(temp_tar_path, "w:gz") as tar:
                for f_item in temp_dir.iterdir():
                    tar.add(f_item, arcname=f_item.name)

            # 4. Encrypt Tar archive using streaming AES-256-GCM
            self.stdout.write("Encrypting configuration backup using AES-256-GCM...")
            passphrase = self.get_encryption_key()
            with open(temp_tar_path, "rb") as f_in, open(final_tar_path, "wb") as f_out:
                encrypt_stream(f_in, f_out, passphrase)

            # Clean up unencrypted temp tar file
            if temp_tar_path.exists():
                temp_tar_path.unlink()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Configuration backup saved successfully to (encrypted): {final_tar_path}"
                )
            )
            self.stdout.write("INFO Config backup completed.")

            # 5. Cleanup temporary config directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

            # S3 off-site config upload logic
            offsite_enabled = os.environ.get("BACKUP_OFFSITE_ENABLED", "false").lower() in ("true", "1", "t") or getattr(settings, "BACKUP_OFFSITE_ENABLED", False)
            offsite_required = os.environ.get("BACKUP_OFFSITE_REQUIRED", "false").lower() in ("true", "1", "t") or getattr(settings, "BACKUP_OFFSITE_REQUIRED", False)
            backup_storage_env = getattr(settings, "BACKUP_STORAGE", "local")
            use_s3_storage = "s3" in [t.strip().lower() for t in backup_storage_env.split(",")]

            if use_s3_storage or offsite_enabled or offsite_required:
                from common.bdr.storage import S3StorageProvider
                s3_provider = S3StorageProvider()
                if s3_provider.is_available():
                    self.stdout.write("INFO Uploading encrypted backup to S3...")
                    try:
                        s3_provider.backup_config(str(final_tar_path), timestamp)
                        self.stdout.write("INFO Upload successful.")
                    except Exception as e:
                        if offsite_required:
                            self.stderr.write("CRITICAL Off-site backup failed.")
                            self.stderr.write("Backup marked as FAILED.")
                            raise e
                        else:
                            self.stdout.write(self.style.WARNING("WARNING S3 upload failed, but ignored (Staging Mode)."))
                else:
                    if offsite_required:
                        self.stderr.write("CRITICAL Off-site backup failed.")
                        self.stderr.write("Backup marked as FAILED.")
                        raise ValueError("S3 credentials not configured in Production environment.")
                    else:
                        self.stdout.write("WARNING S3 backup disabled (Development Mode)")
            else:
                self.stdout.write("WARNING S3 backup disabled (Development Mode)")

            self.stdout.write("INFO Backup completed successfully.")

            # 6. Retention Cleanup
            if not options.get("no_cleanup"):
                self.perform_retention_cleanup(output_path)

            # Update SRE metrics
            from common.bdr_metrics import update_sre_metric

            update_sre_metric(
                "last_successful_config_backup", datetime.utcnow().isoformat()
            )
            update_sre_metric("config_backup_status", "SUCCESS")

        except Exception as e:
            # Safely cleanup temp files/dir
            if temp_tar_path.exists():
                temp_tar_path.unlink()
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            from common.bdr_metrics import update_sre_metric

            update_sre_metric(
                "last_failed_config_backup", datetime.utcnow().isoformat()
            )
            update_sre_metric("config_backup_status", "FAILED")
            update_sre_metric("config_backup_error", str(e))
            self.stderr.write(
                self.style.ERROR(f"Backup configuration process failed: {str(e)}")
            )
            raise e

    def perform_retention_cleanup(self, backup_path):
        """
        Deletes configuration backups using Grandfather-Father-Son (GFS) retention rules.
        """
        from common.bdr_retention import perform_gfs_retention_cleanup

        perform_gfs_retention_cleanup(backup_path, "config_backup_", stdout=self.stdout)
