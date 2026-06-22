# ARCHITECTURE AUDIT REPORT: Django Blog/CMS System

## 1. System Overview (AS-IS)
The system is a modular monolith built with Django 5.0 and Django REST Framework (DRF). It is designed to serve as a comprehensive Blog/CMS platform with a standardized API, localized for both English and Persian (Jalali calendar support).

### Key Applications:
- **blog/**: Root configuration, settings, and main URL routing.
- **core/**: Shared abstract base models and infrastructure.
- **common/**: Standardized API response logic, authentication, and global utilities.
- **users/**: Identity management and authorization.
- **posts/**: Core CMS logic including posts, taxonomies, and content versioning.
- **medias/**: Centralized asset management and storage integration.
- **interactions/**: Engagement features like comments and reactions.
- **pages/**: Static content management.
- **navigation/**: Dynamic menu and link management.

---

## 2. Django App Breakdown

### **posts (Content Management)**
- **Models**: `Post`, `Category`, `Tag`, `Series`, `AuthorProfile`, `Revision`, `PostTag`.
- **Services**: `increment_post_view_count`, `publish_scheduled_posts`, `sync_post_media`.
- **Views**: `PostViewSet`, `PostCommentViewSet`, `CategoryViewSet`, `TagViewSet`, `SeriesViewSet`, `RevisionViewSet`, `publish_post`, `related_posts`.
- **Responsibilities**: Orchestrating content creation, scheduling, status management, and relationships between content and taxonomies.

### **medias (Asset Library)**
- **Models**: `Media`, `PostMedia`.
- **Services**: `create_media_from_file`.
- **Views**: `MediaViewSet`, `download_media`.
- **Responsibilities**: Managing file uploads, extracting metadata (image dimensions, file size), and tracking media usage across posts.

### **interactions (Engagement)**
- **Models**: `Comment`, `Reaction`.
- **Services**: `create_comment`, `toggle_reaction`.
- **Views**: `CommentViewSet` (via PostComment), `Reaction` management.
- **Responsibilities**: Handling user feedback, threaded comments, and generic reactions (likes/emojis) using Django ContentTypes.

### **users (Identity & Access)**
- **Models**: `User`.
- **Services**: Auth-related logic (managed largely by Djoser/SimpleJWT).
- **Views**: Standard DRF/Djoser auth views.
- **Responsibilities**: User registration, authentication (JWT & Static API Key), and profile picture management.

### **core (Base Infrastructure)**
- **Models**: `BaseModel` (abstract).
- **Responsibilities**: Providing audit fields (`created_at`, `updated_at`, `is_active`) to all other models.

---

## 3. Data Model Analysis

### **Post**
- **Fields**: `slug`, `title`, `excerpt`, `content` (CKEditor5), `status` (choices), `visibility` (choices), `published_at`, `scheduled_at`, `views_count`, `reading_time_sec`, `is_hot`, `seo_title`, `seo_description`.
- **Relationships**: `AuthorProfile` (FK), `Category` (FK), `Series` (FK), `Media` (FKs for cover/OG), `Tags` (M2M).
- **Rules**: Auto-calculates `reading_time_sec` on save; triggers `sync_post_media` to link assets in HTML content.

### **Media**
- **Fields**: `storage_key`, `url`, `type` (image/video/audio/file), `mime`, `width`, `height`, `size_bytes`, `alt_text`, `title`.
- **Relationships**: `uploaded_by` (FK to User).
- **Rules**: Metadata extraction upon upload; supports S3 or Local storage backends.

### **Comment**
- **Fields**: `content`, `status` (pending/approved/spam/removed), `ip`, `user_agent`.
- **Relationships**: `Post` (FK), `User` (FK), `parent` (Self-referencing FK for replies).
- **Rules**: Threaded structure; visibility restricted by moderation status.

### **Reaction**
- **Fields**: `reaction` (string key, e.g., 'like').
- **Relationships**: `User` (FK), `ContentType` + `object_id` (Generic Foreign Key).
- **Constraints**: `unique_together` on user, content_object, and reaction type.

---

## 4. Business Logic Flow

### **Post Creation & Attachment**
1. Author submits post data (including `cover_media_id`, `og_image_id`).
2. `Post.save()` is called.
3. **Reading Time**: `save()` method calculates reading time based on content length.
4. **Media Sync**: `sync_post_media` service parses HTML `<img>` tags, finds matching `Media` objects by `storage_key`, and creates `PostMedia` records. It also ensures cover/OG images are correctly linked in the association table.

### **Publishing & Scheduling**
1. Posts set to "published" with a future date automatically transition to "scheduled".
2. A **Celery Beat** task (`publish_scheduled_posts_task`) runs every minute.
3. The task identifies posts with `status='scheduled'` and `scheduled_at <= now`.
4. It updates status to `published` and sets `published_at` to the original scheduled time.

### **SEO & Metadata**
- Each `Post` and `Page` has explicit `seo_title` and `seo_description` fields.
- `Post` includes an `og_image` relationship for social sharing.
- Slugs are used as primary lookup fields in the API.

---

## 5. SEO System Analysis
- **Fields**: Dedicated fields in `Post` and `Page` models.
- **Sitemap**: Centralized in `blog/sitemaps.py`. Includes `PostSitemap` (filtered for published posts) and `StaticViewSitemap` (for home, about, auth pages).
- **Slug Management**: Slugs are manually or automatically generated and enforced as unique in the DB. API lookups are performed via `lookup_field = "slug"`.
- **Meta Tags**: Handled by storing `seo_title`, `seo_description`, and `og_image` in the database, intended for use by the frontend to populate HTML tags.

---

## 6. Media System Analysis
- **Upload**: Handled via `MediaViewSet` and `create_media_from_file` service.
- **Metadata**: Extracted using the `PIL` (Pillow) library for images (width, height) and stored in the `Media` model.
- **Linking**: Managed through the `PostMedia` through-model, which categorizes usage as 'cover', 'og-image', or 'in-content'.
- **Optimization**: The system previously had optimization logic (AVIF), but it is currently disabled or removed from the core service flow, leaving files as uploaded.

---

## 7. Architecture Patterns (AS-IS)
- **Service Layer**: Business logic is encapsulated in `services.py` files (e.g., `sync_post_media`, `create_comment`) to keep ViewSets thin.
- **Standardized Response**: `StandardResponseRenderer` wraps all API outputs in a `{data, messagesList, pagination}` envelope.
- **Standardized Schema**: `StandardizedAutoSchema` automatically reflects the envelope structure in OpenAPI/Swagger.
- **Static API Key Auth**: A custom `StaticAPIKeyAuthentication` class allows system-to-system or testing access via the `X-API-Key` header.
- **Generic Relationships**: Used for the `Reaction` system to allow likes/emojis on any model without hard coupling.
- **Signals**: Used in `users/signals.py` for cache invalidation upon user profile changes.

---

## 8. Migration-Relevant Insights

### **Tight Coupling (Django Dependent)**
- **Django ContentTypes**: The `Reaction` system is heavily dependent on Django's internal ContentType mapping.
- **CKEditor5 Integration**: Content parsing and media sync logic are tied to the HTML structure generated by CKEditor5.
- **Standardized AutoSchema**: The OpenAPI generation is tightly integrated with DRF's metadata system.

### **Framework-Independent Logic**
- **Reading Time Calculation**: Simple regex-based word count.
- **Media Sync Strategy**: The pattern of parsing HTML for `storage_key` strings and maintaining an association table.
- **Standardized Response Envelope**: The JSON structure is a pure data contract.

### **Migration Risks**
- **Sitemap Logic**: Django's built-in `Sitemap` framework needs a custom equivalent in the new system.
- **Permission Matrix**: Complex DRF permissions (`IsAuthorOrAdminOrReadOnly`) must be carefully mapped to new middleware/guards.
- **Media Storage**: The logic for switching between Local and S3 backends (handled by `django-storages`) must be replicated.
