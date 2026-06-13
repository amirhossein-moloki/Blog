# External Integrations

This document describes the third-party services and APIs integrated into the Blog Platform.

---

## 1. Google OAuth2
- **Purpose:** Allows users to sign in using their Google accounts.
- **Implementation:** Custom authentication backend in `users/views.py`.
- **Configuration:** Requires `GOOGLE_CLIENT_ID` in the environment variables.
- **Failure Handling:** Returns a `400 Bad Request` if the token is invalid or a `503 Service Unavailable` if Google services are unreachable.

---

## 2. AWS S3 (Optional Storage)
- **Purpose:** Scalable cloud storage for media assets.
- **Implementation:** Integrated via `django-storages`.
- **Configuration:** Triggered by setting `STORAGE_BACKEND=s3`.
- **Behavior:** Files are uploaded directly to the S3 bucket; URLs are generated using the configured `AWS_S3_CUSTOM_DOMAIN`.

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
