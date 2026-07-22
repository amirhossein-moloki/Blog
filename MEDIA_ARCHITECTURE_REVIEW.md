# Architectural Review Report: Media Upload & Article Media Policy

This report provides a comprehensive architectural review of the Media Management policy across the project, focusing on the Articles module. It evaluates the existing "Media-first" workflow, analyzes the proposed "Article-first" single-request multipart workflow, explores compatibility and risks, and proposes a balanced hybrid architecture that addresses both technical and developer experience goals.

---

## 1. Current Policy Analysis

### 1.1 How does the current media lifecycle work?
The current system operates on a **Media-first** lifecycle model:
1. **Media Creation & Upload:** Media files are uploaded independently via the `MediaViewSet` (specifically the `create` action at `/api/medias/`) or the CKEditor upload endpoint (`/api/posts/ckeditor/upload/`).
2. **Backend Storage:** The upload service sanitizes the filename, saves the file to default storage (e.g., S3 or local system), retrieves the storage URL, and creates a database record in the `Media` model containing metadata (such as dimensions, MIME type, size, and type).
3. **Frontend Reference:** The API returns the created `Media` object (or just the URL for CKEditor). The frontend utilizes these returned values to construct the article body (embedding `<img>` tags pointing to the uploaded media) or references the generated ID in fields like `cover_image_id` or `og_image_id`.
4. **Relationship Linking (Sync):** When an `Article` or `ArticleTranslation` is created or updated, the custom `save` method invokes the service `sync_article_media`. This service performs two key syncing operations:
   - Synchronizes `cover` and `og-image` attachments tied directly to the `Article`.
   - Parses the localized HTML body (e.g., `ArticleTranslation.content`) using BeautifulSoup to extract image paths matching `MEDIA_URL`, and creates or deletes `ArticleMedia` relationship records using the `in-content` attachment type.
5. **Deletion & Cleanup:** No built-in automated garbage collection of unreferenced/orphan media exists. `ArticleMedia` entries are deleted in cascade if an article is deleted (`on_delete=models.CASCADE`), but the underlying physical files and `Media` model records are not automatically pruned from storage.

### 1.2 What responsibilities belong to the frontend?
- **Workflow Coordination:** The frontend must manage the sequence of operations. For instance, when drafting an article with a cover image, it must first upload the cover image to the Media API, wait for a successful response to get the `id`, and then include that `id` as `cover_image_id` in the payload for the Article API.
- **CKEditor Local Handling:** The frontend handles editor-triggered uploads. When an author drops an image into CKEditor, the editor's upload adapter transmits the file to the CKEditor upload endpoint, obtains the resulting URL, and inserts a standard `<img>` tag in the local editor view.
- **State Tracking:** The frontend must keep track of which uploaded media IDs correspond to the cover, OG image, and any inline body images.

### 1.3 What responsibilities belong to the backend?
- **File Ingestion:** Receives raw files, executes filename sanitization via `get_sanitized_filename`, and handles physical storage (via Django's storage abstraction, e.g., local disk, S3, or MinIO).
- **Metadata Extraction:** Extracts key properties like MIME type, file size, image dimensions (using Pillow), or video durations.
- **Relational Syncing:** Parses article content dynamically using `BeautifulSoup` inside `sync_article_media` to build and clean up association records (`ArticleMedia`) mapping `Media` objects to `Article` objects.
- **Access Control:** Authorizes who can upload files or modify specific articles.

### 1.4 Why was the current Media-first workflow originally designed this way?
This design is highly typical of modern CMS and decoupled head architectures:
- **Loose Coupling:** The Media Library is treated as an independent service. An image is uploaded once and can theoretically be reused across different modules, blog posts, or profile pages.
- **Simple API Boundaries:** Endpoints do one thing and do it well. `POST /api/medias/` only processes binary uploads and metadata, while `POST /api/posts/articles/` handles only structured text-based JSON data. This completely avoids the complexity of mixing raw binary multipart data and deeply nested JSON structures in a single endpoint.
- **Stateless/Optimized Uploading:** Frontends can upload heavy media assets to a dedicated media service (or even direct-to-S3 pre-signed URLs) before any draft article exists.

### 1.5 What are its advantages?
- **Media Reusability:** Authors can select an existing image from the Media Library as a cover image for multiple articles or reuse it in different sections without uploading duplicate binary files.
- **Performance:** Editing a text field in an article does not require sending large binary files back and forth. Large file uploads are handled once, isolation-style.
- **Client Flexibility:** Works naturally with rich-text editor components like CKEditor, which natively upload images immediately upon drag-and-drop to obtain a static URL.
- **Separation of Concerns:** The database operations for text data and storage operations for heavy binary files are fully decoupled.

### 1.6 What are its disadvantages?
- **Higher Developer Friction (Frontend):** To perform a single operation ("Create Article with Cover Image"), the client must orchestrate multiple network requests (Upload Cover $\to$ Get ID $\to$ Submit Article).
- **Orphan Media Generation:** If an author uploads three potential cover images, selects one, and saves the article, the other two images remain in the backend as orphan `Media` records with no associated `ArticleMedia` relations, taking up storage space.
- **Incomplete Workflows:** If the article creation fails after images have been successfully uploaded, the uploaded files remain abandoned in storage.

### 1.7 Which parts are tightly coupled?
- `sync_article_media` is tightly coupled to the internal directory structure and `settings.MEDIA_URL`. It parses HTML elements and assumes that files reside inside `/media/` paths.
- The `Article` model depends directly on `medias.Media` through ForeignKey relationships (`cover_image` and `og_image`), creating a circular-like conceptual dependency since Media also links back to Article via `ArticleMedia`.

### 1.8 Which parts are unnecessarily complex?
- **Two separate upload engines:** The project has `create_media_from_file` service in `medias/services.py` and a duplicate upload flow implemented inside `ckeditor_upload_view` (`posts/ckeditor_views.py`), which duplicates some logic of the media service.
- **BeautifulSoup HTML Parsing:** While elegant for automated relational linking, extracting URLs out of arbitrary HTML blocks on every `save()` operation adds processing overhead and relies on precise URL path comparisons (`path[len(settings.MEDIA_URL):]`).

### 1.9 Which parts duplicate responsibilities?
- Filename sanitization, file-saving, and `Media` model creation occur in both `medias/services.py` (`create_media_from_file`) and `posts/ckeditor_views.py` (`ckeditor_upload_view`).

### 1.10 Which parts create extra API requests?
- Creating an article with attachments requires:
  1. `POST /api/medias/` (for the cover image)
  2. `POST /api/medias/` (for the OG image)
  3. `POST /api/posts/articles/` (for the article itself)
- This forces the client to make up to 3 separate API requests to publish a single article.

---

## 2. Proposed Policy Review

### Proposed Architecture Checklist
* Frontend submits the entire article and related media files in a single multipart request.
* Backend automatically creates `Media` records.
* Backend uploads files.
* Backend rewrites article content.
* Backend creates `ArticleMedia` relationships.
* Backend manages cleanup.
* Frontend never uploads media separately for article creation.

### Technical Suitability Evaluation
**Yes, it is technically suitable, but only under specific constraints.**

The proposed "Article-first" single-request workflow is highly viable and solves the "multi-request friction" problem for the frontend. However, declaring that **"the frontend never uploads media separately for article creation"** is a critical architectural misstep. We must explain why:

1. **CKEditor Requirement:** Modern editors like CKEditor require immediate, asynchronous uploads. When an editor drags an image into the text area, the editor immediately sends a separate HTTP POST to get an upload URL to render the image. If we force a single-request flow, the frontend would have to keep the image in memory as a Base64-encoded string, which drastically slows down editor performance, inflates payload sizes, and breaks standard editor plugins.
2. **The "Draft" Paradox:** When writing a long article, authors save draft revisions multiple times. Resubmitting all binary files with every single auto-save draft is incredibly inefficient and unscalable.

Thus, while the backend **should definitely support** the proposed single-request multipart flow (which has already been partially implemented in the codebase via `ArticleCreateUpdateSerializer.to_internal_value`), it **must coexist** with the standalone media upload endpoints.

---

## 3. Compatibility Analysis

### 3.1 Media Library
- If we move *entirely* to the Article-first flow, the concept of a shared Media Library is broken. Media would only be created during article creation, preventing reuse of assets across articles or other modules.
- By allowing both workflows, the Media Library remains fully functional.

### 3.2 Existing APIs
- The proposed changes have already been introduced in the serializers (`ArticleCreateUpdateSerializer` accepts file fields like `cover_image` and `og_image` directly in a multipart request, alongside standard `JSON`-structured data in `article` parameter, or file elements matching `files[<id>]`).
- Keeping this dual compatibility preserves existing mobile/frontend integrations that already use the standalone Media API.

### 3.3 CKEditor Integration
- CKEditor relies on `posts/ckeditor_views.py` to upload media *before* the article is submitted. Abandoning the media-first flow breaks the rich-text editing experience entirely.

### 3.4 Existing Services
- `sync_article_media` remains crucial for parsing inline images. The single-request flow doesn't change the fact that content body image links must be tracked in the database for reference integrity.

### 3.5 Future Modules (e.g., Pages, Portfolios)
- If future modules need media attachment capabilities, they can leverage the generic standalone `Media` system instead of duplicating complex single-request parser engines.

### 3.6 Localization, SEO, and Caching
- Localization requires distinct versions of images (e.g., infographics with localized text). A dual workflow allows attaching localized media specifically to an `ArticleTranslation`.
- SEO & Caching benefits from stable, permanent media URLs. Re-uploading and rewriting content URLs constantly on single-request updates would invalidate CDN and client caches.

### 3.7 File Reuse
- Under a pure "Article-first" model, file reuse is impossible because images are strictly bound to a single transaction.

### 3.8 Performance & Scalability
- **The proposed workflow (Single Request):** Sending 50MB of images alongside article text blocks in a single, blocking request keeps Django threads busy for longer, degrading application throughput.
- **The current workflow (Separated):** Distributes load. Media uploads can be offloaded to dedicated s3-direct gateways, keeping Django app threads fast and light.

---

## 4. Risk Assessment

| Risk Area | Risk Details | Mitigation Strategy |
| :--- | :--- | :--- |
| **Data Consistency** | If an article creation fails midway (e.g., validation error on a text field) after saving files to storage, the storage key is orphaned. | Place the entire database transaction in `transaction.atomic()`. The ViewSet's `create` and `update` methods must track `_uploaded_media` in the request object and delete files from storage if the transaction rolls back (this is already implemented in `ArticleViewSet.create`/`update`). |
| **Transaction Failures** | Long-running file saves or network failures during S3 uploads can cause database connection timeouts if done inside atomic transactions. | Perform S3 uploads/storage operations **before** opening the DB transaction block, or keep the storage save outside `atomic()` and execute DB writes inside. |
| **Large Uploads** | Large multipart payloads can cause request timeouts, block Django worker processes, or hit Nginx `client_max_body_size` limits. | Maintain strict payload size validation. Continue to support standalone sequential uploads as the recommended path for heavy media. |
| **Security** | Arbitrary file uploads in a single payload could bypass extension checks if validation is localized to a single field. | Apply the custom `validate_file` validator universally to any file field in the serializer (`to_internal_value`). |
| **Future Maintainability** | Multipart parsing of mixed form-data and nested JSON objects (`article` parameter JSON string) is notoriously difficult to maintain and test. | Clearly document the expected request payload structures and provide comprehensive unit tests for mixed-mode payloads. |
| **Migration Challenges** | Transitioning fully to an Article-first model would require migrating existing CKEditor-inserted inline media into explicit attachment types. | Do not migrate; allow `sync_article_media` to continue identifying inline images dynamically, ensuring seamless backward compatibility. |

---

## 5. Improvement Suggestions & Architectures Comparison

Below is an objective comparison of three potential architectural patterns:

### Option 1: Pure Media-First (Status Quo)
* **Description:** Frontend must upload all files first via `/api/medias/`, retrieve the IDs, and then send a purely text JSON payload to `/api/posts/articles/`.
* **Pros:** Cleanest backend design, strong separation of concerns, high media reusability, easy to scale.
* **Cons:** Suboptimal developer experience (DX) for frontend developers; multiple roundtrips required for basic article publishing.

### Option 2: Pure Article-First (The Proposal)
* **Description:** Frontend submits everything in a single HTTP POST multipart request. Separate media uploading is completely disallowed.
* **Pros:** One-click publishing from the frontend.
* **Cons:** Breaks CKEditor integration completely; extremely high memory and performance overhead for auto-saves; blocks file reusability; very complex payload parsing.

### Option 3: Balanced Hybrid Workflow (Recommended)
* **Description:** The backend natively supports **both** workflows.
  1. It provides a robust, single-request endpoint using multipart data where `cover_image`, `og_image`, and a map of inline attachments (`files[<id>]` replacing `<img data-upload-id="...">` in the HTML body) can be processed together.
  2. It retains the standalone `/api/medias/` and CKEditor upload endpoints.
* **Pros:** Excellent DX for basic forms (e.g., mobile apps uploading a post with a cover image instantly), while maintaining full compatibility with CKEditor, large uploads, and the Shared Media Library.
* **Cons:** Requires the backend to maintain two serializer paths, but this is already elegantly solved in the current implementation of `ArticleCreateUpdateSerializer`.

---

## 6. Final Recommendation

### Final Verdict: **Adopt the Balanced Hybrid Workflow (Option 3)**

### Architectural Justifications

1. **Single Responsibility Principle (SRP):**
   The `MediaViewSet` maintains the single responsibility of managing the library. The `ArticleViewSet` manages articles. By using a hybrid approach, the responsibility of coordinating both is placed inside the serializer level (`ArticleCreateUpdateSerializer.to_internal_value`), keeping the models and core services highly cohesive and decoupled.

2. **Separation of Concerns & Extensibility:**
   Future modules (such as portfolios or landing pages) can leverage the exact same standalone `Media` system without rewriting heavy parsing logic. If they want to adopt a single-request flow later, they can implement a similar mixin at the serializer level without altering any underlying database tables or storage abstractions.

3. **Developer Experience (DX):**
   Frontend teams are not constrained by a single rigid pattern.
   - Simple mobile submission forms can use the single-request multipart flow to submit everything at once, preventing multi-step failure risks.
   - Rich web CMS dashboards can use the media-first workflow to power drag-and-drop file library widgets and instant CKEditor uploads.

4. **Reliability & Error Recovery:**
   Under the hybrid workflow, if a multipart submission fails, the backend automatically performs a cleanup using `_uploaded_media` in `ArticleViewSet` transaction rollback blocks. Standalone uploads remain safe because they are independent operations.

### Required Changes to the Project's Media Policy before Development Continues:

1. **Consolidate Upload Engines:**
   Deprecate the custom file-saving logic inside `posts/ckeditor_views.py` (`ckeditor_upload_view`). Refactor it to import and use the standard `create_media_from_file` service from `medias/services.py`. This ensures a single, secure pipeline for filename sanitization, size validation, and metadata extraction.

2. **Standardize API Error Format:**
   Ensure any upload failures inside the multipart flow return validation messages wrapped under the standard `messagesList` key, adhering to the custom response format.

3. **Explicit Media Deletion/Cleanup Task:**
   Implement a background Celery task (e.g., `delete_orphan_media`) that periodically runs (e.g., daily) to query `Media` records that do not have any corresponding entries in `ArticleMedia` or references in `AuthorProfile.avatar`. This prevents S3 or local system storage from filling up with abandoned files, solving the biggest disadvantage of both systems.

---
**Report compiled and reviewed by Jules, Lead Software Architect.**
