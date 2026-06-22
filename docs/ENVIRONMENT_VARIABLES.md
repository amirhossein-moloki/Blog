# Environment Variables Documentation

The Blog Platform uses environment variables for configuration, following the "Twelve-Factor App" principles. These can be defined in a `.env` file in the root directory.

---

## Django Core
| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `SECRET_KEY` | String | Yes | - | Security key for cryptographic signing. |
| `DEBUG` | Boolean | No | `False` | Enables/disables debug mode. Never enable in production. |
| `ALLOWED_HOSTS` | CSV | No | `localhost,127.0.0.1` | Comma-separated list of host/domain names the site can serve. |
| `SITE_NAME` | String | No | `Blog Platform` | The title of the platform. |
| `DOMAIN` | String | No | `localhost` | The primary domain of the application. |
| `USE_CDN` | Boolean | No | `False` | Enables serving static and media files from a CDN. |
| `CDN_DOMAIN` | String | No | - | The domain of the CDN (e.g., `cdn.example.com`). |
| `FRONTEND_URL` | URL | No | `http://localhost:3000` | URL for the frontend application. |
| `STATIC_API_KEY` | String | Yes | - | Secret key used for Static API Key authentication. |

---

## Security & CORS
| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `CORS_ALLOWED_ORIGINS` | CSV | No | - | Comma-separated list of origins allowed to make cross-site requests. |
| `CORS_ALLOW_ALL_ORIGINS` | Boolean | No | `False` | If `True`, bypasses the CORS whitelist (Dev only). |
| `CSRF_TRUSTED_ORIGINS` | CSV | No | - | Trusted origins for CSRF protection. |

---

## Database
| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | URL | Yes | - | PostgreSQL connection URL (e.g., `postgres://user:pass@db:5432/db`). |
| `POSTGRES_DB` | String | No | `blog_db` | Database name (for Docker setup). |
| `POSTGRES_USER` | String | No | `db_user` | Database user. |
| `POSTGRES_PASSWORD` | String | No | - | Database password. |

---

## Redis & Celery
| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `USE_REDIS` | Boolean | No | `False` | Set to `True` to enable Redis for cache and tasks. |
| `REDIS_URL` | URL | No | `redis://cache:6379/0` | Redis server connection URL. |
| `CELERY_WORKER_MAX_TASKS_PER_CHILD` | Integer | No | `100` | Limits tasks per worker child to prevent memory leaks. |
| `CELERY_VISIBILITY_TIMEOUT` | Integer | No | `1200` | Time in seconds to wait for task acknowledgment. |

---

## Storage
| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `STORAGE_BACKEND` | String | No | `local` | `local` for filesystem, `s3` for AWS S3. |
| `AWS_ACCESS_KEY_ID` | String | If S3 | - | S3 access key. |
| `AWS_SECRET_ACCESS_KEY` | String | If S3 | - | S3 secret key. |
| `AWS_STORAGE_BUCKET_NAME` | String | If S3 | - | S3 bucket name. |
| `AWS_S3_ENDPOINT_URL` | URL | No | - | S3 endpoint URL (Required for ParsPack). |
| `AWS_S3_CUSTOM_DOMAIN` | String | No | - | Custom domain for S3 assets. |

---

## Email
| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `EMAIL_BACKEND` | String | No | `django.core.mail.backends.smtp.EmailBackend` | Backend for sending emails. |
| `EMAIL_HOST` | String | No | `localhost` | SMTP server host. |
| `EMAIL_PORT` | Integer | No | `587` | SMTP server port. |
| `EMAIL_USE_TLS` | Boolean | No | `True` | Use TLS for SMTP connection. |

---

## Third-Party Services
| Variable | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GOOGLE_CLIENT_ID` | String | No | - | Client ID for Google OAuth2 login. |

---

## Security Implications
- **`SECRET_KEY`:** If leaked, attackers can forge session cookies and reset tokens.
- **`DEBUG=True`:** Exposes sensitive environment variables and source code on error pages.
- **`DATABASE_URL`:** Contains sensitive credentials; ensure `.env` is never committed to VCS.
