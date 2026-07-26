# Environment Variables Documentation

The Blog Platform uses environment variables for configuration, following the "Twelve-Factor App" principles. These can be defined in a `.env` file in the root directory.

---

## 1. Django Core Settings

| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `SECRET_KEY` | String | Yes | - | Security key for cryptographic signing, session management, and encryption. Keep extremely secret in production. |
| `DEBUG` | Boolean | No | `False` | Enables/disables Django debug mode. Never enable in production. |
| `ALLOWED_HOSTS` | CSV | No | `localhost,127.0.0.1` | Comma-separated list of host/domain names that this Django site can serve. |
| `DOMAIN` | String | No | `localhost` | The primary domain under which the application is served. |
| `SITE_NAME` | String | No | `Blog Platform` | The name of the platform, displayed in administration and emails. |
| `FRONTEND_URL` | URL | No | `http://localhost:3000` | Full URL of the frontend client application. |
| `STATIC_API_KEY` | String | Yes | - | Secret static token used for API Key authentication (`X-API-Key` header). Must be set for the app to start and for authentication-dependent tests to pass. |

---

## 2. Security, CORS & CSRF

| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `CORS_ALLOWED_ORIGINS` | CSV | No | - | Comma-separated list of origins allowed to perform cross-site resource requests. |
| `CORS_ALLOW_ALL_ORIGINS` | Boolean | No | `False` | Bypasses CORS origin checks if set to `True` (useful for local development only). |
| `CSRF_TRUSTED_ORIGINS` | CSV | No | - | Comma-separated list of origins trusted to submit state-changing POST/PUT requests (CSRF protection). |

---

## 3. Database Settings

| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | URL | Yes | - | PostgreSQL connection URL (e.g., `postgres://user:pass@db:5432/dbname`). If configured, takes precedence over other POSTGRES_* settings. |
| `POSTGRES_DB` | String | No | `blog_db` | Database name. Used by both Django and Docker Compose. |
| `POSTGRES_USER` | String | No | `db_user` | Database connection username. |
| `POSTGRES_PASSWORD` | String | No | - | Database connection password. |
| `POSTGRES_HOST` | String | No | `db` | Database host service address. |
| `POSTGRES_PORT` | Integer | No | `5432` | Database host port. |

---

## 4. Enterprise Caching & Redis Settings

| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `USE_REDIS` | Boolean | No | `False` | Enables Redis as the central backing engine for the Enterprise Caching Subsystem and Django Channels layers. If `False`, falls back to local memory (`LocMemCache`). |
| `REDIS_URL` | URL | No | `redis://cache:6379/0` | Connection string to the Redis server instance. |

---

## 5. Celery and Task Queue Settings

| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `CELERY_WORKER_MAX_TASKS_PER_CHILD` | Integer | No | `100` | Limits tasks per worker child process to prevent unexpected memory leaks in long-running environments. |
| `CELERY_TASK_SOFT_TIME_LIMIT` | Integer | No | `900` | Soft execution timeout limit in seconds. |
| `CELERY_TASK_TIME_LIMIT` | Integer | No | `960` | Hard execution timeout limit in seconds. |
| `CELERY_VISIBILITY_TIMEOUT` | Integer | No | `1200` | Visibility timeout for task delivery acknowledgement. |
| `CELERY_RESULT_EXPIRES_HOURS` | Integer | No | `24` | Expiration time of celery results from backend database. |

---

## 6. Media & Cloud Storage Settings

| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `STORAGE_BACKEND` | String | No | `local` | `local` for filesystem storage, or `s3` for S3-compatible cloud storage backend (e.g. AWS or ParsPack). |
| `MEDIA_URL` | String | No | `/media/` | URL path prefix for accessing uploaded media files. |
| `AWS_ACCESS_KEY_ID` | String | If S3 | - | Access Key ID for S3 bucket connection. |
| `AWS_SECRET_ACCESS_KEY` | String | If S3 | - | Secret Access Key for S3 bucket connection. |
| `AWS_STORAGE_BUCKET_NAME` | String | If S3 | - | The S3 bucket name where files are stored. |
| `AWS_S3_REGION_NAME` | String | No | - | S3 region identifier (e.g. `us-east-1`). |
| `AWS_S3_ENDPOINT_URL` | URL | No | - | S3 endpoint URL (Mandatory when using local providers like ParsPack). |
| `AWS_S3_CUSTOM_DOMAIN` | String | No | - | Custom domain mapped to serve assets directly from CDN/S3. |

---

## 7. Enterprise Backup & Disaster Recovery (BDR) Subsystem

These variables govern the scheduling, retention, storage engines, and security of the BDR system.

| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `BACKUP_DIR` | String | No | `/app/backups` | Absolute local path where database, media, and config backups are streamingly saved. |
| `BACKUP_RETENTION_DAYS` | Integer | No | `7` | Retention threshold in days for basic backups. |
| `BACKUP_STORAGE` | String | No | `local` | Target storage engine for backups. Options: `local`, `s3`, or `local,s3`. |
| `BACKUP_ENCRYPT` | Boolean | No | `False` | If `True`, enables stream-based AES-256-GCM encryption for database and configuration backups. Requires `BACKUP_ENCRYPTION_KEY` to be configured. |
| `BACKUP_ENCRYPTION_KEY` | String | If Encrypted | - | Passphrase of high entropy used as the master secret for PBKDF2 HMAC-SHA256 key derivation. If not set, falls back to `SECRET_KEY`. |
| `BACKUP_OFFSITE_ENABLED` | Boolean | No | `False` | Toggles whether backup commands attempt to push encrypted copies to the offsite S3-compatible bucket. |
| `BACKUP_OFFSITE_REQUIRED` | Boolean | No | `False` | If `True` (highly recommended for Production), makes offsite S3 uploads strictly mandatory. Any failure or omission raises a hard `ImproperlyConfigured` or critical exit state. |

---

## 8. Email Configuration

| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `EMAIL_BACKEND` | String | No | `django.core.mail.backends.smtp.EmailBackend` | Backend for email delivery. Use `django.core.mail.backends.console.EmailBackend` for development. |
| `EMAIL_HOST` | String | No | `localhost` | Outgoing SMTP server address. |
| `EMAIL_PORT` | Integer | No | `587` | Outgoing SMTP server port. |
| `EMAIL_USE_TLS` | Boolean | No | `True` | Employs TLS connection security. |
| `EMAIL_HOST_USER` | String | No | - | Username for SMTP authentication. |
| `EMAIL_HOST_PASSWORD` | String | No | - | Password for SMTP authentication. |
| `DEFAULT_FROM_EMAIL` | String | No | `webmaster@localhost` | Sender address used for automated system emails. |

---

## Security Implications & Best Practices

- **Never commit `.env` files:** The `.env` contains critical database passwords, encryption keys, and S3 secrets. It should be added to `.gitignore`.
- **Set `DEBUG=False` in Production:** Enabling `DEBUG=True` exposes secret environment variables, system information, and database tables on error traceback pages.
- **Set a Unique `BACKUP_ENCRYPTION_KEY`:** Never use Django's `SECRET_KEY` as the backup encryption key in production. If the web container is compromised but the backup server remains separate, attackers should not be able to decrypt database backups without the distinct backup key.
