# Final Approved Media Policy & Architecture Decision
**Project:** Enterprise Blog Platform
**Author:** Senior Software Architect
**Status:** APPROVED & IMPLEMENTATION-READY
**Date:** July 2024

---

## 1. Current Architecture Evaluation

The current implementation utilizes a **Media-first** architecture where file upload and content creation are decoupled into separate RESTful operations.

```
Frontend                           Media API                       Article API
   |                                   |                                |
   |--- 1. POST /api/media (File) ---->|                                |
   |<-- 2. Return Media ID & URL ------|                                |
   |                                                                    |
   |----------- 3. POST /api/articles (JSON with Media ID) ------------>|
   |                                                                    |
   |<---------- 4. Return Created Article ------------------------------|
```

### Advantages of Decoupled Media-first Model
- **Separation of Concerns (SoC):** The `medias` app is completely self-contained. It takes files, validates size/type, uploads them to storage, extracts width/height, and registers metadata. It does not need to know about articles, users, or podcasts.
- **Resource Reusability:** A single uploaded asset can be linked as an article cover, an author avatar, a podcast category icon, or included inside multiple article content blocks without duplicating physical bytes.
- **Microservice Readiness:** This isolation makes the Media app an ideal candidate to be split into a separate, dedicated microservice or serverless function in the future.
- **Lightweight Article Payloads:** Creating or updating articles uses clean application/json payloads instead of heavy multipart payloads, optimizing network throughput and database transaction times.
- **Rich-text Editor (CKEditor) Compatibility:** Modern block or rich-text editors require immediate asynchronous inline image uploading during writing. A decoupled Media API naturally supports this.

### Challenges & Limitations
- **Orphan File Bloat:** If a user uploads an image but abandons the article composition, or if validation fails during article creation, the media remains permanently registered in the database and saved in storage.
- **Frontend Orchestration Overhead:** The frontend must manage a multi-step sequence (upload file, receive ID, create article, link ID).
- **BeautifulSoup Sync Dependency:** The system currently scans HTML translations post-save to find `<img>` tags and create `ArticleMedia` rows. While robust, it is a backend heuristic that runs during the critical request-response cycle and can experience race conditions or out-of-sync states under high write volumes.

---

## 2. Problems Identified

1. **No Media Lifecycle State:** The database cannot distinguish between a file that is actively used in a published article versus a file uploaded 2 weeks ago that was never attached to anything.
2. **Code Duplication in CKEditor Upload:**
   - The view `posts/ckeditor_views.py:ckeditor_upload_view` implements its own upload, sanitization, and database registration logic. It duplicates the operations of `medias/services.py:create_media_from_file`, violating the DRY (Don't Repeat Yourself) principle.
3. **No Automatic Garbage Collection (GC):** No background worker or cron script runs to detect and delete unattached, expired media.
4. **Security Vulnerability in Listing Endpoint:**
   - Standard `/api/media/` allows users to list all media items. This can leak private, unattached draft assets or unreleased media attachments to unauthorized eyes.
5. **Lack of Transaction Boundaries during Article Creation:**
   - If an article creation fails validation (e.g., translation slug duplicate), the cover image is already uploaded and saved as a permanent asset with no automatic rollback or cleanup.

---

## 3. Considered Alternatives

### Alternative A: Move Completely to Article-first Multipart Architecture
* **Description:** The frontend submits the article metadata (JSON-like text fields) and the binary files (cover image, OG image) together in a single `multipart/form-data` request.
* **Pros:** Single HTTP request, atomic transactional boundary at database level (if article creation fails, files are easily discarded).
* **Cons:** Extremely high memory overhead for the web servers, makes autosave/draft workflows sluggish, completely incompatible with CKEditor's real-time drag-and-drop inline uploading, and prevents media reuse across different applications.
* **Verdict:** **REJECTED** due to poor scalability, heavy server-side processing, and bad rich-text editing UX.

### Alternative B: Keep Current Decoupled System (As-Is)
* **Pros:** Already built, no additional development effort needed immediately.
* **Cons:** Orphan files will eventually consume gigabytes of expensive cloud/local storage, and duplicate upload logic leaves the system prone to bugs and inconsistent file sanitization.
* **Verdict:** **REJECTED** due to long-term maintenance costs and poor production-readiness.

### Alternative C: Stateful Hybrid Media-first Architecture (The Chosen Architecture)
* **Description:** We retain decoupled REST endpoints but introduce a **Stateful Media Lifecycle** where files are uploaded as `temporary` (unattached) by default. The backend promotes media to `attached` once they are successfully saved as a cover, OG, or within an article's body. A recurring Celery task sweeps and deletes expired temporary files. All uploads (including CKEditor) are dryed up to use a single service.
* **Verdict:** **APPROVED** as it combines the performance benefits of Alternative B with the safety and cleanliness of Alternative A, and provides the ultimate Developer Experience (DX) for frontend integrations.

---

## 4. Final Architecture Decision

We officially adopt the **Stateful Hybrid Media-first Architecture**.

```
+---------------------------------------------------------------------------------+
|                                 MEDIA LIFECYCLE                                 |
+---------------------------------------------------------------------------------+
                                       |
                                       v
                                [Upload File]
                                       |
                                       v
                             Status: "temporary"
                             (Expires in 24 Hours)
                                       |
                    +------------------+------------------+
                    | (Linked in Article Save)            | (Abandoned / Not Linked)
                    v                                     v
            Status: "attached"                     [Celery Beat Cron]
                    |                                     |
                    v                                     v
            Permanent Asset                       [Hard Delete File]
                                                          |
                                                          v
                                                    [Remove Record]
```

### Core Design Components:
1. **Stateful Media Model:** Extend `medias.Media` with an `is_attached` boolean field (defaulting to `False`) or a state tracker.
2. **Unified Upload Pipeline:** Unify all file ingestion (normal file uploads, avatars, CKEditor) through `medias.services.create_media_from_file`.
3. **Automated Promotion Engine:** Whenever an Article or its translation is created or modified, the backend's `sync_article_media` service evaluates cover image, OG image, and in-content images, links them in `ArticleMedia`, and flags the corresponding `Media` records as `is_attached=True`.
4. **Scheduled Garbage Collector:** Run a daily Celery task that queries all `Media` instances where `is_attached=False` and `created_at` is older than 24 hours, deletes their files from physical storage, and removes the database records.

---

## 5. Global Media Policy

To maintain a scalable, secure, and clean filesystem, developers must strictly adhere to the following rules:

* **Central Registry:** The `medias.Media` model remains the single, centralized registry for all files. No other Django application may define file/image fields directly on their primary models unless they reference `Media` via a ForeignKey (e.g., `cover_image = ForeignKey(Media)`).
* **Single Source of Ingestion:** Files must only be uploaded via the `/api/media/` endpoint or custom admin upload widgets that explicitly invoke `medias.services.create_media_from_file`. Direct file writing or custom `default_storage.save` calls are forbidden.
* **Standard File Validation:**
  - File size limits and MIME types must be verified at the serializer layer using `common.validators.validate_file`.
  - Max image size: **10 MB**.
  - Max video size: **100 MB**.
  - Allowed MIME types: Images (`image/jpeg`, `image/png`, `image/webp`, `image/gif`), Videos (`video/mp4`, `video/webm`), Audios (`audio/mpeg`, `audio/wav`), Documents (`application/pdf`).
* **Storage Strategy:** Under local environments, files are saved in `/media/uploads/YYYY/MM/DD/`. Under production, files are uploaded to an S3-compatible object storage (MinIO, AWS S3) with a CDN proxy layer.
* **Naming Policy:** File names are always sanitized using `common.utils.files.get_sanitized_filename`. This strips special characters, transliterates non-ASCII files, and appends a unique short UUID to prevent namespace collisions.
* **Metadata Extraction:** All uploaded images automatically have their width and height extracted and persisted using `Pillow` at creation time.
* **Unused File Purging:** The backend runs a periodic cron cleanup job (`purge_unused_media_task`) to delete unattached media files from physical storage.
* **Secure Access & Listing Policy:**
  - Standard users can only view or download their own uploaded media or public assets.
  - The list action on `MediaViewSet` must filter files so standard authors only see their own uploaded media. Only staff admins can see the entire global media list.

---

## 6. Article Media Policy

The relationship between Articles and Media must be handled cleanly to support autosaves, drafts, and editing.

### Case A: Cover Image
- **Upload Workflow:** The frontend uploads the cover image via `POST /api/media/` as a separate operation. It receives a JSON response with the Media ID.
- **Article Linking:** The frontend submits the Media ID inside the article creation JSON body (under `cover_image`).
- **State Promotion:** On successful article save, the backend marks the referenced `Media` as `is_attached=True` and creates/updates an `ArticleMedia` relationship record with `attachment_type="cover"`.

### Case B: Open Graph Image
- **Workflow:** Same as the Cover Image. The frontend uploads first, retrieves the Media ID, and passes it under `og_image` in the article body.
- **State Promotion:** The backend automatically promotes the referenced OG image to `is_attached=True` and establishes the `ArticleMedia` relation with `attachment_type="og-image"`.

### Case C: Images Inside Article Content (Rich-Text Editor)
- **Workflow:** When a writer inserts, drags, or drops an image into CKEditor 5, the editor immediately uploads the file to the unified media upload pipeline via `/api/media/`.
- **Immediate State:** The uploaded inline image is initially marked as `is_attached=False` (temporary status).
- **Auto-Sync and Promotion:** When the writer clicks "Save Draft" or "Publish", the frontend submits the HTML string containing `<img>` tags.
  - The backend's `save()` method triggers `sync_article_media`.
  - `sync_article_media` parses the HTML using BeautifulSoup, extracts all media URLs belonging to the application's domain, identifies their `Media` IDs, creates `ArticleMedia` records with `attachment_type="in-content"`, and promotes those media items to `is_attached=True`.
- **Image Replacement/Deletion:** If a user deletes an image from CKEditor and saves the article, the next `sync_article_media` run detects that the image is no longer in the HTML, deletes the corresponding `ArticleMedia` relationship, and flags the `Media` item as `is_attached=False`. It will then be collected by the nightly garbage collection task.

---

## 7. ArticleMedia Relationship Policy

The intermediate model `ArticleMedia` acts as the junction table that tracks the associations between `Article` and `Media`.

- **Creation Responsibility:** The backend is the **sole authority** for creating, updating, and deleting `ArticleMedia` records. The frontend never writes to `ArticleMedia` directly.
- **Timing of Creation:**
  - Cover and OG relationships are created/updated immediately during the Article model's `save()` method.
  - In-content relationships are created/updated immediately during the `ArticleTranslation` model's `save()` method after analyzing the localized HTML text.
- **Attachment Types:** The system strictly defines and validates three attachment types:
  1. `cover`: The primary display image of the article.
  2. `og-image`: The dedicated image used for SEO and social sharing cards.
  3. `in-content`: Any image or media file embedded inside the localized rich-text body.

---

## 8. Remove Duplicate Responsibilities

To reduce technical debt, we establish clear architectural boundaries and eliminate duplicated upload code.

| Responsibility | Single Source of Truth (SSoT) | Action Required |
| :--- | :--- | :--- |
| **File Validation** | `common.validators.validate_file` | Used uniformly in `MediaCreateSerializer` and all file-upload components. |
| **File Naming & Sanitization** | `common.utils.files.get_sanitized_filename` | Handles ASCII sanitization and UUID appending. |
| **Physical Storage Handling** | `django.core.files.storage.default_storage` | Configured centrally in `settings.py` (Local or S3-compatible). |
| **Media Record Creation** | `medias.services.create_media_from_file` | Handles database entry, Pillow dimensions, and type selection. |
| **CKEditor Ingestion** | `posts.ckeditor_views.ckeditor_upload_view` | **REFACTOR:** Must import and delegate the file processing entirely to `medias.services.create_media_from_file` instead of manually calling `default_storage.save`. |

---

## 9. Transaction & Error Handling

We design defensive boundaries to prevent database corruption and storage mismatches.

- **Transaction Isolation:** Article updates and translation saves are always wrapped in a Django atomic transaction (`transaction.atomic`). This ensures that if translation creation fails validation, the `Article` save is rolled back.
- **Partial Upload Safeguards:** If file upload fails (network interruption, disk full), the API returns a standard `500 Internal Server Error` and does not write a database record, preventing corrupt files with `0` bytes.
- **Upload Rollbacks:** Since physical file storage (such as AWS S3 or file-system writes) cannot be automatically rolled back by SQL transactions, we implement a "Storage Cleanup on Transaction Fail" signal. If a database transaction fails after a file is saved, a signal catches the failure and deletes the orphaned file from storage.
- **Graceful Failure in Extraction:** If Pillow fails to extract the width/height of an image (e.g. corrupted file header), the system must log a warning but proceed to save the `Media` record with `width=None` and `height=None` rather than failing the upload.

---

## 10. API Design Decision

We recommend and finalize **Option 3 (Hybrid Approach)** as the system's official API contract.

### Contract 1: File Upload (Immediate & Stateful)
- **Endpoint:** `POST /api/media/`
- **Request Headers:** `Content-Type: multipart/form-data`
- **Request Payload:**
  - `file`: Binary Data (Required)
  - `alt_text`: String (Optional)
  - `title`: String (Optional)
- **Response Payload (201 Created):**
```json
{
  "id": 142,
  "storage_key": "uploads/2024/07/22/article_banner_3f9a72b1.webp",
  "url": "http://localhost:8000/media/uploads/2024/07/22/article_banner_3f9a72b1.webp",
  "type": "image",
  "mime": "image/webp",
  "width": 1200,
  "height": 630,
  "size_bytes": 145200,
  "alt_text": "Beautiful landscape",
  "title": "article_banner",
  "is_attached": false,
  "uploaded_by": 12,
  "created_at": "1403/05/01 12:30:15"
}
```

### Contract 2: Article Creation (JSON Payload with Linked Media IDs)
- **Endpoint:** `POST /api/articles/`
- **Request Headers:** `Content-Type: application/json`
- **Request Payload:**
```json
{
  "status": "draft",
  "visibility": "public",
  "category_id": 3,
  "cover_image_id": 142,
  "og_image_id": 143,
  "translations": [
    {
      "language_code": "en",
      "slug": "scaling-django-apis",
      "title": "Scaling Django APIs in 2024",
      "excerpt": "A deep dive into optimizing media and content pipelines.",
      "content": "<h1>Introduction</h1><p>Here is an inline graphic:</p><img src=\"http://localhost:8000/media/uploads/2024/07/22/diagram_9b2a.webp\" />"
    }
  ]
}
```
- **Response Behavior:**
  - On receiving this request, the backend creates the `Article` and `ArticleTranslation`.
  - It links `cover_image_id` 142 and `og_image_id` 143.
  - It runs `sync_article_media` on the English content, detects `diagram_9b2a.webp` (Media ID 144), and links it as `in-content`.
  - It promotes Media items 142, 143, and 144 to `is_attached=True`.

---

## 11. Required Implementation Changes

Developers must perform the following actions to complete the architecture transition:

1. **Database Migration (`medias` app):**
   - Add `is_attached = models.BooleanField(default=False, db_index=True)` to the `Media` model.
   - Run `python manage.py makemigrations medias` and `python manage.py migrate`.
2. **Refactor CKEditor View (`posts/ckeditor_views.py`):**
   - Delete manual `default_storage` save calls.
   - Import `from medias.services import create_media_from_file` and delegate the file creation.
3. **Enhance Promotion Logic (`posts/services.py:sync_article_media`):**
   - In `sync_article_media`, after associating/deleting `ArticleMedia` models, update the corresponding `Media` entries' `is_attached` flag.
   - Query all media attachments for the article and set `is_attached=True`.
   - Any media detached must be marked `is_attached=False`.
4. **Implement Celery GC Task (`medias/tasks.py`):**
   - Write a shared Celery task `purge_unused_media_task` that runs every 24 hours.
   - Delete physical files from `default_storage` and remove database rows where `is_attached=False` and `created_at` is older than 24 hours.

---

## 12. Migration Considerations

- **Legacy Data Safety:** For a smooth production migration, any legacy `Media` files already present in the database must not be deleted.
- **Migration Script:** Write a custom migration script or data migration that queries all `Media` objects currently referenced in any `Article` (via `cover_image`, `og_image`, or existing `ArticleMedia` attachments) and sets their `is_attached` attribute to `True`.
- **Default Status:** Any unattached legacy media should be carefully evaluated, but as a safety measure, we can set all pre-existing media files to `is_attached=True` during migration to prevent accidental deletion of old files whose attachment history is unclear.

---

## 13. Long-Term Scalability Considerations

- **Direct-to-S3 Pre-signed URL Uploads:** As traffic grows, uploading large media files (especially high-definition video attachments) directly through the Django application server will degrade performance. The API should be enhanced to support generating secure S3 pre-signed URLs, allowing frontends to upload large files directly to object storage, with the media metadata registered via a fast webhook call afterwards.
- **On-the-Fly Image Optimization CDN:** Instead of performing resource-heavy image optimization (like AVIF or WebP transcoding) synchronously on Django web workers, integrate an image CDN (such as Cloudflare Polish, Imgix, or a serverless AWS CloudFront image resizing stack). This serves highly optimized, resized, and cached images on-the-fly depending on the client's screen size and browser support, completely offloading CPU work from the application servers.
- **Asynchronous File Cleanup Queue:** To keep database transactions swift and responsive, physical file deletion in the cleanup job should be delegated to a high-speed asynchronous celery task pool, preventing disk IO bottlenecks from slowing down the primary web server.
