# Enterprise Block-Based Content Architecture Specification

This document presents the technical design and architectural specification for our next-generation, Enterprise-grade **Block-Based Content Engine**. Transitioning from a traditional single rich-text field to a highly flexible block-based design enables modular content publishing across multiple platforms (Web, Mobile, AMP, etc.) while maintaining high system stability, complete compatibility with PostgreSQL and Django, and a seamless developer experience.

---

## 1. Core Design Philosophy

The traditional approach to CMS content structure is "Document-oriented" or "Section-oriented" where predefined areas bind media elements to text fields. This design pattern restricts content layout and presentation flexibility, making omnichannel content delivery difficult.

The next-generation architecture introduces a purely **Block-Based Content Philosophy** inspired by modern systems like Notion, Gutenberg, Editor.js, Sanity, and Storyblok.

### Principal Axioms

1. **Atomic Independence**: An article is modeled strictly as a flat, ordered list of independent Blocks. A Block is the minimal, indivisible unit of content presentation.
2. **Deterministic Ordering**: The relative order of Blocks in the storage array is the sole arbiter of rendering order.
3. **Decoupled Associations**: No implicit or explicit relationship exists between different types of blocks unless declared as structured data. Specifically:
   - There is no `media_position` flag on a text block.
   - There is no relational hierarchy of "Image belongs to Paragraph".
   - If an image must appear between two paragraphs, it is saved as an independent `ImageBlock` positioned sequentially between two `ParagraphBlocks`.
4. **Absolute Composability**: Any arbitrary block sequence is valid. Authors are free to create sequences such as:
   - `Heading` $\rightarrow$ `Image` $\rightarrow$ `Image` $\rightarrow$ `Image` $\rightarrow$ `Paragraph` $\rightarrow$ `Paragraph` $\rightarrow$ `Video` $\rightarrow$ `Gallery` $\rightarrow$ `Quote`
   - `Paragraph` $\rightarrow$ `Paragraph` $\rightarrow$ `Paragraph` $\rightarrow$ `Image` $\rightarrow$ `Image` $\rightarrow$ `Divider` $\rightarrow$ `Code`

### ASCII Conceptual Diagram

```
+-----------------------------------------------------------------------+
|                             Article                                   |
+-----------------------------------------------------------------------+
                                   |
                                   | 1 : N (Translations / Locales)
                                   v
+-----------------------------------------------------------------------+
|                       ArticleTranslation                              |
|   - language_code: "fa" / "en" / "ar"                                 |
|   - content_blocks: JSONField (List of Blocks)                        |
+-----------------------------------------------------------------------+
                                   |
         +-------------------------+-------------------------+
         |                         |                         |
         v                         v                         v
+-----------------+       +-----------------+       +-----------------+
|   Block [1]     |       |   Block [2]     |       |   Block [3]     |
|  type: heading  |       |  type: paragraph|       |   type: image   |
+-----------------+       +-----------------+       +-----------------+
```

---

## 2. Block Structure & JSON Design

Every block conforms to a uniform, standard container envelope. This strict metadata casing ensures that the core rendering pipeline, parsing algorithms, and query engines can traverse block arrays without needing to inspect individual domain payloads.

### Standard Block Envelope

```json
{
  "id": "blk_9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "type": "paragraph",
  "version": 1,
  "order": 3,
  "settings": {
    "background_color": "#ffffff",
    "text_alignment": "justify",
    "padding": "medium"
  },
  "metadata": {
    "created_by": 42,
    "last_modified_at": "2026-03-31T12:00:00Z"
  },
  "data": {
    "text": "معماری بلاک‌محور پایداری فوق‌العاده‌ای برای مدیریت تغییرات ارائه می‌دهد."
  }
}
```

### Property Dictionary and Justification

* **`id` (UUIDv4 or Custom K-Sortable ID)**:
  * *Purpose*: A globally unique identifier for the block instance.
  * *Justification*: Required for real-time collaborative editing algorithms (e.g., CRDTs/Yjs), DOM element keying in modern reactive frameworks (React, Vue) to prevent unnecessary re-renders, and precise visual-editor change tracking.
* **`type` (String)**:
  * *Purpose*: The block identifier (e.g., `heading`, `paragraph`, `image`).
  * *Justification*: Acts as the polymorphism key used by the Serializer and the Frontend Rendering Engine to route the block payload to the appropriate schema validator and UI component.
* **`version` (Positive Integer)**:
  * *Purpose*: The schema version of the specific block block type.
  * *Justification*: Enables smooth backward compatibility and database schema evolution. If a future version of `ImageBlock` requires a nested structure, existing blocks are kept at `version: 1` and upgraded lazily or via migration scripts in the service layer.
* **`order` (Integer)**:
  * *Purpose*: Explicit rendering rank.
  * *Justification*: Although the JSON array maintains native ordering, an explicit `order` field acts as a fail-safe index. It allows the backend to easily re-index, sort, and reconcile positions during patch updates and drag-and-drop operations, avoiding race conditions.
* **`settings` (Object)**:
  * *Purpose*: Non-semantic visual styles or presentation configurations (margins, colors, widths, animations).
  * *Justification*: Separates pure content data (`data`) from presentation settings (`settings`), making it easy to repurpose the same raw content across head-less channels (like smartwatches, voice assistants, and native mobile apps) where CSS classes are irrelevant.
* **`metadata` (Object)**:
  * *Purpose*: Non-renderable audit and contextual information (creation timestamp, author user ID, search indexes).
  * *Justification*: Facilitates internal business analytics and editor actions without polluting the payload with display components.
* **`data` (Object)**:
  * *Purpose*: The core semantic payload of the block.
  * *Justification*: Houses the block's unique attributes, isolated from structural metadata. For a paragraph, this holds rich text. For video, this contains streaming credentials and playback settings.

---

## 3. Block Types

The Block Content Engine is designed as an open-ended classification system. Each block type is registered within the platform registry and can evolve its internal schema version independently.

Below is the definitive catalog of core block schemas:

### Core Block Classification

1. **`heading`**:
   * *Data Schema*: `{"level": 1|2|3|4|5|6, "text": "...", "anchor_id": "..."}`
   * *Settings*: Inline alignments, CSS class hooks.
2. **`paragraph`**:
   * *Data Schema*: `{"text": "..."}` (Supports verified inline HTML such as `<strong>`, `<em>`, `<a>`).
3. **`image`**:
   * *Data Schema*: `{"media_id": 42, "caption": "...", "alt": "...", "lazy": true}`
4. **`gallery`**:
   * *Data Schema*: `{"media_ids": [42, 43, 44], "layout": "grid"|"slider", "aspect_ratio": "16:9"}`
5. **`quote`**:
   * *Data Schema*: `{"text": "...", "citation": "..."}`
6. **`table`**:
   * *Data Schema*: `{"headers": ["Col 1", "Col 2"], "rows": [["Cell A1", "Cell B1"], ["Cell A2", "Cell B2"]]}`
7. **`code`**:
   * *Data Schema*: `{"code": "...", "language": "python", "show_line_numbers": true}`
8. **`divider`**:
   * *Data Schema*: `{"style": "solid"|"dashed"|"dots"}`
9. **`video`**:
   * *Data Schema*: `{"media_id": 85, "provider": "local"|"youtube"|"vimeo", "external_url": "...", "autoplay": false, "controls": true}`
10. **`embed`**:
    * *Data Schema*: `{"url": "...", "embed_type": "twitter"|"instagram"|"iframe", "width": 600, "height": 400}`
11. **`button`**:
    * *Data Schema*: `{"label": "...", "url": "...", "target": "_blank"|"_self", "style_preset": "primary"}`
12. **`accordion`**:
    * *Data Schema*: `{"items": [{"title": "Question", "content": "Answer Block Data"}]}`
13. **`faq`**:
    * *Data Schema*: `{"questions": [{"q": "...", "a": "..."}]}` (Specifically formatted for Google's Rich Snippet ingestion).
14. **`timeline`**:
    * *Data Schema*: `{"events": [{"date": "...", "title": "...", "description": "..."}]}`
15. **`related_articles`**:
    * *Data Schema*: `{"article_ids": [102, 105, 120]}` (Dynamic server-resolved block rendering complete article previews).
16. **`custom_plugin_blocks`**:
    * *Data Schema*: Dynamic, open schematics conforming to third-party plugin interface validation.

---

## 4. Plugin & Registry Architecture

Hardcoded conditional blocks (`if type == 'paragraph'`) are the primary source of technical debt in modern content engines. To prevent this, the Block Engine implements a formal **Block Registry Architecture**.

### The Block Registry Class Pattern

The Django Service Layer manages a central registry where developers can mount custom blocks. Each block type registration must subclass an abstract `BaseBlock` class and define its validation rules, serialization routines, rendering logic, editor configuration, and migration strategies.

```
                  +------------------------+
                  |     BlockRegistry      | <---+ Dynamic Registration
                  +------------------------+
                               |
            +------------------+------------------+
            v                                     v
+------------------------+             +------------------------+
|      HeadingBlock      |             |     ParagraphBlock     |
+------------------------+             +------------------------+
| - validation           |             | - validation           |
| - serializer           |             | - serializer           |
| - renderer             |             | - renderer             |
| - editor_config        |             | - editor_config        |
| - migration_strategy   |             | - migration_strategy   |
+------------------------+             +------------------------+
```

### Specification for Abstract Block Class

Every Block class implementation must satisfy the following interfaces:

1. **`validation(payload: dict)`**: Evaluates JSON input against the block type's specific schema using draft-07 JSON Schema validation or custom Pydantic models.
2. **`serializer`**: Returns a designated Django REST Framework Serializer class responsible for converting raw database JSON blocks into clean representation payloads (e.g., expanding database foreign key relations).
3. **`renderer(data: dict, settings: dict)`**: Backend template-based renderer used for static HTML rendering, RSS feeds, and headless fallback views.
4. **`editor_config`**: Exportable JSON configuration outlining the block's parameters, capabilities, available styles, and metadata templates to guide the frontend editor's behavior dynamically.
5. **`migration_strategy`**: A collection of schema version transform methods (e.g., `upgrade_v1_to_v2`, `downgrade_v2_to_v1`) used to resolve outdated data formats during read or write pipelines without modifying database structures on disk.

---

## 5. Media Integration

In accordance with our strict architectural separation, **Media is represented exclusively by dedicated, autonomous blocks**. Embedding binary media or nested media properties inside text-based elements violates Clean Architecture guidelines.

### Strict Separation Principle
- A text block containing HTML is processed to verify that it does not contain inline media representations like base64 or static file paths.
- Images, galleries, and videos must be declared via dedicated blocks (`image`, `gallery`, `video`).
- Media references are validated against the central `medias.Media` entity using `media_id`. This preserves relational integrity while maintaining storage flexibility.

### Image Block Structure Example

```json
{
  "id": "blk_df64df5a-0d86-4e56-b07f-e77a808e08d6",
  "type": "image",
  "version": 1,
  "order": 4,
  "settings": {
    "display_width": "full_width",
    "border_radius": "8px"
  },
  "data": {
    "media_id": 42,
    "caption": "Architectural class interactions between Django models and services",
    "alt": "Clean architecture visual map",
    "lazy": true
  }
}
```

### Media Expansion Pipeline

When the API returns block lists to client applications, raw `media_id` numbers are automatically expanded. This is done by querying the `medias.Media` model inside the serializer representation layer, avoiding multiple queries (N+1 queries) via batched prefetches:

```json
{
  "id": "blk_df64df5a-0d86-4e56-b07f-e77a808e08d6",
  "type": "image",
  "version": 1,
  "order": 4,
  "settings": {
    "display_width": "full_width",
    "border_radius": "8px"
  },
  "data": {
    "media_id": 42,
    "caption": "Architectural class interactions between Django models and services",
    "alt": "Clean architecture visual map",
    "lazy": true,
    "media": {
      "id": 42,
      "url": "https://cdn.example.com/medias/2026/03/architecture-map.avif",
      "mime_type": "image/avif",
      "width": 1920,
      "height": 1080,
      "size_bytes": 145020,
      "title": "Clean Architecture Map"
    }
  }
}
```

---

## 6. Validation Strategy

Data integrity in JSON fields requires a strict, multi-tiered validation pipeline. Our enterprise architecture addresses this by validating data at multiple levels:

```
[Incoming Request]
        |
        v
[1. Multi-tier Serializer Validation] ---> Checks overall list format & length
        |
        v
[2. JSON Schema Validator] --------------> Validates block schemas via Registry
        |
        v
[3. Business Integrity Validation] -------> Checks duplicate IDs, orders, empty blocks
        |
        v
[4. Media Referential Validation] --------> Batches queries to check if Media exists
        |
        v
[Database Commit]
```

### Multi-tiered Validation Pipeline

#### 1. JSON Schema Validation
Using draft-07 of the standard JSON Schema, the payload is parsed at the API boundary to verify it contains required keys (`id`, `type`, `order`, `data`). It then delegates sub-schema validation to the Block Registry based on the block `type`.

#### 2. Duplicate Order Validation
Ensures that no two blocks share the same `order` index. If orders are mismatched, or skipped, the backend's Service Layer normalizes them sequentially (e.g., `[1, 3, 3, 5]` becomes `[1, 2, 3, 4]`) before writing to the database.

#### 3. Unsupported Version Handlers
If a block contains a version number higher than what is currently registered (e.g., a version 2 block is posted to a system that only supports version 1), the system rejects the transaction with a clear error payload. This prevents data corruption during rollbacks.

#### 4. Invalid Media Verification
The validator extracts all `media_id` fields from the block list and runs a single `EXISTS` query in PostgreSQL:
```sql
SELECT id FROM medias_media WHERE id IN (extracted_ids);
```
If any referenced media IDs do not exist, a validation error is thrown.

#### 5. Empty Content Filter
Strips out empty paragraphs and image blocks that do not have either text, a caption, or a `media_id`. This prevents bloated articles from degrading rendering performance.

#### 6. Payload and Block Limits
Enforces system safety constraints:
- Maximum blocks per article: 200 blocks.
- Maximum request payload size: 5 Megabytes.
Any request that exceeds these limits is blocked before serialization to protect against Denial of Service (DoS) attacks.

---

## 7. Rendering Pipeline

To ensure maximum performance and SEO capabilities, the block rendering pipeline is decoupled. Rendering takes place in a multi-stage flow that separates data from HTML generation:

```
+--------------------------------------------------------+
|                      Django API                        |
| - Retrieves compact JSONB blocks                       |
| - Expands Media IDs using cached DB values             |
+--------------------------------------------------------+
                           |
                           | Fast JSON Transfer
                           v
+--------------------------------------------------------+
|               Headless Frontend (Next.js)              |
| - Receives fully expanded JSON blocks payload          |
| - Dispatches blocks to designated components           |
+--------------------------------------------------------+
                           |
            +--------------+--------------+
            |                             |
            v                             v
+-----------------------+     +-----------------------+
|  Server-Side (SSR)    |     |  Client-Side (Hyd.)   |
| - Generates HTML      |     | - Adds interactivity  |
| - Prefetches critical |     | - Lazy-loads below-   |
|   above-fold blocks   |     |   the-fold components |
+-----------------------+     +-----------------------+
```

### Headless Frontend Rendering
Client-side frameworks (Next.js/React) consume the API response and map block structures directly to optimized frontend components. This is handled using a dynamic dispatcher pattern.

#### Frontend Component Dispatcher Pattern
The frontend maps block types to React components using a dictionary registry:

```typescript
// Conceptual Block-to-Component Mapping Dict
const BLOCK_COMPONENTS: Record<string, React.FC<any>> = {
  heading: HeadingBlockComponent,
  paragraph: ParagraphBlockComponent,
  image: ImageBlockComponent,
  gallery: GalleryBlockComponent,
  video: VideoBlockComponent,
  quote: QuoteBlockComponent,
};
```

During rendering, the list is sorted by `order` and mapped dynamically:
- Components below the viewport are wrapped in a dynamic lazy loading container (`IntersectionObserver`).
- Critical components (like top-level headings and the cover image) are rendered immediately during Server-Side Rendering (SSR). This avoids layout shifts (CLS) and improves Largest Contentful Paint (LCP) metrics.

---

## 8. Django Clean Architecture Integration

To preserve Clean Architecture boundaries, the Django layer separates domain logic, serialization, database persistence, and presentation.

```
       [ Django Request Entry Point (DRF View/Controller) ]
                                |
                                v
                [ Serializer Representation Layer ]
              (Dispatches JSONField to Block Registry)
                                |
                                v
               [ Core Domain / Service Layer Logic ]
         (Anti-XSS, Media Sync Tracking, Order Normalization)
                                |
                                v
               [ Database Persistence (JSONB on DB) ]
```

### 1. Database Model Integration
The Django database model `ArticleTranslation` stores content blocks within a native PostgreSQL `JSONField` (using the `JSONB` binary data format):

```python
class ArticleTranslation(BaseModel):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="translations")
    language_code = models.CharField(max_length=10, db_index=True)
    content_blocks = models.JSONField(default=list)  # Replaces legacy rich-text fields
```

### 2. Serializer Architecture
Serialization is handled using custom serializers in Django REST Framework. The `JSONBlockSerializer` reads the list, validates its structure, and processes internal content:

- **`to_internal_value`**: Checks the block structure against schema definitions from the Block Registry.
- **`to_representation`**: Collects all `media_id` values across all blocks in a single pass. It then loads the media details in a single query and embeds them into their respective blocks.

### 3. Service Layer Functions
To keep business logic decoupled from Django's built-in framework classes, core operations are handled by dedicated service layers:

- **`BlockXSSSanitizer`**: Parses and sanitizes text blocks using `BeautifulSoup`, stripping out harmful inline script tags and inline style injection vectors.
- **`BlockOrderManager`**: Sequentially re-numbers blocks during updates, resolving conflicts when authors perform complex drag-and-drop operations.
- **`MediaReferenceSynchronizer`**: Keeps track of media usage in blocks and updates the `ArticleMedia` intermediate table. This prevents referenced media from being accidentally deleted from the media library.

### 4. Admin Visual Editor Design
The Django Admin panel uses a custom Alpine.js editor interface that overlays the standard `JSONField` input. It offers a visual layout editor without requiring external build pipelines:

- **Visual Editor View**: Renders each block as a visual card (e.g. Paragraph editor, Image selector) inside the Django admin.
- **State Synchronization**: Any updates, block additions, deletions, or re-ordering events in the UI instantly update the hidden `content_blocks` JSON text field, ensuring compatibility with Django's native form validation.

---

## 9. Admin Panel Visual Editor Interface

Managing block-based content requires an intuitive, visual editor. The CMS platform integrates a React-based Block Editor (integrated into the Django Admin or a dedicated dashboard) that interacts directly with the structured block data.

### 1. Editor Functionality

#### Drag & Drop Reordering
Every block is wrapped in a drag-and-drop boundary (using libraries like React Beautiful DnD or dnd-kit). Dropping a block updates the `order` property across all blocks in the collection.

#### Inline Block Commands (Add / Delete / Duplicate)
- Hovering between blocks displays an inline "Add Block" button, prompting the editor to choose a block type.
- Each block has a dedicated action menu with options to duplicate (which clones the block with a new unique ID and increments subsequent orders) or delete.

#### Undo / Redo Architecture
The editor UI maintains an internal state stack for user changes:
```typescript
interface EditorHistory {
  past: Block[][];
  present: Block[];
  future: Block[][];
}
```
Pressing `Ctrl + Z` or `Ctrl + Y` updates the block collection state in real-time, matching standard desktop application behaviors.

#### Keyboard Shortcuts
- `Enter` inside a `Paragraph` block creates a new paragraph block directly below.
- `Backspace` at the beginning of an empty block deletes it and focuses the block above.
- `/` triggers an inline autocomplete command list to quickly swap the current block type (e.g., `/image`, `/heading`).

#### Live Side-by-Side Preview
Renders a mock preview of the content using the headless frontend's styling. Editors can view how changes will look on desktop, tablet, and mobile displays side-by-side in real-time.

---

## 10. API Specification & Contracts

The Block-Based CMS exposes standard JSON contracts for reading and writing data, with localized error handling.

### 1. Retrieve Article Request (GET)

**Endpoint**: `/api/v1/articles/{slug}/?lang=fa`

#### Response Contract (200 OK)

```json
{
  "status": "success",
  "data": {
    "id": 142,
    "language_code": "fa",
    "title": "معماری توزیع‌شده با جنگو",
    "slug": "معماری-توزیع-شده-با-جنگو",
    "content_blocks": [
      {
        "id": "blk_a1b2c3d4-1111-4444-8888-999999999999",
        "type": "heading",
        "version": 1,
        "order": 1,
        "settings": {
          "text_alignment": "right"
        },
        "data": {
          "level": 2,
          "text": "معماری سیستم چیست؟"
        }
      },
      {
        "id": "blk_a1b2c3d4-2222-4444-8888-999999999999",
        "type": "paragraph",
        "version": 1,
        "order": 2,
        "settings": {},
        "data": {
          "text": "در این بخش به بررسی الگوهای مدرن توزیع داده در بسترهای ابری می‌پردازیم."
        }
      },
      {
        "id": "blk_a1b2c3d4-3333-4444-8888-999999999999",
        "type": "image",
        "version": 1,
        "order": 3,
        "settings": {
          "display_width": "contained"
        },
        "data": {
          "media_id": 88,
          "caption": "نمودار معماری توزیع شده",
          "alt": "Distributed architecture chart",
          "lazy": true,
          "media": {
            "id": 88,
            "url": "https://cdn.example.com/medias/2026/03/dist-arch.png",
            "mime_type": "image/png",
            "width": 800,
            "height": 600,
            "title": "Distributed Arch Map"
          }
        }
      }
    ]
  },
  "messagesList": []
}
```

---

### 2. Update Article Request (PUT / PATCH)

**Endpoint**: `/api/v1/articles/142/`

#### Request Payload

```json
{
  "language_code": "fa",
  "title": "معماری توزیع‌شده با جنگو",
  "content_blocks": [
    {
      "id": "blk_a1b2c3d4-1111-4444-8888-999999999999",
      "type": "heading",
      "version": 1,
      "order": 1,
      "settings": {},
      "data": {
        "level": 2,
        "text": "معماری سیستم چیست؟"
      }
    },
    {
      "id": "blk_a1b2c3d4-3333-4444-8888-999999999999",
      "type": "image",
      "version": 1,
      "order": 2,
      "settings": {},
      "data": {
        "media_id": 99999,
        "caption": "تصویر نامعتبر تست",
        "alt": "Missing media test",
        "lazy": true
      }
    }
  ]
}
```

#### Error Response Contract (400 Bad Request)

If business rules or media checks fail, the API returns standardized validation errors mapped directly to the invalid blocks:

```json
{
  "status": "error",
  "data": null,
  "messagesList": [
    {
      "field": "content_blocks[1].data.media_id",
      "message": "رسانه‌ای با شناسه ۹۹۹۹۹ در کتابخانه رسانه‌ها وجود ندارد."
    }
  ]
}
```

---

## 11. Performance Analysis & Scalability

Operating a high-traffic block-based CMS requires optimizing payload size, network delivery, and database operations.

### 1. Database Indexing & JSONB Execution
Storing blocks in a native PostgreSQL `JSONB` column provides excellent read performance. Because blocks are fetched in a single row query, the system avoids complex table joins:
- To optimize search and filtration, the system uses a **Generalized Inverted Index (GIN)** on the JSONB field:
  ```sql
  CREATE INDEX idx_article_translation_blocks ON posts_articletranslation USING gin (content_blocks);
  ```
- This allows PostgreSQL to run complex structural queries in milliseconds:
  ```sql
  SELECT * FROM posts_articletranslation WHERE content_blocks @> '[{"type": "video"}]';
  ```

### 2. Payload Optimization
- To prevent heavy payloads from slowing down client applications, text values within `Paragraph` and `Heading` blocks are truncated in list views (e.g. search pages or categories).
- Full blocks are only returned when requesting the detail view of an article.

### 3. Caching & CDN Delivery Strategy
- **Layer 1: Redis Cache-Aside**: Detailed responses with fully expanded media objects are cached in Redis under structured cache keys:
  ```
  active_article:detail:{language_code}:{slug}
  ```
- **Layer 2: CDN Caching**: Edge CDN nodes (like Cloudflare or CloudFront) cache API responses using custom HTTP header rules (`Cache-Control: public, max-age=31536000, s-maxage=604800, stale-while-revalidate=60`). This reduces load on backend servers by serving read requests directly from the edge.
- **L1/L2 Cache Invalidation**: When an article is updated, a Django signal triggers a task to purge the CDN cache and update the Redis cache in the background.

### 4. Lazy Loading & Image Optimization
Images are dynamically resized by the media CDN based on the frontend's display parameters:
- Images are requested in next-generation formats (`AVIF`, `WebP`) with explicit dimension headers, preventing visual layout shifts (CLS).
- Off-screen images use native lazy loading (`loading="lazy"`), drastically reducing initial bandwidth usage.

---

## 12. Security Analysis & Mitigation

Enterprise content publishing must protect against common security vulnerabilities, such as malicious user input and denial of service attacks.

```
       [ Dangerous Payload Input ]
                    |
                    v
  [ BeautifulSoup HTML Sanitizer Block ]
  - Strips dangerous HTML tags (<script>, etc)
  - Enforces safe text protocols
                    |
                    v
       [ CORS & API Key Middleware ]
  - Validates source origins and API permissions
                    |
                    v
       [ DB Isolation Sandbox ]
```

### 1. XSS (Cross-Site Scripting) Mitigation
Because editors can input HTML formatting into text-based blocks, the backend uses a strict sanitization process:
- All incoming HTML strings in `Paragraph` and `Heading` blocks are processed by **BeautifulSoup** using a strict safelist.
- Any dangerous tags (such as `<script>`, `<iframe>`, `<embed>`, `<onload>`) are stripped out.
- This ensures that only safe tags (like `<strong>`, `<em>`, `<a>`, `<code>`) are saved to the database.

### 2. Media Ownership & Verification
- When checking `media_id` references, the system verifies that the media has been successfully processed and is marked as "active".
- This prevents editors from referencing unfinished uploads, private assets, or deleted system files.

### 3. Payload and Request Security
- Enforces strict limits on POST request payload sizes (5MB limit) to protect against buffer overflow and DoS attacks.
- Implements rate limiting on write endpoints using Django Rest Framework middleware.

---

## 13. SEO & Accessibility (a11y)

The structured format of block-based content is highly beneficial for search engine optimization (SEO) and accessibility.

### 1. Heading Hierarchy Control
- The API validates that headings follow a sequential order (e.g., an `H3` is preceded by an `H2` within the block array).
- This structure helps search engines parse the article outline accurately, improving search rankings.

### 2. Image Metadata Enforcement
- Accessible rich text is maintained by making the `alt` property mandatory on all `ImageBlock` schemas.
- If an editor leaves the Alt text blank, the block defaults to using the media asset's global title, ensuring screen readers always have descriptive text.

### 3. Automatic Structured Data (Schema.org JSON-LD)
Because the article is structured as an array of typed blocks, the frontend can easily generate semantic structured data:
- An article containing a `video` block automatically generates `VideoObject` metadata.
- An article with an `faq` block generates `FAQPage` structured data.
This allows search engines to display rich snippets, improving click-through rates.

### 4. Semantic HTML Output
The headless rendering engine converts blocks into semantic HTML elements:
- `heading` $\rightarrow$ `<h2>` / `<h3>`
- `paragraph` $\rightarrow$ `<p>`
- `quote` $\rightarrow$ `<blockquote>`
- `divider` $\rightarrow$ `<hr>`
- `table` $\rightarrow$ `<table>`, `<thead>`, `<tbody>`
Using clean semantic HTML ensures maximum compatibility with web browsers and screen readers.

---

## 14. Schema Evolution & Future Compatibility

Adding new block types (such as `timeline`, `accordion`, or `custom_plugin_blocks`) to a running enterprise system must be seamless. The block-based architecture handles this without database schema migrations.

### How Dynamic Expansions Avoid Database Migrations

```
      +------------------------------------------------+
      |      PostgreSQL Database (No migrations)       |
      | - content_blocks column contains raw JSONB.    |
      +------------------------------------------------+
                               |
                               | Unmodified Data
                               v
      +------------------------------------------------+
      |               Django Registry                  |
      | - Add a new block definition class.            |
      | - Register schema validation rules.            |
      +------------------------------------------------+
                               |
                               | Runtime Interceptor
                               v
      +------------------------------------------------+
      |               Headless Frontend                |
      | - Render component for the new block type.     |
      | - Seamless fallback for older block versions.  |
      +------------------------------------------------+
```

### Protocol for System Upgrades

1. **Schema-less Adaptations**: Because blocks are stored in a standard JSON list, adding a new block type only requires defining its structure. No database changes or SQL migrations are needed.
2. **Backward-Compatible Registrations**: When a new block type is introduced, it is added to the central `BlockRegistry`.
3. **Graceful Fallbacks**: If an older client application encounters an unrecognized block type, the rendering engine falls back to a clean text parser or omits the block entirely, preventing application crashes.
4. **On-the-Fly Schema Migrations**: When updating a block's structure (e.g., converting a single-image block to a responsive-image block), the block's `migration_strategy` updates the structure dynamically as the data is read:
   - Older records remain stored at `version: 1`.
   - When the data is fetched, the serializer updates the payload to `version: 2` on the fly, avoiding expensive offline batch updates.

---

## 15. Architectural Comparison

To evaluate this design, we compare the proposed **Block-Based CMS Architecture** against traditional content structures.

### Comprehensive Comparison Matrix

| Feature / Metric | Traditional Rich Text (Legacy) | Section + Media Architecture | Relational CMS Architecture | **Block-Based JSONB CMS (Proposed)** |
| :--- | :--- | :--- | :--- | :--- |
| **Read Performance** | Fast (single field read) | Moderate (requires Joins) | Slow (multiple table joins) | **Extremely Fast** (single row fetch, indexed JSONB) |
| **Layout Flexibility** | Very Low (HTML editor limits) | Low (predefined sections) | Moderate (relational structures) | **Infinite** (flexible block order) |
| **API Integration** | Poor (requires parsing HTML) | Moderate (structured list) | Good (relational serialization) | **Excellent** (native JSON format) |
| **Media Association** | Hardcoded HTML source URLs | Medium (associated with sections) | Strict (Foreign Keys) | **Atomic & Decoupled** (expanded via media library IDs) |
| **Schema Evolution** | Easy (requires no schema) | Difficult (database migrations) | Extremely Difficult (complex migrations) | **Seamless** (schema-less JSONB, registry-driven) |
| **Localization (i18n)** | Easy (per-field translation) | Complex (multi-table translations) | Very Complex (nested relational translation) | **Native & Clean** (stored in translation tables) |
| **SEO & Semantic HTML** | Poor (inline visual styles) | Moderate (structured fields) | Good (structured fields) | **Perfect** (automatic structured data generation) |
| **Visual Editing Experience**| Poor (CKEditor text areas) | Moderate (nested inline forms) | Poor (disconnected forms) | **Excellent** (drag-and-drop block layouts) |

---

## 16. Summary & Recommendations

Based on the requirements of our enterprise platform, the **Block-Based JSONB Content Engine** is the recommended architecture for the CMS.

### Key Architectural Decisions

1. **Implement on model `ArticleTranslation`**: Add the `content_blocks` column using PostgreSQL's native `JSONField` type to support translation-specific block layouts naturally.
2. **Build a central `BlockRegistry`**: Manage block configurations in a single registry, avoiding complex conditional logic.
3. **Use the `ArticleMedia` intermediate table**: Track media usage within JSON blocks to prevent referenced files from being deleted accidentally.
4. **Implement edge caching**: Cache fully expanded JSON blocks at the CDN level to deliver rapid page load speeds worldwide.

This specification provides the technical blueprint for the development team to build a highly scalable, flexible, and future-proof content engine.
