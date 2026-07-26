"""
EN: Enterprise S3 Backup Provider with compression, AES-256-GCM encryption, integrity verification, and S3 security configuration.
FA: ارائه‌دهنده پشتیبان‌گیری سازمانی S3 همراه با فشرده‌سازی، رمزگذاری AES-256-GCM، اعتبارسنجی یکپارچگی و تنظیمات امنیتی S3.
"""

import gzip
import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from django.conf import settings

from common.bdr_crypto import GzipEncryptionStream, decrypt_and_decompress_stream

try:
    import boto3

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

logger = logging.getLogger(__name__)


class S3BackupProvider:
    """
    EN: S3-compatible Backup Provider supporting secure streaming uploads and downloads.
    FA: ارائه‌دهنده پشتیبانی S3 سازگار با آپلودها و دانلودهای جریانی امن.
    """

    def __init__(
        self,
        bucket_name=None,
        access_key=None,
        secret_key=None,
        endpoint_url=None,
        region_name=None,
    ):
        self.bucket_name = (
            bucket_name
            or os.environ.get("AWS_STORAGE_BUCKET_NAME")
            or getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
        )
        self.access_key = (
            access_key
            or os.environ.get("AWS_ACCESS_KEY_ID")
            or getattr(settings, "AWS_ACCESS_KEY_ID", None)
        )
        self.secret_key = (
            secret_key
            or os.environ.get("AWS_SECRET_ACCESS_KEY")
            or getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
        )
        self.endpoint_url = (
            endpoint_url
            or os.environ.get("AWS_S3_ENDPOINT_URL")
            or getattr(settings, "AWS_S3_ENDPOINT_URL", None)
        )
        self.region_name = (
            region_name
            or os.environ.get("AWS_S3_REGION_NAME")
            or getattr(settings, "AWS_S3_REGION_NAME", "us-east-1")
        )

        if not HAS_BOTO3:
            raise ImportError(
                "boto3 package is required for S3BackupProvider but not installed."
            )

        if not self.bucket_name:
            raise ValueError(
                "S3 bucket name is not configured. Specify AWS_STORAGE_BUCKET_NAME."
            )

        # EN: S3 Client initialization with TLS only enforcement
        # FA: مقداردهی اولیه کلاینت S3 با اجبار استفاده از پروتکل امن TLS
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=self.endpoint_url,
            region_name=self.region_name,
            use_ssl=True,  # TLS-only communication
        )

    def get_encryption_key(self) -> str:
        """
        EN: Derives a safe passphrase string from BACKUP_ENCRYPTION_KEY or Django's SECRET_KEY.
        FA: استخراج رمز عبور امن از کلید پشتیبان‌گیری یا کلید اصلی جنگو.
        """
        raw_key = os.environ.get("BACKUP_ENCRYPTION_KEY") or getattr(
            settings, "BACKUP_ENCRYPTION_KEY", None
        )
        if not raw_key:
            raw_key = settings.SECRET_KEY
        if isinstance(raw_key, bytes):
            return raw_key.decode("utf-8")
        return str(raw_key)

    def _calculate_sha256(self, filepath) -> str:
        """
        EN: Efficiently calculates SHA256 checksum of a file.
        FA: محاسبه کارآمد چکسام SHA256 یک فایل.
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def upload_backup(self, local_file_path, s3_key, metadata=None) -> dict:
        """
        EN: Compresses, encrypts, and uploads local media file to S3 streamingly.
        FA: فشرده‌سازی، رمزگذاری و آپلود جریانی فایل رسانه محلی به S3 بدون ساخت آرشیو غیررمزگذاری شده روی دیسک.
        """
        local_path = Path(local_file_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_file_path}")

        original_size = local_path.stat().st_size
        original_mtime = local_path.stat().st_mtime
        original_sha256 = self._calculate_sha256(local_path)

        # EN: Build safe S3 Metadata tags for incremental comparisons
        # FA: ساخت برچسب‌های متادیتا S3 برای مقایسه افزایشی در آینده
        custom_metadata = {
            "original-size": str(original_size),
            "original-mtime": str(original_mtime),
            "original-sha256": original_sha256,
        }
        if metadata:
            for k, v in metadata.items():
                custom_metadata[k.lower()] = str(v)

        passphrase = self.get_encryption_key()

        # EN: Write directly to encrypted stream to satisfy "Never upload: Plain files, Temporary unencrypted archives"
        # FA: نوشتن مستقیم در جریان رمزگذاری شده برای رعایت عدم ذخیره موقت فایل غیررمزگذاری شده روی دیسک.
        import tempfile

        temp_enc = tempfile.NamedTemporaryFile(delete=False, suffix=".enc")
        temp_enc_name = temp_enc.name
        temp_enc.close()

        try:
            with open(temp_enc_name, "wb") as f_out:
                crypto_stream = GzipEncryptionStream(f_out, passphrase)
                compressor = gzip.GzipFile(fileobj=crypto_stream, mode="wb")
                try:
                    with open(local_path, "rb") as f_in:
                        while True:
                            chunk = f_in.read(65536)
                            if not chunk:
                                break
                            compressor.write(chunk)
                finally:
                    compressor.close()
                    crypto_stream.close()

            enc_size = os.path.getsize(temp_enc_name)
            enc_sha256 = self._calculate_sha256(temp_enc_name)

            # EN: Configure server-side encryption for extra off-site security
            # FA: پیکربندی رمزگذاری سمت سرور برای امنیت بیشتر در فضای ابری خارج از سایت
            extra_args = {
                "Metadata": custom_metadata,
                "ServerSideEncryption": "AES256",
            }

            with open(temp_enc_name, "rb") as f_in:
                self.s3_client.upload_fileobj(
                    f_in,
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    ExtraArgs=extra_args,
                )

            # EN: Post-upload integrity validation
            # FA: اعتبارسنجی یکپارچگی داده‌ها پس از آپلود
            head = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            if head["ContentLength"] != enc_size:
                raise ValueError(f"S3 Object size validation failed for {s3_key}")

            manifest = {
                "file": s3_key,
                "size": enc_size,
                "sha256": enc_sha256,
                "created": datetime.utcnow().isoformat(),
            }
            return manifest

        except Exception as e:
            logger.error(
                f"S3 backup upload failed for key '{s3_key}': {e}", exc_info=True
            )
            from common.bdr_metrics import update_sre_metric

            update_sre_metric("bdr_s3_upload_failed", 1, increment=True)
            raise e
        finally:
            if os.path.exists(temp_enc_name):
                os.unlink(temp_enc_name)

    def download_backup(self, s3_key, local_file_path):
        """
        EN: Downloads encrypted backup from S3 and streamingly decrypts and decompresses it locally.
        FA: دانلود نسخه رمزگذاری شده از S3 و رمزگشایی و خروج از حالت فشرده جریانی در مقصد محلی.
        """
        local_path = Path(local_file_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        import tempfile

        temp_enc = tempfile.NamedTemporaryFile(delete=False, suffix=".enc")
        temp_enc_name = temp_enc.name
        temp_enc.close()

        try:
            with open(temp_enc_name, "wb") as f_out:
                self.s3_client.download_fileobj(self.bucket_name, s3_key, f_out)

            passphrase = self.get_encryption_key()

            with open(temp_enc_name, "rb") as f_in, open(local_path, "wb") as f_out:
                decrypt_and_decompress_stream(f_in, f_out, passphrase)

        finally:
            if os.path.exists(temp_enc_name):
                os.unlink(temp_enc_name)

    def verify_backup(self, s3_key) -> bool:
        """
        EN: Verifies S3 backup integrity by performing a streaming decryption dry-run.
        FA: بررسی صحت نسخه پشتیبان S3 از طریق شبیه‌سازی جریانی رمزگشایی.
        """
        import io

        class NullStream(io.RawIOBase):
            def write(self, b):
                return len(b)

            def writable(self):
                return True

        null_out = NullStream()
        import tempfile

        temp_enc = tempfile.NamedTemporaryFile(delete=False, suffix=".enc")
        temp_enc_name = temp_enc.name
        temp_enc.close()

        try:
            with open(temp_enc_name, "wb") as f_out:
                self.s3_client.download_fileobj(self.bucket_name, s3_key, f_out)

            passphrase = self.get_encryption_key()
            with open(temp_enc_name, "rb") as f_in:
                decrypt_and_decompress_stream(f_in, null_out, passphrase)
            return True
        except Exception as e:
            logger.error(
                f"S3 backup verification failed for '{s3_key}': {e}", exc_info=True
            )
            return False
        finally:
            if os.path.exists(temp_enc_name):
                os.unlink(temp_enc_name)

    def list_backups(self, prefix="") -> list:
        """
        EN: Lists backup keys in S3 along with their associated metadata.
        FA: لیست کردن فایل‌های پشتیبان در S3 به همراه متادیتای مرتبط با آن‌ها.
        """
        paginator = self.s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

        backups = []
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                size = obj["Size"]
                last_modified = obj["LastModified"]
                try:
                    head = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
                    metadata = head.get("Metadata", {})
                except Exception:
                    metadata = {}
                backups.append(
                    {
                        "Key": key,
                        "Size": size,
                        "LastModified": last_modified,
                        "Metadata": metadata,
                    }
                )
        return backups

    def delete_expired_backup(self, s3_key) -> bool:
        """
        EN: Deletes a backup object from S3.
        FA: حذف فایل پشتیبان از S3 در راستای انقضای مانیفست.
        """
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
        return True
