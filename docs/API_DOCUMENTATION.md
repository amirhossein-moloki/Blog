# API Documentation

The Blog Platform API is built using Django REST Framework and follows RESTful standards. All responses are standardized and support dynamic field selection.

---

## Global Standards

### Base URL
- **Production:** `https://api.yourdomain.com/api/`
- **Development:** `http://localhost:8000/api/`

### Standard Response Format
```json
{
  "data": { ... },
  "messagesList": [],
  "pagination": {
    "pageNo": 1,
    "pageSize": 10,
    "totalPage": 5,
    "totalCount": 48
  }
}
```
*Note: The `pagination` key is only present in list responses.*

---

## Core Endpoints

### 1. Authentication
- **Admin Login:** `POST /api/auth/admin-login/`
    - Request: `username`, `password`
    - Response: `access`, `refresh`
- **Google Login:** `POST /api/auth/google/login/`
    - Request: `id_token`
    - Response: `access`, `refresh`
- **Token Refresh:** `POST /api/token/refresh/`

### 2. Posts
- **List Posts:** `GET /api/posts/`
    - Query Params: `category`, `tags`, `is_hot`, `search`, `ordering`, `fields`
- **Retrieve Post:** `GET /api/posts/{slug}/`
- **Publish Post:** `POST /api/posts/{slug}/publish/`
    - Permission: Admin or Author of the post.

### 3. Media
- **Upload Media:** `POST /api/media/`
    - Body: `file` (Multipart), `alt_text`, `title`
    - Action: Automatically converts images to AVIF.
- **Download Media:** `GET /api/media/{id}/download/`

### 4. Interactions
- **Post Comment:** `POST /api/comments/`
    - Body: `post`, `content`, `parent`
- **React to Content:** `POST /api/reactions/`
    - Body: `reaction` (e.g., 'like'), `content_type`, `object_id`

---

## Serializer Analysis

### Post Serializer
- **Read-Only:** `views_count`, `reading_time_sec`, `comments_count`, `likes_count`.
- **Dynamic:** Fields like `content` are only included in the retrieve view, not in the list view (optimized for bandwidth).
- **Validation:** `publish_at` field handles status transitions (Draft → Scheduled → Published).

### Media Serializer
- **Optimization:** Extracts `width`, `height`, `mime`, and `size_bytes` automatically from the file.

---

## Business Logic Flows

### Post Lifecycle
1. User creates a `Post` with `status='draft'`.
2. User updates `status='scheduled'` and sets `publish_at` to a future date.
3. Every minute, a Celery task (`publish_scheduled_posts_task`) checks for passed dates and sets `status='published'`.

### Media Synchronization
When a `Post` is saved, the `sync_post_media` service:
1. Scans the `content` HTML for `<img>` tags.
2. Extracts internal media URLs.
3. Updates the `PostMedia` junction table to track which media is used in which post.
4. Deletes unused attachments to maintain database integrity.

---

## Error Handling
The API returns standard HTTP status codes:
- **401 Unauthorized:** Missing or invalid JWT.
- **403 Forbidden:** Authenticated user lacks permission for the object/action.
- **400 Bad Request:** Validation errors (returned in `data` or `messagesList`).
- **429 Too Many Requests:** Triggered by Axes after multiple failed login attempts.
