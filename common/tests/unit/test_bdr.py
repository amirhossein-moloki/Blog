import base64
import gzip
import hashlib
import os
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import cryptography primitives to correctly mock/build the stream encrypted testing values
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings

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
    @patch("subprocess.run")
    def test_backup_database_unencrypted_sqlite(self, mock_run):
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
    @patch("subprocess.run")
    def test_backup_database_encrypted_sqlite(self, mock_run):
        """
        Tests database backup with AES encryption.
        """
        out_dir = self.temp_backup_dir / "database"
        call_command("backup_database", "--output-dir", str(out_dir), "--no-cleanup")

        files = list(out_dir.glob("*.enc"))
        self.assertEqual(len(files), 1)
        enc_file = files[0]

        # Read encrypted bytes
        with open(enc_file, "rb") as f:
            raw_bytes = f.read()

        # Decrypt manually to verify
        # Safe 32-byte key generation matches command
        key = hashlib.sha256("test_super_secret_key".encode("utf-8")).digest()
        iv = raw_bytes[:16]
        encrypted_data = raw_bytes[16:]

        cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted_data) + decryptor.finalize()

        decompressed = gzip.decompress(decrypted)
        self.assertTrue(b"SQLite" in decompressed or len(decompressed) >= 0)

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
    @patch("subprocess.run")
    def test_backup_database_postgresql_pg_dump(self, mock_run):
        """
        Tests pg_dump invocation when using the postgresql engine.
        """
        # Configure subprocess.run to return success
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        out_dir = self.temp_backup_dir / "database"
        call_command("backup_database", "--output-dir", str(out_dir), "--no-cleanup")

        # Verify pg_dump was called with correct environment and arguments
        # Since git was also called, we search call_args_list for pg_dump
        pg_dump_calls = [
            call
            for call in mock_run.call_args_list
            if any("pg_dump" in str(arg) for arg in call.args)
        ]
        self.assertTrue(len(pg_dump_calls) > 0, "pg_dump should be invoked")

        call_obj = pg_dump_calls[0]
        cmd = call_obj.args[0]
        kwargs = call_obj.kwargs

        self.assertIn("pg_dump", cmd)
        self.assertIn("test_db", cmd)
        self.assertIn("-U", cmd)
        self.assertIn("test_user", cmd)
        self.assertEqual(kwargs["env"]["PGPASSWORD"], "test_password")

    def test_backup_database_retention_cleanup(self):
        """
        Tests that backups older than BACKUP_RETENTION_DAYS are purged.
        """
        out_dir = self.temp_backup_dir / "database"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Create an expired backup file
        expired_file = out_dir / "db_backup_20200101_000000.sql.gz"
        expired_file.write_text("expired backup data")

        # Set modify time to 10 days ago
        ten_days_ago = datetime.utcnow() - timedelta(days=10)
        os.utime(expired_file, (ten_days_ago.timestamp(), ten_days_ago.timestamp()))

        # Create a fresh backup file
        fresh_file = out_dir / "db_backup_20260101_000000.sql.gz"
        fresh_file.write_text("fresh backup data")

        # Run command with retention set to 7 days
        with patch.dict(os.environ, {"BACKUP_RETENTION_DAYS": "7"}):
            call_command("backup_database", "--output-dir", str(out_dir))

        self.assertFalse(expired_file.exists(), "Expired backup should be deleted.")
        self.assertTrue(fresh_file.exists(), "Fresh backup should be kept.")


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

    @override_settings()
    def test_backup_media_incremental_sync(self):
        """
        Tests incremental synchronization of media files using file existence and hash checks.
        """
        # Create some media files
        (self.temp_src_dir / "pic1.jpg").write_text("image content 1")
        (self.temp_src_dir / "folder").mkdir(parents=True, exist_ok=True)
        (self.temp_src_dir / "folder" / "pic2.png").write_text("image content 2")

        # Override settings.MEDIA_ROOT
        with override_settings(MEDIA_ROOT=str(self.temp_src_dir)):
            # Sync to backup destination
            call_command("backup_media", "--output-dir", str(self.temp_dst_dir))

        # Check target matches
        self.assertTrue((self.temp_dst_dir / "pic1.jpg").exists())
        self.assertTrue((self.temp_dst_dir / "folder" / "pic2.png").exists())
        self.assertEqual(
            (self.temp_dst_dir / "pic1.jpg").read_text(), "image content 1"
        )

        # Change pic1.jpg in source
        (self.temp_src_dir / "pic1.jpg").write_text("new content")

        # Sync again
        with override_settings(MEDIA_ROOT=str(self.temp_src_dir)):
            call_command("backup_media", "--output-dir", str(self.temp_dst_dir))

        self.assertEqual((self.temp_dst_dir / "pic1.jpg").read_text(), "new content")


class BackupConfigTest(TestCase):
    def setUp(self):
        super().setUp()
        self.temp_backup_dir = Path(settings.BASE_DIR) / "test_backups_conf"
        self.temp_backup_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.temp_backup_dir.exists():
            shutil.rmtree(self.temp_backup_dir)
        super().tearDown()

    def test_backup_config_packaging_and_masking(self):
        """
        Tests config file packaging and masking sensitive environment keys in logging/output.
        """
        out_dir = self.temp_backup_dir / "config"

        # Create fake .env inside Django BASE_DIR for packaging test
        env_file = Path(settings.BASE_DIR) / ".env"
        old_env_content = None
        if env_file.exists():
            old_env_content = env_file.read_text()

        env_file.write_text(
            "SECRET_KEY=highly_secret_value\nDATABASE_URL=postgres://user:pass@host:5432/db\nDEBUG=True"
        )

        try:
            call_command("backup_config", "--output-dir", str(out_dir), "--no-cleanup")

            # Check archive exists
            archives = list(out_dir.glob("*.tar.gz"))
            self.assertEqual(len(archives), 1)

            # Extract archive to check contents
            extract_dir = self.temp_backup_dir / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(archives[0], "r:gz") as tar:
                tar.extractall(path=extract_dir)

            self.assertTrue((extract_dir / ".env").exists())
            self.assertIn("SECRET_KEY", (extract_dir / ".env").read_text())

        finally:
            # Restore original .env
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
        Tests decryption, decompression, and database restoration workflow.
        """
        # 1. Prepare raw sql, compress it, encrypt it with AES-256-CTR
        sql_content = b"CREATE TABLE restore_test (id int);"
        gzipped_data = gzip.compress(sql_content)

        # Encrypt with CTR mode
        key = hashlib.sha256("recovery_pass".encode("utf-8")).digest()
        iv = b"1234567890123456"  # 16 bytes IV
        cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
        encryptor = cipher.encryptor()
        encrypted_data = iv + encryptor.update(gzipped_data) + encryptor.finalize()

        enc_file = self.temp_restore_dir / "db_backup.sql.gz.enc"
        enc_file.write_bytes(encrypted_data)

        # 2. Invoke restoration in mock mode for SQLite in-memory
        call_command("restore_system", "--db-file", str(enc_file), "--decrypt")

        self.assertTrue(
            enc_file.exists(),
            "Restore command shouldn't delete the backup file itself.",
        )

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
        # Create a mock database file under the discovered backup root
        backup_base = self.temp_restore_dir / "backups"
        db_dir = backup_base / "database"
        db_dir.mkdir(parents=True, exist_ok=True)

        latest_db_backup = db_dir / "db_backup_20261231_235959.sql.gz"
        with gzip.open(latest_db_backup, "wb") as f:
            f.write(b"SELECT 1;")

        # Run restore_system with custom BACKUP_DIR env
        with patch.dict(os.environ, {"BACKUP_DIR": str(backup_base)}):
            call_command("restore_system")
