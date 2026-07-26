# Commands & Server Testing Guide | راهنمای دستورات و تست روی سرور

Welcome to the comprehensive command reference and testing guide for the Blog Platform.
به راهنمای جامع دستورات و مستندات تست روی سرور برای پروژه پلتفرم وبلاگ خوش آمدید.

---

## Table of Contents | فهرست مطالب
1. [Docker & Container Commands | دستورات داکر و کانتینر](#1-docker--container-commands--دستورات-داکر-و-کانتینر)
2. [Django Management Commands | دستورات مدیریتی جنگو](#2-django-management-commands--دستورات-مدیریتی-جنگو)
3. [Celery & Task Queue Commands | دستورات سلری و صف تسک‌ها](#3-celery--task-queue-commands--دستورات-سلری-و-صف-تسکها)
4. [Backup & Disaster Recovery (BDR) | سیستم پشتیبان‌گیری و بازیابی](#4-backup--disaster-recovery-bdr--سیستم-پشتیبانگیری-و-بازیابی)
5. [How to Test on the Server | آموزش کامل تست روی سرور](#5-how-to-test-on-the-server--آموزش-کامل-تست-روی-سرور)

---

## 1. Docker & Container Commands | دستورات داکر و کانتینر

These commands control the multi-container application stack on local and production environments.
این دستورات برای مدیریت کانتینرهای پروژه در محیط‌های توسعه محلی و سرورهای تولیدی استفاده می‌شوند.

*   **Build and Start all services (detached mode) | ساخت مجدد و اجرای تمام سرویس‌ها در پس‌زمینه:**
    ```bash
    docker-compose up --build -d
    ```

*   **Stop and remove containers | متوقف کردن و حذف کانتینرها:**
    ```bash
    docker-compose down
    ```

*   **View combined logs of all services | مشاهده لاگ‌های تمام سرویس‌ها به صورت زنده:**
    ```bash
    docker-compose logs -f
    ```

*   **View logs of a specific service (e.g., Django web container) | مشاهده لاگ‌های یک سرویس خاص (مثلاً وب جنگو):**
    ```bash
    docker-compose logs -f web
    ```

*   **Run an interactive shell inside Django container | اجرای خط فرمان تعاملی داخل کانتینر جنگو:**
    ```bash
    docker-compose exec web bash
    ```

---

## 2. Django Management Commands | دستورات مدیریتی جنگو

Standard and custom Django administrative commands. Use `docker-compose exec web <command>` if running in a containerized environment.
دستورات استاندارد و سفارشی مدیریتی جنگو. در صورتی که پروژه روی داکر در حال اجراست، دستورات را با پیشوند `docker-compose exec web` اجرا کنید.

*   **Run migrations | اعمال مهاجرت‌های پایگاه داده:**
    ```bash
    # Local / محلی
    python manage.py migrate

    # Inside Docker / روی کانتینر داکر
    docker-compose exec web python manage.py migrate
    ```

*   **Create a new database migration | ساخت فایل‌های مهاجرت جدید:**
    ```bash
    # Local / محلی
    python manage.py makemigrations

    # Inside Docker / روی کانتینر داکر
    docker-compose exec web python manage.py makemigrations
    ```

*   **Create superuser | ساخت کاربر ادمین ارشد:**
    ```bash
    # Local / محلی
    python manage.py createsuperuser

    # Inside Docker / روی کانتینر داکر
    docker-compose exec web python manage.py createsuperuser
    ```

*   **Open Django interactive shell | ورود به شل تعاملی جنگو:**
    ```bash
    # Local / محلی
    python manage.py shell

    # Inside Docker / روی کانتینر داکر
    docker-compose exec web python manage.py shell
    ```

*   **Collect static files | جمع‌آوری فایل‌های استاتیک:**
    ```bash
    # Local / محلی
    python manage.py collectstatic --noinput

    # Inside Docker / روی کانتینر داکر
    docker-compose exec web python manage.py collectstatic --noinput
    ```

*   **Generate OpenAPI Schema | تولید فایل شمای مستندات API:**
    ```bash
    # Local / محلی
    python manage.py spectacular --file schema_generated.yml

    # Inside Docker / روی کانتینر داکر
    docker-compose exec web python manage.py spectacular --file schema_generated.yml
    ```

---

## 3. Celery & Task Queue Commands | دستورات سلری و صف تسک‌ها

These run background workers and scheduled beat processes.
این دستورات برای اجرای ورکرها و زمان‌بندی تسک‌های پس‌زمینه پروژه استفاده می‌شوند.

*   **Run Celery worker (all queues) | اجرای ورکر سلری برای تمام صف‌ها:**
    ```bash
    # Local / محلی
    celery -A blog worker -l info

    # Inside Docker (Done automatically by celery containers, but for manual check) / روی داکر به صورت دستی
    docker-compose exec web celery -A blog worker -l info
    ```

*   **Run Celery worker for specific priority queues | اجرای ورکر سلری برای صف‌های اولویت‌بندی شده خاص:**
    ```bash
    celery -A blog worker -Q high_priority,default,low_priority -l info
    ```

*   **Run Celery Beat (scheduler) | اجرای زمان‌بند سلری (بیت):**
    ```bash
    # Local / محلی
    celery -A blog beat -l info
    ```

---

## 4. Backup & Disaster Recovery (BDR) | سیستم پشتیبان‌گیری و بازیابی

The platform's highly resilient backup and disaster recovery commands.
دستورات پیشرفته و امنیتی سیستم پشتیبان‌گیری و بازیابی بحران برای پایگاه داده، رسانه‌ها و پیکربندی‌های سیستم.

*   **Backup database (creates stream encrypted/compressed dump) | پشتیبان‌گیری امن و فشرده از پایگاه داده:**
    ```bash
    # Local / محلی
    python manage.py backup_database

    # Inside Docker / روی کانتینر داکر
    docker-compose exec web python manage.py backup_database
    ```

*   **Backup media directory | پشتیبان‌گیری از پوشه فایل‌های رسانه‌ای:**
    ```bash
    # Local / محلی
    python manage.py backup_media

    # Inside Docker / روی کانتینر داکر
    docker-compose exec web python manage.py backup_media
    ```

*   **Backup configuration files (encrypted `.env`, Nginx, Compose files) | پشتیبان‌گیری رمزنگاری‌شده از تنظیمات و پیکربندی‌ها:**
    ```bash
    # Local / محلی
    python manage.py backup_config

    # Inside Docker / روی کانتینر داکر
    docker-compose exec web python manage.py backup_config
    ```

*   **Restore system (triggers the 8-step disaster recovery workflow) | بازیابی کامل کل سیستم (فعال‌سازی جریان ۸ مرحله‌ای بازیابی بحران):**
    > ⚠️ **CRITICAL WARNING:** This is a destructive operation that drops current schemas and recovers the system to a clean state.
    > ⚠️ **هشدار حیاتی:** این دستور یک فرآیند مخرب است که کلیه جداول فعلی را پاک کرده و سیستم را با استفاده از پشتیبان‌ها بازسازی می‌کند.
    ```bash
    # Local / محلی
    python manage.py restore_system

    # Inside Docker / روی کانتینر داکر
    docker-compose exec web python manage.py restore_system
    ```

---

## 5. How to Test on the Server | آموزش کامل تست روی سرور

To perform health audits and verify that your server is running perfectly with zero regressions, follow this step-by-step procedure.
برای انجام بازرسی سلامت سیستم و اطمینان از عملکرد عالی و بدون مشکل پروژه روی سرور اصلی، مراحل زیر را گام‌به‌گام دنبال کنید.

### Step 5.1: SSH to your Server | اتصال به سرور از طریق SSH
First, connect to your server machine where the Docker containers are deployed:
ابتدا از طریق کلاینت SSH به سرور متصل شوید:
```bash
ssh <USERNAME>@<SERVER_IP_ADDRESS>
```

Navigate to your active project repository root directory:
به دایرکتوری اصلی پروژه بروید:
```bash
cd /path/to/blog-backend
```

---

### Step 5.2: Execute Django Automated Tests | اجرای تست‌های خودکار جنگو
You can run all backend unit and integration tests inside the running Django container without interrupting the live service.
شما می‌توانید تمام تست‌های واحد (Unit) و یکپارچه‌سازی (Integration) را مستقیماً درون کانتینر در حال اجرای جنگو اجرا کنید بدون اینکه نیازی به توقف سرویس‌دهی باشد.

*   **Run all tests in the suite | اجرای کلیه تست‌های پروژه:**
    > 💡 **Note:** `STATIC_API_KEY` must be passed for authentication-related tests to run successfully.
    > 💡 **نکته:** جهت اجرای صحیح تست‌های مربوط به احراز هویت، متغیر محیطی `STATIC_API_KEY` باید مقداردهی شود.
    ```bash
    docker-compose exec web sh -c "STATIC_API_KEY=test_static_api_key python manage.py test"
    ```

*   **Run specific App tests (e.g. Users, Posts) | اجرای تست‌های یک اپلیکیشن خاص:**
    ```bash
    docker-compose exec web sh -c "STATIC_API_KEY=test_static_api_key python manage.py test users"
    docker-compose exec web sh -c "STATIC_API_KEY=test_static_api_key python manage.py test posts"
    ```

*   **Run the Backup & Disaster Recovery (BDR) isolated suite | اجرای اختصاصی تست‌های سیستم پشتیبان‌گیری و بازیابی بحران:**
    ```bash
    docker-compose exec web sh -c "STATIC_API_KEY=test_static_api_key python manage.py test common.tests.unit.test_bdr"
    ```

---

### Step 5.3: Check Test Coverage on the Server | بررسی درصد پوشش تست‌ها (Coverage)
To inspect the percentage of code lines covered by tests on the active server:
برای دیدن درصد دقیق پوشش کدها توسط تست‌ها در سرور فعال:
```bash
# 1. Run tests with coverage collection / اجرای تست‌ها به همراه جمع‌آوری گزارش پوشش
docker-compose exec web sh -c "STATIC_API_KEY=test_static_api_key coverage run manage.py test"

# 2. View coverage summary report / مشاهده خلاصه گزارش پوشش کدها
docker-compose exec web sh -c "coverage report"
```

---

### Step 5.4: Test and Verify using Postman / Newman (API Tests) | تست با ابزار پستمن روی سرور
If you have Newman (the command-line runner for Postman) installed on the server, or wish to trigger integrated Postman API calls:
در صورتی که نیومن (Newman) را روی سرور نصب دارید یا می‌خواهید تست‌های API پستمن را فراخوانی کنید:

*   **Run active API Postman Collection | اجرای کالکشن تست‌های وب‌سرویس پستمن:**
    ```bash
    newman run postman_collection.json -e postman_environment.json
    ```

---

### Step 5.5: Real-time Troubleshooting & Diagnostic Logs | خطایابی و لاگ‌های سیستم روی سرور
To observe live database connections, task execution, or incoming API traffic errors on the server, keep a terminal open watching:
برای عیب‌یابی در لحظه اتصال به پایگاه داده، صف‌های سلری یا ترافیک وب ادمین، از دستورات زیر استفاده کنید:

```bash
# Watch live Django request logs / مشاهده زنده لاگ‌های وب سرور جنگو
docker-compose logs -f web

# Watch live Celery task executions / مشاهده زنده فرآیند تسک‌های پس‌زمینه سلری
docker-compose logs -f celery_default celery_high_priority
```
