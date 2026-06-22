# External Integrations

This document describes the third-party services and APIs integrated into the Blog Platform.

---

## 1. Google OAuth2
- **Purpose:** Allows users to sign in using their Google accounts.
- **Implementation:** Custom authentication backend in `users/views.py`.
- **Configuration:** Requires `GOOGLE_CLIENT_ID` in the environment variables.
- **Failure Handling:** Returns a `400 Bad Request` if the token is invalid or a `503 Service Unavailable` if Google services are unreachable.

---

## 2. Storage & CDN (AWS S3 / ParsPack)
- **Purpose:** Scalable cloud storage for media assets and global delivery via CDN.
- **Implementation:** Integrated via `django-storages` (S3Boto3Storage).
- **Configuration:**
    - Set `STORAGE_BACKEND=s3` to enable S3 storage.
    - For ParsPack S3, configure `AWS_S3_ENDPOINT_URL` (e.g., `https://s3.parspack.com`).
    - To enable CDN delivery, set `USE_CDN=True` and provide `CDN_DOMAIN`.
- **Behavior:**
    - Files are uploaded directly to the S3 bucket.
    - If CDN is enabled, `STATIC_URL` and `MEDIA_URL` point to the CDN domain.
    - If CDN is disabled but S3 is used, `MEDIA_URL` points to the S3 bucket or custom domain.

---

## 3. Email (SMTP)
- **Purpose:** System notifications, password resets, and account activations.
- **Implementation:** Django's core email backend.
- **Failure Handling:** Failed emails are logged to `logs/smtp.log`. Asynchronous sending via Celery prevents blocking the main request thread.

---

## 4. CKEditor 5
- **Purpose:** Provides a rich text editing experience for authors.
- **Customization:** Configured in `blog/settings.py` with custom toolbars and image upload endpoints (`/api/editor/upload/`).

---

## 5. FFmpeg
- **Purpose:** Video optimization and transcoding.
- **Implementation:** Executed as a subprocess within Celery workers.
- **Dependency:** Must be installed in the Docker container (handled in `Dockerfile`).

---

## 6. Iranian Localized Integrations
- **Jalali Date:** Provided by `django-jalali-date` for Persian calendar support in the Admin panel and API responses.
- **Normalization:** Custom logic in `common` for normalizing Persian/Arabic characters (e.g., standardizing 'ک' and 'ی').
