# Enterprise Media Architecture Forensic Audit Report

**Author:** Jules, Lead Principal Architect
**Date:** July 2026
**Subject:** Forensic Audit of the CMS Media Library Architecture & Generic Block Engine Integration

---

## Executive Summary

This forensic audit report evaluates the backend architecture of the CMS Media Library and its integration with the next-generation Generic Block Engine. Our deep-dive review of models, serializers, services, views, and permission scopes shows that the current CMS implements a hybrid, partially-integrated media system.

While a real, independent Media Library is implemented with dedicated models and REST APIs, critical integration and architectural boundaries are missing. Specifically, the system successfully employs a **"Media-First"** workflow where media is uploaded in advance and referenced by a unique ID inside JSONB content blocks, keeping content decoupled from static physical files. However, the system suffers from a **"Dual-Workflow Gap"**—there is absolutely no support for an **"Article-First"** inline upload workflow within content blocks, unlike the legacy rich-text HTML block (`content`) and cover image fields. Additionally, the database relational tracking table (`ArticleMedia`) exists but is not used to prevent safe deletion, creating a high vulnerability to database-to-content desynchronization, stale JSONB references, and unmanaged orphan files in the storage layers.

Overall, the system provides a robust schema-level foundation but is not yet fully enterprise-ready due to these critical integration gaps, unsafe deletion policies, and lack of advanced media processing (such as image variants, hashing, or responsive sizing).

---

## Architecture Diagram

Below is the visualization of the current system's flow, illustrating how Article, ArticleTranslation, Content Blocks, the Media Service, and the Media Library interact:

```
[ Frontend Client ]
         │
         ├── (1) Uploads raw file (Multipart POST to /api/media/)
         │       ▼
         │   [ MediaViewSet / MediaCreateSerializer ]
         │       │
         │       ├── (2) Invokes Service Layer
         │       │   ▼
         │       │   [ medias.services.create_media_from_file ]
         │       │       │
         │       │       ├── (3) Sanitizes filename & stores binary in default_storage
         │       │       │   ▼
         │       │       │   [ Storage Layer (Local FS / S3) ]
         │       │       │
         │       │       └── (4) Extracts metadata (MIME, Dimensions, Size) & creates record
         │       │           ▼
         │       │           [ Media Database Record ]
         │       │
         │       └── (5) Returns mediaId & URL payload
         │
         ├── (6) Creates/Updates Article with JSONB blocks list (POST/PUT to /api/posts/articles/)
         │       ▼
         │   [ ArticleCreateUpdateSerializer ]
         │       │
         │       ├── (7) Validates Block JSON Schema and resolves references
         │       │   ▼
         │       │   [ posts.services.validate_and_sanitize_blocks ]
         │       │       │
         │       │       └── Queries Media Library database to verify that media_id exists & is_active
         │       │
         │       ├── (8) Normalizes orders, sanitizes HTML tags (BeautifulSoup), and persists JSONB
         │       │   ▼
         │       │   [ ArticleTranslation.content_blocks (JSONB) ]
         │       │
         │       └── (9) Synchronizes attachment mappings
         │           ▼
         │           [ posts.services.sync_article_media ]
         │               │
         │               └── Populates [ ArticleMedia ] (Intermediary table tracking active linkages)
         │
         └── (10) Retrieves Article Detail (GET /api/posts/articles/{slug}/)
                 ▼
             [ ArticleDetailSerializer ]
                 │
                 └── (11) Batches and expands media references generically in serializer representation
                     ▼
                     Appends full "media" dictionary details directly inside Image / Gallery / Video JSON blocks
```

---

## Audit Table

| Capability | Status | File / Code Evidence | Architectural Notes |
| :--- | :---: | :--- | :--- |
| **Independent Media Library** | ✅ Implemented | `medias/models.py:Media`, `medias/views.py:MediaViewSet` | Exists as an isolated domain entity with its own database schema, API endpoints, and download logic. |
| **Upload API** | ✅ Implemented | `medias/serializers.py:MediaCreateSerializer` | Supports POST file uploads with size and extension validation. |
| **Select Existing Media** | ✅ Implemented | `posts/blocks.py:ImageBlock`, `posts/serializers.py:HybridMediaField` | Fully supported. Editors reference existing `media_id` in blocks or provide standard IDs. |
| **Upload From Block** | ❌ Missing | `posts/serializers.py`, `posts/services.py` | Content blocks do not support multi-part files inline. File upload is restricted to top-level cover/OG fields or legacy HTML content parsing. |
| **mediaId Based Storage** | ✅ Implemented | `posts/blocks.py:ImageBlock` (schema enforces `media_id` integer) | Exposes clean decoupling of media references from raw file storage inside content blocks. |
| **Media Reuse** | ✅ Implemented | `medias/models.py:ArticleMedia` (unique together constraint) | Multiple articles can reference the exact same `Media` instance. Relational bindings are mapped sequentially. |
| **Replace Image** | ⚠️ Partially | `medias/admin.py:save_model` (admin only); API is `❌ Missing` | Supported inside Django Admin by replacing files on existing records, but the REST API (`MediaDetailSerializer`) only allows editing metadata, not files. |
| **Variants & Thumbnails** | ❌ Missing | `medias/services.py` | Images are saved as-is in their original dimensions. There is no automated generation of size-based thumbnails or AVIF/WebP variant maps. |
| **Safe Delete** | ❌ Missing | `medias/views.py:MediaViewSet` (no delete hooks/restrictions) | Users can delete media records actively linked in JSONB blocks. Django CASCADE deletes `ArticleMedia` but leaves broken/stale `media_id` numbers inside block JSON on database. |

---

## Comprehensive Feature & Boundary Audits

### 1. Media Library Architecture Audit
* **Does a real Media Library exist?** Yes, status is **✅ Implemented**.
* **Evidence:**
  - **Models:** `Media` (in `medias/models.py`) stores a unified, independent database index of all uploaded digital assets.
  - **CRUD Operations:** Supported fully via `MediaViewSet` (in `medias/views.py`), which registers all default routers (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).
  - **Unique Identifier:** Uses Django's default auto-incrementing integer `id`.
  - **Metadata Coverage:** It is highly robust. Standard database fields store file characteristics:
    - `storage_key`: Filename in target storage (S3 key or local filesystem relative path).
    - `url`: Public path URL of the asset.
    - `type`: Category indicator ("image", "video", "audio", "file").
    - `mime`: MIME type (e.g. `image/jpeg`).
    - `width`/`height`: Extracted image dimensions via Pillow.
    - `size_bytes`: Integer size representation.
    - `alt_text` / `title`: Metadata descriptive contexts.
    - `uploaded_by`: ForeignKey reference tracking user ownership.
    - `created_at` / `updated_at`: Precise timestamps.
  - **Search & Filter:** *Partially Implemented*. Django Admin contains search and filter boxes (`list_filter = ("type", "mime")`, `search_fields = ("title", "alt_text")`). However, the API `MediaViewSet` completely lacks any filter/search backend integration.
  - **Reusability:** Fully functional. Multiple articles can link to the same media file ID.

---

### 2. Image Block Upload Workflow Audit
* **Workflow Evaluation:**
  Our investigation of `posts/blocks.py` and `posts/serializers.py` indicates that the system only supports a **"Media-First"** workflow.
* **Analysis:**
  - The JSON Schema for `ImageBlock` requires `media_id` as an integer:
    ```python
    "media_id": {"type": "integer", "minimum": 1}
    ```
  - The API's block validator `validate_and_sanitize_blocks` checks that the `media_id` integer points to an active database record:
    ```python
    existing_active_media_ids = set(Media.objects.filter(id__in=media_ids_to_check, is_active=True).values_list("id", flat=True))
    ```
  - There is **no mechanism** inside `content_blocks` deserialization to intercept file uploads. If a file object is submitted in the multi-part request mapped to a block ID, it will be ignored, or cause a JSON validation failure.
* **Architectural Violations:** The system fails to support the **"Article-First"** workflow for blocks, which is a major inconsistency because it *does* support it for `cover_image_id` and `og_image_id` via the custom `HybridMediaField`, and for legacy rich-text `content` via beautifulsoup inline parsing in `_process_inline_files`.

---

### 3. Direct File Storage Detection
* **Detection Audit:** We ran deep codebase searches on `content_blocks` database stores.
* **Findings:**
  - **No** base64 data, direct binary file streams, or embedded raw media data are stored inside the `content_blocks` JSONB column.
  - No file paths are saved inside block objects.
  - Blocks conform to clean REST standards, saving only `media_id` as an integer.
* **Why direct file/binary storage in JSON is an architectural anti-pattern:**
  1. **Database Bloat:** Base64 streams dramatically increase JSON size, slowing down database transactions, indexing speeds, and query parsing times.
  2. **Zero Cacheability:** Content JSON changes on every small update, preventing efficient cache pooling and CDNs from storing lightweight blocks list payload.
  3. **No Centralized Control:** Direct file-path storage bypasses the media library, meaning duplicate uploads go undetected and file deletions can never be safely tracked.

---

### 4. Existing Media Selection Workflow
* **Evaluation:** Fully supported on the backend API layer.
* **Analysis:**
  - Since standard image blocks consume `media_id`, an editor can browse existing media using `GET /api/media/` and supply any valid ID to the block payload during creation.
  - The block expansion pipeline (`get_content_blocks` in `ArticleDetailSerializer`) reads the raw IDs, performs a fast single batch query (`Media.objects.filter(id__in=media_ids)`), converts them into full detail structures, and embeds them dynamically under the `"media"` key of the output block payload.
  - This keeps the database representation highly lightweight (storing integers) while rendering fully-formed objects to client applications on read.

---

### 5. Dual Workflow Verification
* **Evaluation:** **❌ Unsupported (Dual Workflow Gap)**
* **Analysis:**
  - **Workflow A (Upload New Image via Block)**: **❌ Missing**. If a user tries to create an article and upload a file *inside* the block array in a single transaction, the serializer will fail because the block validator expects `media_id` to be an existing integer ID.
  - **Workflow B (Select Existing Image)**: **✅ Implemented**. The user sends `{"type": "image", "data": {"media_id": 123}}`, which validates, saves, and expands cleanly.
* **Consequence:** Editors are forced to adopt a multi-step sequence: upload media to `/api/media/` first, wait for the response, grab the `id`, compile the block JSON, and then POST to create the article.

---

### 6. Media Service Boundary Audit
* **Evaluation:** Partially respected but displays minor leaks.
* **Analysis:**
  - Standard file creations are correctly delegated to the central service helper `create_media_from_file` (in `medias/services.py`).
  - **Leakage of Concerns:** Inside `posts/serializers.py`, the `HybridMediaField` and `_process_inline_files` methods contain file-handling logic (such as checking anonymous users, invoking `validate_file`, and instantiating inline media uploads) that directly calls `create_media_from_file` inside the representation layer.
  - In a strict enterprise architecture, file validation, duplication checks, and processing hooks must reside solely inside a robust `MediaService` class rather than being scattered across DRF serializer fields and private utility functions.

---

### 7. Media Reuse Capability
* **Evaluation:** Fully compatible at the relational database level.
* **Analysis:**
  - The `ArticleMedia` model maintains references using the following composite constraint:
    ```python
    unique_together = ("article", "media", "attachment_type")
    ```
  - This allows multiple independent articles (e.g. Article 1, Article 2, etc.) to link to the exact same `Media` row.
  - **Missing Enterprise Features:** No dependency tracking dashboard, active references usage counters, or usage lists are available. Deleting a `Media` record does not inform the user which articles currently rely on it.

---

### 8. Media Lifecycle Audit

The complete lifecycle for media assets is traced below:

```
[1. Upload]             ──► Received as multipart file via API /api/media/ or Django Admin.
                             │
[2. Validation]         ──► `validate_file` checks size (<10MB) and extension array. No magic-number verification.
                             │
[3. Storage Layer]      ──► `default_storage.save` writes physical binary to local disk or S3.
                             │
[4. Metadata Extraction]──► Pillow parses image width/height. MIME/size captured.
                             │
[5. Database Record]    ──► `Media.objects.create` saves database record with auto-assigned ID.
                             │
[6. Usage Tracking]     ──► `sync_article_media` scans block JSON on save, creating/deleting mapping rows in `ArticleMedia`.
                             │
[7. Rendering]          ──► `ArticleDetailSerializer` fetches JSON blocks, fetches Media records, and expands them inline.
                             │
[8. Deletion]           ──► permanent deletion via DELETE endpoint. Cascades relationship, but leaves stale references.
```

---

### 9. Advanced Media Features
We audited advanced operational features within the backend code:

| Feature | Status | Forensic Notes & Code Evidence |
| :--- | :---: | :--- |
| **Drag & Drop Upload** | ⚠️ Partial | Supported on standard API endpoints since they accept file inputs. The visual drag-and-drop itself is entirely dependent on frontend layout components. |
| **Replace Image** | ⚠️ Partial | Admin Panel form supports replacement via custom model saving. The public REST API lacks file replacement support because `MediaDetailSerializer` has no write-enabled file field. |
| **Image Variants** | ❌ Missing | No variant mapping or size-based resizing occurs on upload. Physical files are stored strictly in their raw original upload dimensions. |
| **Thumbnail Generation**| ❌ Missing | No automatic generation of square icons or lightweight preview thumbnails. |
| **Crop Support** | ❌ Missing | No coordination, coordinate parameters, or Pillow cropping interfaces exist in the service layer. |
| **Responsive Images** | ❌ Missing | Serializers do not output `srcset` payloads or high-density alternative URLs. |
| **CDN Support** | ✅ Implemented | Supported globally via `USE_CDN` and `CDN_DOMAIN` settings (in `blog/settings.py`) which append the CDN domain prefix to file URLs. |
| **Duplicate Detection** | ❌ Missing | Uploading the exact same image twice creates two identical files with unique storage paths, wasting database space. |
| **Hash Based Storage** | ❌ Missing | Storage keys use original sanitized filenames rather than cryptographic hashes (like MD5 or SHA-256) of file content. |

---

### 10. Security Audit
Our security review of the Media subsystem reveals several gaps:
* **File Type & Size Verification:**
  - Excellent: File sizes are limited strictly to 10MB (`validate_file` in `common/validators.py`).
  - Ext-Check: Only specified formats are allowed.
  - **Critical Gap:** Ext-Check relies purely on string splitting: `ext = str(value).split(".")[-1].lower()`. If an attacker uploads a malicious executable file named `exploit.jpg` containing raw PHP or Python code, and the backend does not check the file's binary signature (using a library like `python-magic`), the file will be accepted.
* **Access Control & Permissions:**
  - Very Secure: `MediaViewSet` permissions are bound to `IsAuthorOrAdmin`, preventing unauthenticated users from uploading or modifying files.
  - Modification isolation: Safe methods are restricted; authors can only modify/delete media they uploaded (`uploaded_by == request.user`).
* **Storage Isolation:** None. All users' uploads are stored in a single folder hierarchy, with no containerization or isolated bucket paths.

---

### 11. Database Relationship Audit
* **Model Analysis:**
  - `ArticleMedia` model tracks active links between `Article` and `Media` models.
  - **Delete Behavior Vulnerability:**
    - If an admin deletes a `Media` object via `DELETE /api/media/123/`, the Django database engine cascade-deletes the `ArticleMedia` mapping row.
    - BUT PostgreSQL and Django have **no awareness** of the raw integer reference `"media_id": 123` buried inside the `content_blocks` JSONB column.
    - Thus, the JSON content blocks are **never updated**, leaving stale, broken ID references in the database.
* **Can the system safely determine whether a media file is still being used?**
  - **No.** While the `ArticleMedia` relationship table tracks active references, the system **does not use this information** to block media deletion.
  - There is no protection, trigger, or warning inside `Media.delete()` or `MediaViewSet.destroy()` to prevent deleting a media file that is actively used in one or more articles. Deleting it instantly breaks the rendering of those articles.

---

## Critical Findings

The findings of this audit are prioritized below into actionable engineering categories:

### Critical Priority (Requires Immediate Fixes)
1. **Unsafe Media Deletion (Broken Integrity):**
   Deletions on the `Media` model are unchecked. Deleting an asset instantly causes stale/broken references inside `ArticleTranslation.content_blocks` JSON. Any future attempt to edit and save that article will crash or throw validation errors because `validate_and_sanitize_blocks` verifies that all block-referenced media IDs exist.
2. **Lack of File Content Verification (Spoofing Vulnerability):**
   The file-extension validator checks only the filename string (`.jpg`, `.png`). It does not verify the actual binary MIME type using file signatures (magic numbers). This allows attackers to upload executable scripts by simply appending a safe image extension.

### High Priority
1. **The Dual-Workflow Gap:**
   Image blocks inside the `content_blocks` list cannot accept inline files. This forces client developers to adopt a fragmented sequence where files must be uploaded first before the article is created.
2. **Missing Orphan File Deletion:**
   Deleting a `Media` database record does not trigger a post-delete handler to remove the actual file from physical storage. Over time, this leads to significant storage leakage and accumulating costs.

### Medium Priority
1. **API Search & Filter Gap:**
   `MediaViewSet` lacks any DRF search or filter backends, preventing client applications from displaying a searchable visual media gallery.
2. **File Duplication:**
   Uploading the exact same image multiple times creates duplicate files on S3/filesystem, which can cause significant storage overhead.

### Recommendations & Modern Standard Architecture
* **Safe Deletion Pre-delete Signal:**
  Implement a `pre_delete` signal on the `Media` model. It must check `ArticleMedia` and block deletions if active attachments exist, raising a clean validation error to prevent broken article layouts:
  ```python
  @receiver(pre_delete, sender=Media)
  def prevent_active_media_deletion(sender, instance, **kwargs):
      if instance.article_attachments.exists():
          raise ValidationError("Cannot delete media: It is actively linked to published content.")
  ```
* **Implement File Magic Verification:**
  Enhance `validate_file` to use `python-magic` to parse actual file content byte streams and confirm they match allowed extensions, blocking executable file spoofing.
* **Consolidate MediaService boundaries:**
  Move inline media extraction, `HybridMediaField` upload handlers, and other custom file processing functions into a unified `MediaService` utility class to ensure clean separation of concerns.

---

## Final Architecture Verdict

1. **Is the current Media architecture compatible with the Block Engine?**
   **Yes, but only partially.** The schema and serializer expansion layer are well-designed. However, the lack of referential safety on delete and the dual-workflow gap prevent it from being a fully robust and integrated solution.
2. **Is it Enterprise-ready?**
   **No.** It lacks fundamental enterprise requirements: safe delete barriers, file content security validation, automatic variant/thumbnail rendering, and automatic cleanup of orphaned files in storage.
3. **Does it require a dedicated Media subsystem implementation?**
   **No, the current medias app is a solid foundation.** Rather than starting over, the system simply requires reinforcing the boundaries of the existing `medias` app—specifically implementing a safe-delete pre-delete signal, upgrading file validation, and creating a unified service class to resolve the dual-workflow gap.
4. **What must be fixed before further CMS development?**
   1. Fix the **stale-reference/broken validation loop** by adding a safe-delete block on the `Media` model.
   2. Secure the upload pipeline against **executable-extension spoofing** by verifying file headers/signatures instead of just the file extension.
   3. Add **automated physical file cleanup** to ensure deleting database records frees up disk/S3 storage.
