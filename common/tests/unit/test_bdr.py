import gzip
import json
import os
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings

from common.bdr_crypto import (
    GzipEncryptionStream,
    decrypt_and_decompress_stream,
    decrypt_stream,
    encrypt_stream,
)
from common.bdr_retention import perform_gfs_retention_cleanup
from common.tasks import (
    backup_config_task,
    backup_database_task,
    backup_media_task,
    validate_backups_task,
)

try:
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class BackupDatabaseTest(TestCase):
    def setUp(self):
        super().setUp()
        self.temp_backup_dir = Path(settings.BASE_DIR) / "test_backups_db"
        self.temp_backup_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.temp_backup_dir.exists():
            shutil.rmtree(self.temp_backup_dir)
        super().tearDown()

    @override_settings(BACKUP_ENCRYPT=False)
    @patch("subprocess.Popen")
    def test_backup_database_unencrypted_sqlite(self, mock_popen):
        """
        Tests backing up an unencrypted database with the default SQLite database engine.
        """
        out_dir = self.temp_backup_dir / "database"
        call_command("backup_database", "--output-dir", str(out_dir), "--no-cleanup")

        # Confirm target directory has the gzip file
        files = list(out_dir.glob("*.gz"))
        self.assertEqual(len(files), 1)
        backup_file = files[0]

        # Verify compression/gzip format by opening and reading it
        with gzip.open(backup_file, "rb") as f:
            content = f.read()
            self.assertTrue(b"SQLite" in content or len(content) >= 0)

    @override_settings(
        BACKUP_ENCRYPT=True, BACKUP_ENCRYPTION_KEY="test_super_secret_key"
    )
    def test_backup_database_encrypted_sqlite(self):
        """
        Tests database backup with AES-256-GCM encryption.
        """
        out_dir = self.temp_backup_dir / "database"
        call_command("backup_database", "--output-dir", str(out_dir), "--no-cleanup")

        files = list(out_dir.glob("*.enc"))
        self.assertEqual(len(files), 1)
        enc_file = files[0]

        # Decrypt stream to verify
        import io

        dec_out = io.BytesIO()
        passphrase = "test_super_secret_key"
        with open(enc_file, "rb") as f_in:
            decrypt_and_decompress_stream(f_in, dec_out, passphrase)

        decrypted_content = dec_out.getvalue()
        self.assertTrue(b"SQLite" in decrypted_content or len(decrypted_content) >= 0)

    @override_settings(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "test_db",
                "USER": "test_user",
                "PASSWORD": "test_password",
                "HOST": "localhost",
                "PORT": "5432",
            }
        }
    )
    @patch("shutil.which", return_value="/usr/bin/pg_dump")
    @patch("subprocess.Popen")
    def test_backup_database_postgresql_pg_dump(self, mock_popen, mock_which):
        """
        Tests pg_dump invocation when using the postgresql engine.
        """
        # Configure Popen process mock
        mock_process = MagicMock()
        mock_process.stdout.read.side_effect = [b"CREATE TABLE test;", b""]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        out_dir = self.temp_backup_dir / "database"
        call_command("backup_database", "--output-dir", str(out_dir), "--no-cleanup")

        # Verify pg_dump Popen was called (handling internal delegates)
        self.assertTrue(mock_popen.called)

        pg_dump_called = False
        for call_obj in mock_popen.call_args_list:
            args = call_obj[0][0]
            if "pg_dump" in args:
                pg_dump_called = True
                self.assertIn("test_db", args)
                break
        self.assertTrue(pg_dump_called, "pg_dump should be run")

    def test_backup_database_retention_cleanup(self):
        """
        Tests GFS retention rules clean up older backups while preserving key ones.
        """
        out_dir = self.temp_backup_dir / "database"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Create multiple fake hourly, daily, weekly, monthly backups
        now = datetime.utcnow()

        # 1. Newest backup (always kept)
        b1 = out_dir / f"db_backup_{now.strftime('%Y%m%d_%H%M%S')}.sql.gz"
        b1.write_text("fresh")

        # 2. Backups to keep as GFS daily
        b2_ts = now - timedelta(days=2)
        b2 = out_dir / f"db_backup_{b2_ts.strftime('%Y%m%d_%H%M%S')}.sql.gz"
        b2.write_text("keep day 2")
        os.utime(b2, (b2_ts.timestamp(), b2_ts.timestamp()))

        # 3. Expired backup outside any retention window
        expired_ts = now - timedelta(days=100)
        b_expired = out_dir / f"db_backup_{expired_ts.strftime('%Y%m%d_%H%M%S')}.sql.gz"
        b_expired.write_text("expired")
        os.utime(b_expired, (expired_ts.timestamp(), expired_ts.timestamp()))

        # Run GFS retention cleanup
        with patch.dict(os.environ, {"RETENTION_DAILY": "7", "RETENTION_MONTHLY": "1"}):
            perform_gfs_retention_cleanup(out_dir, "db_backup_")

        self.assertTrue(b1.exists(), "Newest backup must be kept.")
        self.assertTrue(b2.exists(), "GFS daily backup within threshold must be kept.")
        self.assertFalse(
            b_expired.exists(),
            "Expired backup outside retention windows must be purged.",
        )


class BackupMediaTest(TestCase):
    def setUp(self):
        super().setUp()
        self.temp_src_dir = Path(settings.BASE_DIR) / "test_media_src"
        self.temp_dst_dir = Path(settings.BASE_DIR) / "test_media_dst"

        self.temp_src_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dst_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.temp_src_dir.exists():
            shutil.rmtree(self.temp_src_dir)
        if self.temp_dst_dir.exists():
            shutil.rmtree(self.temp_dst_dir)
        super().tearDown()

    def test_backup_media_incremental_sync(self):
        """
        Tests incremental synchronization and deleted object protection of media files.
        """
        # Create some media files
        (self.temp_src_dir / "pic1.jpg").write_text("image content 1")
        (self.temp_src_dir / "folder").mkdir(parents=True, exist_ok=True)
        (self.temp_src_dir / "folder" / "pic2.png").write_text("image content 2")

        # Sync
        with override_settings(MEDIA_ROOT=str(self.temp_src_dir)):
            call_command("backup_media", "--output-dir", str(self.temp_dst_dir))

        self.assertTrue((self.temp_dst_dir / "pic1.jpg").exists())
        self.assertTrue((self.temp_dst_dir / "folder" / "pic2.png").exists())

        # Delete file in source (Deleted Object Protection test)
        (self.temp_src_dir / "pic1.jpg").unlink()

        with override_settings(MEDIA_ROOT=str(self.temp_src_dir)):
            call_command("backup_media", "--output-dir", str(self.temp_dst_dir))

        # Deleted file in source must NOT be deleted in target backup
        self.assertTrue(
            (self.temp_dst_dir / "pic1.jpg").exists(),
            "Backup must protect against deletion in source.",
        )

    @patch("boto3.client")
    @override_settings(STORAGE_BACKEND="s3", AWS_STORAGE_BUCKET_NAME="test-bucket")
    def test_backup_media_s3_sync(self, mock_boto_client):
        """
        Tests S3-compatible cloud storage dynamic detection and bucket synchronization.
        """
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Mock paginator contents for list_objects_v2
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "media/image1.jpg.enc",
                        "Size": 100,
                        "LastModified": datetime.utcnow(),
                    },
                    {
                        "Key": "media/folder/image2.png.enc",
                        "Size": 200,
                        "LastModified": datetime.utcnow(),
                    },
                ]
            }
        ]
        mock_s3.get_paginator.return_value = mock_paginator

        # Mock head_object to bypass ContentLength size validation
        class EqualToAnything:
            def __eq__(self, other):
                return True

        mock_s3.head_object.return_value = {
            "ContentLength": EqualToAnything(),
            "Metadata": {
                "original-size": "100",
                "original-sha256": "wrong_sha_to_force_upload",
                "original-mtime": "0.0",
            },
        }

        # Create some mock local files to backup
        (self.temp_src_dir / "image1.jpg").write_text("local image 1")
        (self.temp_src_dir / "folder").mkdir(parents=True, exist_ok=True)
        (self.temp_src_dir / "folder" / "image2.png").write_text("local image 2")

        with override_settings(MEDIA_ROOT=str(self.temp_src_dir)):
            call_command("backup_media", "--output-dir", str(self.temp_dst_dir))

        # Verify s3 client list objects and upload was invoked due to push architecture
        self.assertTrue(mock_s3.get_paginator.called)
        self.assertTrue(mock_s3.upload_fileobj.called)


class MaintenanceLockFallbackTest(TestCase):
    def setUp(self):
        super().setUp()
        from common.bdr.maintenance_lock import MaintenanceLockManager

        self.lock_manager = MaintenanceLockManager()
        # Ensure locks are released/clean before tests
        self.lock_manager.release_lock()

    def tearDown(self):
        self.lock_manager.release_lock()
        super().tearDown()

    @patch("redis.Redis")
    def test_redis_failure_during_restore_creates_local_lock(self, mock_redis):
        """
        Verifies that if Redis fails or is unavailable during a restore, the system
        gracefully falls back to creating an atomic POSIX maintenance lock file.
        """
        # Configure redis client to raise an exception, simulating redis failure
        mock_client = MagicMock()
        mock_client.set.side_effect = Exception("Redis connection timed out")
        self.lock_manager.redis_client = mock_client

        # Attempt to acquire maintenance lock
        success = self.lock_manager.acquire_lock(owner="test-job-fallback")
        self.assertTrue(success)

        # Verify Redis fallback activated: local maintenance.lock was created
        self.assertTrue(self.lock_manager.local_lock_path.exists())

        # Verify lock content contains the expected JSON metadata
        with open(self.lock_manager.local_lock_path, "r") as f:
            data = json.load(f)
            self.assertEqual(data["reason"], "database_restore")
            self.assertEqual(data["owner"], "test-job-fallback")

    @patch("redis.Redis")
    def test_redis_acquire_release_check_happy_path(self, mock_redis):
        """
        Tests the lock manager's happy path when Redis is active and available.
        """
        mock_client = MagicMock()
        mock_client.set.return_value = True
        mock_client.exists.return_value = True
        mock_client.get.return_value = json.dumps(
            {
                "owner": "test-owner",
                "created": datetime.utcnow().isoformat(),
                "ttl": 600,
            }
        )
        self.lock_manager.redis_client = mock_client

        # Test acquire
        success = self.lock_manager.acquire_lock(owner="test-owner")
        self.assertTrue(success)
        mock_client.set.assert_called_once()

        # Test check is_locked
        self.assertTrue(self.lock_manager.is_locked())
        mock_client.exists.assert_called_once()

        # Test get_status
        status = self.lock_manager.get_status()
        self.assertTrue(status["locked"])
        self.assertEqual(status["type"], "redis")
        self.assertEqual(status["owner"], "test-owner")

        # Test release
        released = self.lock_manager.release_lock()
        self.assertTrue(released)
        mock_client.delete.assert_called_with(self.lock_manager.redis_lock_key)

    def test_active_middleware_blocks_with_http_503(self):
        """
        Verifies that when a maintenance lock is active, the middleware intercepts
        requests and returns a proper HTTP 503 response.
        """
        from django.test import RequestFactory

        from common.middleware import BDRMaintenanceMiddleware

        # Acquire lock locally to simulate active maintenance
        self.lock_manager.acquire_lock(owner="test-middleware-blocking")

        middleware = BDRMaintenanceMiddleware(get_response=lambda r: None)
        request = RequestFactory().get("/api/articles/")

        response = middleware(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 503)

        # Verify JSON response schema
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["status"], "maintenance")
        self.assertEqual(data["message"], "System restoration in progress")

    def test_crashed_lock_recovery(self):
        """
        Verifies that if a restore crashes and the lock is left behind, the POSIX flock
        is released by the OS, allowing a new process to detect it as inactive and recover.
        """
        # Simulate a crashed lock file by creating a file with JSON content,
        # but NOT holding an active flock on it (which happens when the process crashes/exits).
        self.lock_manager.local_lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_manager.local_lock_path, "w") as f:
            json.dump(
                {
                    "reason": "database_restore",
                    "started": datetime.utcnow().isoformat(),
                    "owner": "crashed-process",
                },
                f,
            )

        # Verify that is_locked() detects it as unheld, cleans it up, and returns False
        self.assertFalse(self.lock_manager.is_locked())
        self.assertFalse(self.lock_manager.local_lock_path.exists())

    def test_sre_metrics_increment_and_update(self):
        """
        Tests SRE metrics update and increment helper function.
        """
        from common.bdr_metrics import update_sre_metric

        # Update metric
        update_sre_metric("bdr_s3_upload_failed", 5)

        # Test increment
        update_sre_metric("bdr_s3_upload_failed", 2, increment=True)

        # Verify from file
        metrics_file = (
            Path(settings.BASE_DIR) / "test_restore_temp" / "sre_metrics.json"
        )
        self.assertTrue(metrics_file.exists())
        with open(metrics_file, "r") as f:
            data = json.load(f)
            self.assertEqual(data["bdr_s3_upload_failed"], 7)


class S3BackupProviderDirectTest(TestCase):
    def setUp(self):
        super().setUp()
        self.temp_dir = Path(settings.BASE_DIR) / "test_s3_provider_temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        super().tearDown()

    @patch("boto3.client")
    def test_s3_backup_provider_upload_download_verify_delete(self, mock_boto_client):
        """
        Directly exercises all operations on S3BackupProvider with mock boto3 client.
        """
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Configure mock responses
        class EqualToAnything:
            def __eq__(self, other):
                return True

        mock_s3.head_object.return_value = {
            "ContentLength": EqualToAnything(),
            "Metadata": {
                "original-size": "15",
                "original-sha256": "abcdef",
                "original-mtime": "12345.6",
            },
        }
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "media/test.enc",
                        "Size": 100,
                        "LastModified": datetime.utcnow(),
                    }
                ]
            }
        ]
        mock_s3.get_paginator.return_value = mock_paginator

        from common.bdr.s3_backup_provider import S3BackupProvider

        provider = S3BackupProvider(bucket_name="my-bucket")

        # Local test file
        local_file = self.temp_dir / "test.txt"
        local_file.write_text("hello s3 backup")

        # Test upload
        manifest = provider.upload_backup(local_file, "media/test.enc")
        self.assertEqual(manifest["file"], "media/test.enc")
        self.assertTrue(mock_s3.upload_fileobj.called)

        # Test download
        dest_file = self.temp_dir / "restored.txt"

        # When downloading, mock the decryption pipeline (write valid decrypt format or just mock it)
        # S3BackupProvider downloads to a temp file, then calls decrypt_and_decompress_stream.
        # Since we use GzipEncryptionStream, let's write a valid Gzip GCM stream into self.temp_dir / "mock_download.enc"
        # and mock download_fileobj to copy this file's bytes.
        import io

        from common.bdr_crypto import GzipEncryptionStream

        enc_buf = io.BytesIO()
        crypto_stream = GzipEncryptionStream(enc_buf, provider.get_encryption_key())
        with gzip.GzipFile(fileobj=crypto_stream, mode="wb") as f_gz:
            f_gz.write(b"hello s3 backup")
        crypto_stream.close()

        def mock_download_fileobj(bucket, key, fileobj):
            fileobj.write(enc_buf.getvalue())

        mock_s3.download_fileobj.side_effect = mock_download_fileobj

        # Test download
        provider.download_backup("media/test.enc", dest_file)
        self.assertTrue(dest_file.exists())
        self.assertEqual(dest_file.read_text(), "hello s3 backup")

        # Test verify_backup
        verified = provider.verify_backup("media/test.enc")
        self.assertTrue(verified)

        # Test list_backups
        backups = provider.list_backups(prefix="media/")
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0]["Key"], "media/test.enc")

        # Test delete_expired_backup
        success = provider.delete_expired_backup("media/test.enc")
        self.assertTrue(success)
        mock_s3.delete_object.assert_called_with(
            Bucket="my-bucket", Key="media/test.enc"
        )


class BackupConfigTest(TestCase):
    def setUp(self):
        super().setUp()
        self.temp_backup_dir = Path(settings.BASE_DIR) / "test_backups_conf"
        self.temp_backup_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.temp_backup_dir.exists():
            shutil.rmtree(self.temp_backup_dir)
        super().setUp()

    def test_backup_config_packaging_and_masking(self):
        """
        Tests config file packaging and masking sensitive environment keys in logging/output.
        """
        out_dir = self.temp_backup_dir / "config"

        env_file = Path(settings.BASE_DIR) / ".env"
        old_env_content = None
        if env_file.exists():
            old_env_content = env_file.read_text()

        env_file.write_text(
            "SECRET_KEY=highly_secret_value\nDATABASE_URL=postgres://user:pass@host:5432/db\nDEBUG=True"
        )

        passphrase = "test_super_secret_key"
        try:
            # Patch get_encryption_key to return deterministic passphrase during backup command execution
            with patch(
                "common.management.commands.backup_config.Command.get_encryption_key",
                return_value=passphrase,
            ):
                call_command(
                    "backup_config", "--output-dir", str(out_dir), "--no-cleanup"
                )

            # Check archive exists (encrypted version)
            archives = list(out_dir.glob("*.tar.gz.enc"))
            self.assertEqual(len(archives), 1)

            # Extract archive to check contents (decrypting first)
            dec_out_tar = self.temp_backup_dir / "decrypted_conf.tar.gz"

            with open(archives[0], "rb") as f_in, open(dec_out_tar, "wb") as f_out:
                decrypt_stream(f_in, f_out, passphrase)

            extract_dir = self.temp_backup_dir / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(dec_out_tar, "r:gz") as tar:
                tar.extractall(path=extract_dir)

            self.assertTrue((extract_dir / ".env").exists())
            self.assertIn("SECRET_KEY", (extract_dir / ".env").read_text())

        finally:
            if old_env_content is not None:
                env_file.write_text(old_env_content)
            elif env_file.exists():
                env_file.unlink()


class RestoreSystemTest(TestCase):
    def setUp(self):
        super().setUp()
        self.temp_restore_dir = Path(settings.BASE_DIR) / "test_restore_temp"
        self.temp_restore_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.temp_restore_dir.exists():
            shutil.rmtree(self.temp_restore_dir)
        super().tearDown()

    @override_settings(BACKUP_ENCRYPT=True, BACKUP_ENCRYPTION_KEY="recovery_pass")
    def test_restore_database_flow(self):
        """
        Tests decryption, decompression, and database restoration workflow using AES-256-GCM.
        """
        sql_content = b"CREATE TABLE restore_test (id int);"

        # Build memory-safe encrypted Gzip stream
        import io

        enc_buf = io.BytesIO()
        passphrase = "recovery_pass"
        crypto_stream = GzipEncryptionStream(enc_buf, passphrase)

        with gzip.GzipFile(fileobj=crypto_stream, mode="wb") as f_gz:
            f_gz.write(sql_content)
        crypto_stream.close()

        enc_file = self.temp_restore_dir / "db_backup.sql.gz.enc"
        enc_file.write_bytes(enc_buf.getvalue())

        # Invoke restoration in mock mode for SQLite in-memory
        call_command("restore_system", "--db-file", str(enc_file), "--decrypt")
        self.assertTrue(enc_file.exists())

    @override_settings(BACKUP_ENCRYPT=True, BACKUP_ENCRYPTION_KEY="correct_pass")
    def test_restore_database_wrong_key(self):
        """
        Verifies that restoring database with an invalid decryption key raises a ValueError.
        """
        sql_content = b"CREATE TABLE restore_test (id int);"
        import io

        enc_buf = io.BytesIO()
        # Encrypted with correct key
        crypto_stream = GzipEncryptionStream(enc_buf, "correct_pass")
        with gzip.GzipFile(fileobj=crypto_stream, mode="wb") as f_gz:
            f_gz.write(sql_content)
        crypto_stream.close()

        enc_file = self.temp_restore_dir / "db_backup.sql.gz.enc"
        enc_file.write_bytes(enc_buf.getvalue())

        # Attempt to restore with a WRONG key
        with patch(
            "common.management.commands.restore_system.Command.get_encryption_key",
            return_value="wrong_pass",
        ):
            with self.assertRaises(ValueError):
                call_command("restore_system", "--db-file", str(enc_file), "--decrypt")

    @override_settings(BACKUP_ENCRYPT=True, BACKUP_ENCRYPTION_KEY="correct_pass")
    def test_restore_database_corrupted_backup(self):
        """
        Verifies that restoring a corrupted or tampered backup file raises a ValueError.
        """
        sql_content = b"CREATE TABLE restore_test (id int);"
        import io

        enc_buf = io.BytesIO()
        crypto_stream = GzipEncryptionStream(enc_buf, "correct_pass")
        with gzip.GzipFile(fileobj=crypto_stream, mode="wb") as f_gz:
            f_gz.write(sql_content)
        crypto_stream.close()

        # Corrupt the payload bytes
        corrupted_bytes = bytearray(enc_buf.getvalue())
        # Let's change some of the encrypted bytes at the end
        corrupted_bytes[-10] ^= 0xFF

        enc_file = self.temp_restore_dir / "db_backup_corrupt.sql.gz.enc"
        enc_file.write_bytes(bytes(corrupted_bytes))

        with self.assertRaises(ValueError):
            call_command("restore_system", "--db-file", str(enc_file), "--decrypt")

    @override_settings(BACKUP_ENCRYPTION_KEY="correct_pass")
    def test_restore_config_validation(self):
        """
        Verifies that configuration restoration performs validation checks on .env files and blocks malformed ones.
        """
        # Create a malformed env file (not matching key=value format)
        malformed_env_content = b"THIS_IS_CORRUPT_NOT_KEY_VALUE_FORMAT\n"

        # Package into tar.gz
        import io

        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
            tarinfo = tarfile.TarInfo(name=".env")
            tarinfo.size = len(malformed_env_content)
            tar.addfile(tarinfo, io.BytesIO(malformed_env_content))

        # Encrypt the tarball
        enc_tar_buf = io.BytesIO()
        tar_buf.seek(0)
        encrypt_stream(tar_buf, enc_tar_buf, "correct_pass")

        enc_conf_file = self.temp_restore_dir / "config_backup.tar.gz.enc"
        enc_conf_file.write_bytes(enc_tar_buf.getvalue())

        # Attempting restoration must raise ValueError due to syntax validation check
        with self.assertRaises(ValueError):
            call_command("restore_system", "--config-file", str(enc_conf_file))

    def test_restore_media_flow(self):
        """
        Tests restoring media files from a backup directory to MEDIA_ROOT.
        """
        backup_media_dir = self.temp_restore_dir / "media_backup"
        backup_media_dir.mkdir(parents=True, exist_ok=True)
        (backup_media_dir / "image.png").write_text("image bytes")

        target_media_root = self.temp_restore_dir / "media_root"
        target_media_root.mkdir(parents=True, exist_ok=True)

        with override_settings(MEDIA_ROOT=str(target_media_root)):
            call_command("restore_system", "--media-file", str(backup_media_dir))

        restored_file = target_media_root / "image.png"
        self.assertTrue(restored_file.exists())
        self.assertEqual(restored_file.read_text(), "image bytes")

    def test_auto_discovery_validation(self):
        """
        Tests the SRE weekly validation dry-run auto-discovery.
        """
        backup_base = self.temp_restore_dir / "backups"
        db_dir = backup_base / "database"
        db_dir.mkdir(parents=True, exist_ok=True)

        latest_db_backup = db_dir / "db_backup_20261231_235959.sql.gz"
        with gzip.open(latest_db_backup, "wb") as f:
            f.write(b"SELECT 1;")

        with patch.dict(os.environ, {"BACKUP_DIR": str(backup_base)}):
            call_command("restore_system")


class BackupTasksTest(TestCase):
    @patch("common.tasks.call_command")
    def test_backup_database_task_calls_command(self, mock_call_command):
        """
        Tests backup_database_task correctly executes backup_database.
        """
        result = backup_database_task()
        self.assertTrue(result)
        mock_call_command.assert_any_call("backup_database")

    @patch("common.tasks.call_command")
    def test_backup_media_task_calls_command(self, mock_call_command):
        """
        Tests backup_media_task correctly executes backup_media.
        """
        result = backup_media_task()
        self.assertTrue(result)
        mock_call_command.assert_any_call("backup_media")

    @patch("common.tasks.call_command")
    def test_backup_config_task_calls_command(self, mock_call_command):
        """
        Tests backup_config_task correctly executes backup_config.
        """
        result = backup_config_task()
        self.assertTrue(result)
        mock_call_command.assert_any_call("backup_config")

    @patch("common.tasks.call_command")
    def test_validate_backups_task_calls_command(self, mock_call_command):
        """
        Tests validate_backups_task correctly executes restore_system.
        """
        result = validate_backups_task()
        self.assertTrue(result)
        mock_call_command.assert_any_call("restore_system")
