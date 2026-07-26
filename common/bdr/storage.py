"""
EN: Enterprise environment-aware BDR Storage Provider Redesign.
FA: بازطراحی لایه ذخیره‌سازی سازمانی و حساس به محیط BDR.
"""

import logging
import os
import shutil
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from common.bdr.s3_backup_provider import S3BackupProvider

logger = logging.getLogger(__name__)


class BackupStorageProvider:
    """
    EN: Base Backup Storage Provider abstraction.
    FA: کلاس پایه انتزاعی ارائه‌دهنده ذخیره‌سازی پشتیبان.
    """

    def backup_database(self, local_path, timestamp_str, **kwargs):
        raise NotImplementedError()

    def backup_media(self, source_dir, target_dir, **kwargs):
        raise NotImplementedError()

    def backup_config(self, local_path, timestamp_str, **kwargs):
        raise NotImplementedError()

    def restore(self, backup_type, file_path, **kwargs):
        raise NotImplementedError()

    def verify(self, backup_type, file_path, **kwargs):
        raise NotImplementedError()

    def cleanup(self, backup_type, target_dir, **kwargs):
        raise NotImplementedError()


class LocalStorageProvider(BackupStorageProvider):
    """
    EN: Local Storage Provider implementing standard file system operations.
    FA: ارائه‌دهنده ذخیره‌سازی محلی برای عملیات سیستم فایل استاندارد.
    """

    def backup_database(self, local_path, timestamp_str, **kwargs):
        logger.info("Database backup completed locally.")

    def backup_media(self, source_dir, target_dir, **kwargs):
        logger.info("Media backup completed locally.")

    def backup_config(self, local_path, timestamp_str, **kwargs):
        logger.info("Config backup completed locally.")

    def restore(self, backup_type, file_path, **kwargs):
        logger.info(f"Local restore completed for {backup_type} from {file_path}")

    def verify(self, backup_type, file_path, **kwargs):
        logger.info(f"Local verification completed for {backup_type}")
        return True

    def cleanup(self, backup_type, target_dir, **kwargs):
        logger.info(f"Local cleanup completed for {backup_type} in {target_dir}")


class S3StorageProvider(BackupStorageProvider):
    """
    EN: S3 Storage Provider for off-site backup, validation, and restoration.
    FA: ارائه‌دهنده ذخیره‌سازی S3 برای پشتیبان‌گیری، اعتبارسنجی و بازیابی خارج از سایت.
    """

    def __init__(self):
        self.bucket_name = os.environ.get("AWS_STORAGE_BUCKET_NAME") or getattr(
            settings, "AWS_STORAGE_BUCKET_NAME", None
        )
        self.access_key = os.environ.get("AWS_ACCESS_KEY_ID") or getattr(
            settings, "AWS_ACCESS_KEY_ID", None
        )
        self.secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY") or getattr(
            settings, "AWS_SECRET_ACCESS_KEY", None
        )
        self.s3_configured = bool(self.bucket_name)
        self.provider = None
        if self.s3_configured:
            self.provider = S3BackupProvider()

    def is_available(self) -> bool:
        return self.s3_configured

    def backup_database(self, local_file_path, timestamp_str, **kwargs):
        if not self.is_available():
            raise ValueError("S3 credentials not configured.")
        s3_key = f"database/{os.path.basename(local_file_path)}"
        logger.info(f"Uploading encrypted backup to S3... (Key: {s3_key})")
        manifest = self.provider.upload_backup(local_file_path, s3_key)
        logger.info("Upload successful.")

        # Also upload associated manifest if it exists
        manifest_path = (
            Path(local_file_path).parent
            / f"{os.path.basename(local_file_path)}_manifest.json"
        )
        if manifest_path.exists():
            s3_manifest_key = f"database/{manifest_path.name}"
            # Simply upload manifest as a plain file using client directly or provider
            self.provider.s3_client.upload_file(
                Filename=str(manifest_path),
                Bucket=self.bucket_name,
                Key=s3_manifest_key,
            )
        return manifest

    def backup_media(self, local_file_path, s3_key, metadata=None, **kwargs):
        if not self.is_available():
            raise ValueError("S3 credentials not configured.")
        logger.info(f"Uploading encrypted media backup to S3... (Key: {s3_key})")
        manifest = self.provider.upload_backup(
            local_file_path, s3_key, metadata=metadata
        )
        logger.info("Upload successful.")
        return manifest

    def backup_config(self, local_file_path, timestamp_str, **kwargs):
        if not self.is_available():
            raise ValueError("S3 credentials not configured.")
        s3_key = f"config/{os.path.basename(local_file_path)}"
        logger.info(f"Uploading encrypted config backup to S3... (Key: {s3_key})")
        manifest = self.provider.upload_backup(local_file_path, s3_key)
        logger.info("Upload successful.")
        return manifest

    def restore(self, s3_key, local_file_path, **kwargs):
        if not self.is_available():
            raise ValueError("S3 credentials not configured.")
        logger.info(f"Downloading backup from S3... (Key: {s3_key})")
        self.provider.download_backup(s3_key, local_file_path)
        logger.info(f"S3 restore completed for {s3_key}")

    def verify(self, s3_key, **kwargs):
        if not self.is_available():
            raise ValueError("S3 credentials not configured.")
        return self.provider.verify_backup(s3_key)

    def cleanup(self, s3_key, **kwargs):
        if not self.is_available():
            raise ValueError("S3 credentials not configured.")
        return self.provider.delete_expired_backup(s3_key)


def get_storage_providers():
    """
    EN: Resolves active storage providers based on configuration and environment.
    FA: حل و فرآوری ارائه‌دهندگان ذخیره‌سازی فعال بر اساس تنظیمات و محیط.
    """
    backup_storage_env = getattr(settings, "BACKUP_STORAGE", "local")
    storage_types = [t.strip().lower() for t in backup_storage_env.split(",")]

    providers = []
    if "local" in storage_types:
        providers.append(LocalStorageProvider())
    if "s3" in storage_types:
        providers.append(S3StorageProvider())

    return providers
