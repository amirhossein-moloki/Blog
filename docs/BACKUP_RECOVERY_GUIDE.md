# Backup & Disaster Recovery (BDR) Guide
# راهنمای جامع پشتیبان‌گیری و بازیابی فاجعه (BDR)

Welcome to the comprehensive SRE and Administrator guide for the Enterprise Backup & Disaster Recovery (BDR) subsystem. This document provides clear tutorials on utilizing the backup subsystem, all management commands, and complete procedures for testing and validating backups on the server.

به راهنمای جامع مدیریت و راهبری سیستم پشتیبان‌گیری و بازیابی فاجعه خوش آمدید. این سند شامل آموزش استفاده، معرفی کامل دستورات مدیریتی و همچنین فرآیند جامع تست و اعتبارسنجی بکاپ‌ها روی سرور می‌باشد.

---

## 1. Overview of BDR Commands
## ۱. مرور کلی دستورات سیستم پشتیبان‌گیری

The system features four central Django management commands that can be invoked within the container:
سیستم از چهار دستور مدیریتی اصلی در جنگو تشکیل شده است که درون کانتینر قابل اجرا هستند:

1. `backup_database`: Streams and backs up the PostgreSQL database with compression and encryption.
   - پشتیبان‌گیری جریانی از پایگاه‌داده همراه با فشرده‌سازی و رمزنگاری.
2. `backup_media`: Synchronizes media files incrementally with optional off-site S3 storage.
   - همگام‌سازی افزایشی فایل‌های رسانه با ذخیره‌ساز ابری خارج از سایت S3.
3. `backup_config`: Packages and encrypts critical configurations (`.env`, `docker-compose.yml`, `nginx.conf`, etc.).
   - بسته‌بندی و رمزنگاری تنظیمات حیاتی سیستم به همراه حذف خودکار رمزها از فایل‌های لاگ.
4. `restore_system`: Decrypts, validates, and completely restores database schemas, media assets, and configurations under safe maintenance constraints.
   - رمزگشایی، اعتبارسنجی و بازیابی کامل پایگاه داده، رسانه‌ها و تنظیمات تحت تدابیر ایمنی.

---

## 2. Comprehensive Tutorial: Using Backup Commands
## ۲. آموزش جامع استفاده از دستورات پشتیبان‌گیری

All commands should be executed from the repository root inside the `web` container.
تمامی دستورات باید از ریشه پروژه درون کانتینر `web` اجرا شوند.

### A. Database Backup (`backup_database`)
### الف) پشتیبان‌گیری پایگاه‌داده

This command backs up your primary database streamingly. It writes compressed `gzip` and encrypted `AES-256-GCM` bytes directly to the storage.
این دستور از پایگاه داده اصلی شما به صورت جریانی و بدون نیاز به ذخیره موقت فایل غیررمزگذاری شده روی دیسک پشتیبان‌گیری می‌کند.

**Syntax (ساختار دستور):**
```bash
python manage.py backup_database [OPTIONS]
```

**Parameters (پارامترها):**
- `--output-dir <path>`: Directory to save the database backup (defaults to `backups/database`).
  - مسیر ذخیره‌سازی پشتیبان پایگاه‌داده (پیش‌فرض: `backups/database`).
- `--encrypt`: Force encryption on the backup file even if `BACKUP_ENCRYPT` is disabled in settings.
  - اجبار رمزگذاری فایل پشتیبان، حتی اگر در تنظیمات غیرفعال باشد.
- `--no-cleanup`: Skip GFS (Grandfather-Father-Son) retention cleanup phase.
  - عدم اجرای خودکار قانون پاک‌سازی دوره‌ای و نگهداری GFS.

**Examples (نمونه‌ها):**
```bash
# Basic backup with default settings / پشتیبان‌گیری معمولی با تنظیمات پیش‌فرض
python manage.py backup_database

# Backup with forced encryption and custom path / پشتیبان‌گیری با رمزگذاری اجباری در مسیر دلخواه
python manage.py backup_database --output-dir /app/custom_backups/db --encrypt
```

---

### B. Media Backup (`backup_media`)
### ب) پشتیبان‌گیری فایل‌های رسانه (Media)

Synchronizes media directory (`media/`) incrementally. In Production, it pushes files off-site to S3. It includes Ransomware Protected Sync to prevent deletion attacks.
این دستور پوشه رسانه‌ها را به صورت افزایشی همگام‌سازی می‌کند. در پروداکشن، فایل‌ها به S3 ارسال می‌شوند. همچنین مجهز به محافظت ضد باج‌افزار است تا از حذف ناخواسته فایل‌های بکاپ جلوگیری کند.

**Syntax (ساختار دستور):**
```bash
python manage.py backup_media [OPTIONS]
```

**Parameters (پارامترها):**
- `--output-dir <path>`: Target directory for local media sync (defaults to `backups/media`).
  - پوشه هدف برای همگام‌سازی محلی رسانه‌ها.
- `--no-cleanup`: Skip retention purge.
  - عدم اجرای پاک‌سازی فایل‌های منقضی شده.

**Examples (نمونه‌ها):**
```bash
# Sync media according to settings / همگام‌سازی رسانه‌ها بر اساس تنظیمات سیستم
python manage.py backup_media
```

---

### C. Configuration Backup (`backup_config`)
### ج) پشتیبان‌گیری تنظیمات و متغیرها

Compresses `.env`, `.env.example`, `docker-compose.yml`, `Dockerfile`, and `nginx.conf` into a secure `tar.gz.enc` file.
این دستور فایل‌های مهم پیکربندی سیستم را به صورت فشرده و رمزگذاری‌شده در قالب یک فایل امن ذخیره می‌کند.

**Syntax (ساختار دستور):**
```bash
python manage.py backup_config [OPTIONS]
```

**Parameters (پارامترها):**
- `--output-dir <path>`: Directory to save the config backup (defaults to `backups/config`).
  - پوشه هدف برای ذخیره بکاپ تنظیمات.
- `--no-cleanup`: Skip GFS purge.
  - عدم اجرای پاک‌سازی بکاپ‌های تنظیمات قدیمی.

**Examples (نمونه‌ها):**
```bash
# Backup configs and encrypt / پشتیبان‌گیری رمزگذاری‌شده از تنظیمات
python manage.py backup_config
```

---

### D. System Restoration & Dry-Run Validation (`restore_system`)
### د) فرآیند بازیابی سیستم و اعتبارسنجی

This command is the central restoration utility. It implements a strict 8-step safety workflow.
این دستور ابزار اصلی بازیابی سیستم است که یک فرآیند ۸ مرحله‌ای امن را پیاده‌سازی می‌کند.

**Syntax (ساختار دستور):**
```bash
python manage.py restore_system [OPTIONS]
```

**Parameters (پارامترها):**
- `--db-file <path>`: Path to the database backup file (`.sql.gz` or `.sql.gz.enc`).
  - مسیر فایل بکاپ پایگاه داده برای اعمال بازیابی.
- `--media-file <path>`: Path to local backup media folder to restore from.
  - مسیر پوشه بکاپ رسانه برای بازیابی فایل‌ها.
- `--config-file <path>`: Path to the encrypted config backup tarball (`.tar.gz.enc`).
  - مسیر فایل رمزگذاری شده تنظیمات برای بازیابی.
- `--decrypt`: Force decryption assuming `BACKUP_ENCRYPT` was active.
  - اجبار رمزگشایی در هنگام بازیابی.

**Examples (نمونه‌ها):**
```bash
# Complete system restore (DB + Media + Config)
# بازیابی کامل سیستم (پایگاه‌داده + رسانه‌ها + تنظیمات)
python manage.py restore_system --db-file backups/database/db_backup_20260726_120000.sql.gz.enc --media-file backups/media --config-file backups/config/config_backup_20260726_120000.tar.gz.enc
```

---

## 3. Comprehensive Tutorial: Testing Backups on the Server
## ۳. آموزش جامع تست و صحت‌سنجی بکاپ‌ها روی سرور

Ensuring your backups work before a disaster happens is a core SRE requirement. Follow these steps to test your backups on a live server without clashing with database records.

اطمینان از صحت عملکرد فرآیند بازیابی قبل از وقوع بحران، از اصول حیاتی SRE است. گام‌های زیر را برای تست بکاپ‌ها روی سرور بدون ایجاد تداخل دنبال کنید.

### Method 1: Dry-Run Restore Discovery (No State Changes)
### روش اول: اعتبارسنجی بدون اعمال تغییرات (Dry-Run Auto-Discovery)

Run `restore_system` without any arguments. It automatically scans your default directories, grabs the latest database, config, and media backups, decrypts them streamingly in memory, verifies their SHA-256 checksums, and outputs a complete SRE status report. **This does not modify the database or files.**

با اجرای دستور `restore_system` بدون هیچ پارامتری، سیستم به طور خودکار آخرین فایل‌های پشتیبان را پیدا کرده و به صورت جریانی در حافظه موقت بازگشایی و رمزگشایی می‌کند تا صحت تگ‌های رمزنگاری AES-256-GCM و یکپارچگی فایل‌ها را بسنجد. **این روش هیچ تغییری روی دیتابیس یا فایل‌های فعلی شما ایجاد نمی‌کند.**

```bash
# Execute Dry-Run Validation / اجرای اعتبارسنجی آزمایشی
python manage.py restore_system
```

**Expected Successful Console Output (خروجی موفقیت‌آمیز نمونه):**
```text
====================================================
WEEKLY RESTORE AND RECOVERY VALIDATION REPORT (DRY RUN)
====================================================
Latest Database Backup discovered: db_backup_20260726_145922.sql.gz.enc
 -> DB Backup Integrity: VALID
Latest Config Backup discovered: config_backup_20260726_145922.tar.gz.enc
 -> Config Backup Integrity: VALID (5 files packaged)
Media backup files found: 145 files synchronized.
====================================================
```

---

### Method 2: Safe Sandbox Verification (Recommended)
### روش دوم: تست کامل در محیط ایزوله (Sandbox)

To perform a 100% realistic recovery simulation without affecting production traffic:
برای شبیه‌سازی کامل فرآیند بازیابی واقعی بدون تاثیر بر ترافیک کاربران زنده سرور:

1. **Spin up a staging/test environment via Docker Compose:**
   راه‌اندازی کانتینرهای تست با استفاده از تنظیمات مجزا:
   ```bash
   # Build test environment / راه‌اندازی کانتینرهای محیط تست
   docker-compose -f docker-compose.yml -f docker-compose.test.yml up -d
   ```
2. **Execute a realistic restore:**
   اجرای فرآیند واقعی بازیابی دیتابیس، رسانه و کانفیگ در کانتینر تست:
   ```bash
   docker-compose exec web python manage.py restore_system \
     --db-file /app/backups/database/db_backup_xxxx.sql.gz.enc \
     --media-file /app/backups/media \
     --config-file /app/backups/config/config_backup_xxxx.tar.gz.enc
   ```
3. **Verify the 8-Step workflow successfully completes:**
   بررسی اتمام موفقیت‌آمیز فرآیند هشت‌مرحله‌ای بازیابی ایمن:
   - [x] Step 1: Maintenance Mode locks out write traffic / قفل موقت ترافیک ورودی
   - [x] Step 3: Postgres session termination executes / قطع کانکشن‌های فعال دیتابیس
   - [x] Step 4: Stream verification validates AES-256-GCM tag / صحت‌سنجی امضای رمزنگاری
   - [x] Step 5: Clean schema recreation drops public schema / پاکسازی کامل اسکیمای قبلی جهت جلوگیری از تداخل
   - [x] Step 6: Automatically executes migrations / اعمال روان میگریشن‌ها
   - [x] Step 7: Automatic health check validates database reachable / چک کردن زنده بودن سیستم
   - [x] Step 8: Maintenance lock is released / اتمام قفل و بازگشت ترافیک استاندارد

---

### Method 3: Inspecting Telemetry SRE Metrics
### روش سوم: بررسی لاگ‌ها و متریک‌های سیستمی SRE

SRE metrics are saved inside `/app/backups/sre_metrics.json`. Inspect this file on the server to verify the timestamp and integrity of your latest scheduled operations.

متریک‌های سیستمی به صورت مرتب در فایل `/app/backups/sre_metrics.json` روی سرور ثبت می‌شوند. با بررسی این فایل از صحت عملیات‌های زمان‌بندی شده گذشته اطمینان حاصل کنید.

```bash
# View live telemetry metrics / مشاهده متغیرهای آماری و سلامتی سیستم
cat backups/sre_metrics.json
```

**Sample JSON Telemetry Payload (نمونه متغیرهای ثبت شده):**
```json
{
    "last_successful_db_backup": "2026-07-26T14:59:22",
    "last_db_backup_duration_sec": 4.12,
    "last_db_backup_size_bytes": 1048576,
    "last_db_backup_encryption_status": "AES-256-GCM",
    "db_backup_status": "SUCCESS",
    "last_restore_validation_timestamp": "2026-07-26T15:30:00",
    "restore_validation_db_integrity": "VALID",
    "restore_validation_config_integrity": "VALID",
    "restore_validation_status": "SUCCESS"
}
```

---

## 4. Disaster Recovery Checklist
## ۴. چک‌لیست مقابله با بحران

In the event of a physical server loss or a cloud database failure, execute this checklist step-by-step:

در صورت بروز قطعی کامل سرور یا خرابی پایگاه داده، مراحل زیر را گام‌به‌گام دنبال کنید:

- [ ] **Step 1:** Prepare a fresh virtual machine / تهیه یک سرور مجازی یا ابری جدید.
- [ ] **Step 2:** Configure the environment variables in a secure `.env` file containing correct secrets and `BACKUP_ENCRYPTION_KEY`.
  - متغیرهای محیطی را در یک فایل `.env` جدید با کلید رمزگذاری صحیح تنظیم کنید.
- [ ] **Step 3:** Mount your backup volume or retrieve the latest backups from your secure ParsPack/S3 bucket.
  - بکاپ‌ها را از دیسک پشتیبان یا از سطل ابری S3 فراخوانی کنید.
- [ ] **Step 4:** Launch the Docker services via `docker-compose up -d`.
  - اجرای سرویس‌ها و کانتینرها با داکر.
- [ ] **Step 5:** Execute the restoration command:
  - اجرای دستور نهایی بازیابی کل سیستم:
  ```bash
  docker-compose exec web python manage.py restore_system \
    --db-file /app/backups/database/latest.sql.gz.enc \
    --media-file /app/backups/media \
    --config-file /app/backups/config/latest.tar.gz.enc
  ```
- [ ] **Step 6:** Inspect staging dashboard to verify application and database are completely healthy.
  - بررسی پنل ادمین و وب‌سایت برای تایید سلامت نهایی سرویس‌ها.
