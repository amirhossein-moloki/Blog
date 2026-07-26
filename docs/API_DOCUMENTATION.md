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

### 2. Articles & Taxonomies
- **List Articles:** `GET /api/articles/`
    - Query Params: `category`, `tags`, `is_hot`, `search`, `ordering`, `fields`
- **Retrieve Article:** `GET /api/articles/{slug}/`
- **Publish Article:** `POST /api/articles/{slug}/publish/`
    - Permission: Admin or Author of the article.
- **Categories:** `GET /api/articles/categories/`
    - Response contains hierarchical category listings with the `icon` URL (SVG supported).

### 3. Podcast Subsystem
- **List Podcast Categories:** `GET /api/articles/podcast-categories/`
    - Response includes `id`, `title`, `slug`, `icon` (SVG path), `is_active`.
- **List Podcasts:** `GET /api/articles/podcasts/`
    - Query Params: `category` (filter by category ID), `media_type` (`audio` or `video`), `ordering` (e.g. `-published_date`), `search`
- **Retrieve Podcast:** `GET /api/articles/podcasts/{id}/`
    - Activates atomic increment for the episode's `view_count` on every detail retrieval.
    - Response includes full category detail and Jalali localized published timestamp (`published_date_jalali`).

### 4. Polaroid Gallery Subsystem
- **List Gallery Items:** `GET /api/articles/gallery/`
    - Returns active Polaroid style gallery cards sorted by the `order` parameter.
    - Fields returned: `id`, `image`, `caption`, `order`, `link`, `is_active`.

### 5. Media
- **Upload Media:** `POST /api/media/`
    - Body: `file` (Multipart), `alt_text`, `title`
    - Action: Automatically extracts metadata and uploads the original file.
- **Download Media:** `GET /api/media/{id}/download/`

### 6. Interactions
- **Article Comment:** `POST /api/comments/`
    - Body: `article`, `content`, `parent`
- **React to Content:** `POST /api/reactions/`
    - Body: `reaction` (e.g., 'like'), `content_type`, `object_id`

---

## Serializer Analysis

### Article Serializer
- **Read-Only:** `views_count`, `reading_time_sec`, `comments_count`, `likes_count`.
- **Dynamic:** Fields like `content` are only included in the retrieve view, not in the list view (optimized for bandwidth).
- **Validation:** `publish_at` field handles status transitions (Draft → Scheduled → Published).
- **New Fields:** Includes `short_description` (localized metadata), `related_articles` (full listing of manually selected related articles on retrieval), and write support for `related_article_ids` during creation/updates.

### Podcast Serializer
- **Read-Only:** `view_count`.
- **Fields:** Returns `category` alongside `category_detail` objects, `published_date_jalali` (fully parsed Jalali date string), `duration` (in minutes), and lists of `related_podcasts`.
- **Content Normalization:** Integrates `ContentNormalizationMixin` to convert episode descriptions from rich HTML to standardized, clean Markdown formatting in representation.

### Media Serializer
- **Optimization:** Extracts `width`, `height`, `mime`, and `size_bytes` automatically from the file.

---

## Business Logic Flows

### Article Lifecycle
1. User creates an `Article` with `status='draft'`.
2. User updates `status='scheduled'` and sets `publish_at` to a future date.
3. Every minute, a Celery task (`publish_scheduled_articles_task`) checks for passed dates and sets `status='published'`.

### Media Synchronization
When an `Article` is saved, the `sync_article_media` service:
1. Scans the `content` HTML for `<img>` tags.
2. Extracts internal media URLs.
3. Updates the `ArticleMedia` junction table to track which media is used in which article.
4. Deletes unused attachments to maintain database integrity.

### Podcast View Tracker
When `PodcastViewSet.retrieve()` is invoked:
1. Django issues an atomic `F()` update to the model database row: `view_count = F('view_count') + 1`.
2. This avoids typical race conditions where concurrent reads could cause incorrect view counts.

---

## Error Handling
The API returns standard HTTP status codes:
- **401 Unauthorized:** Missing or invalid JWT.
- **403 Forbidden:** Authenticated user lacks permission for the object/action.
- **400 Bad Request:** Validation errors (returned in `data` or `messagesList`).
- **429 Too Many Requests:** Triggered by Axes after multiple failed login attempts.
