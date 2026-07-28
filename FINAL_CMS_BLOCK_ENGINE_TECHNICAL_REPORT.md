# CMS Generic Block Engine: Enterprise Technical Whitepaper
## Comprehensive Architectural, Data Model, and Pipeline Specifications

---

## 1. Architecture Overview

Our Next-Generation Content Management System (CMS) replaces traditional rigid "section-oriented" and single-field HTML documents with a highly decoupled, modular **Generic Block Engine**. In this paradigm, an article is no longer treated as a monolithic document with metadata overlays, but as a structured, localized stream of atomic, self-contained **Content Blocks**.

The system leverages a decoupled, headless-ready architecture. The CMS is split into discrete logical layers, ensuring absolute separation of concerns between storage, validation, serialization, and presentation.

### Conceptual Layer Hierarchy

```
       +-------------------------------------------------------------+
       |                  1. API & Presentation Layer                |
       |       - REST Endpoints (Django REST Framework Views)        |
       |       - Inbound request parsing and content negotiation     |
       +-------------------------------------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                  2. Serialization Layer                     |
       |       - ArticleList & ArticleDetail Serializers             |
       |       - Dynamic field filtering and Jalali date conversions |
       |       - Generic Media Expansion and enrichment injection     |
       +-------------------------------------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |              3. Validation & Sanitization Layer             |
       |       - Standard JSON Schema draft-07 validators            |
       |       - Heading Hierarchy and duplicate ID/Order checks     |
       |       - BeautifulSoup-based XSS mitigation engines          |
       +-------------------------------------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                    4. Domain Service Layer                  |
       |       - Core business logic (reading time calculators)      |
       |       - Media reference synchronization and cleanup triggers|
       +-------------------------------------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                    5. Data Persistence Layer                |
       |       - PostgreSQL Native JSONB Columns                     |
       |       - Django ORM models and custom managers               |
       +-------------------------------------------------------------+
```

### Logical Hierarchy: Article to Block

Every Article exists as a core meta-object containing status, author, and scheduling metadata. This connects directly to language-specific translations (`ArticleTranslation`), which contain the raw sequence of blocks stored in a single binary JSON column (`content_blocks`).

```
+------------------------------------------------------------+
|                    Core Article Model                      |
| (Author, Category, Cover, Status, Dates, Visibility, etc.) |
+------------------------------------------------------------+
                             |
                             | 1 : N (Translations)
                             v
+------------------------------------------------------------+
|                 ArticleTranslation Model                   |
|     (language_code: "fa"/"en", Title, Excerpt, SEO, etc.)  |
+------------------------------------------------------------+
                             |
                             | 1 : 1 (JSONB Column)
                             v
+------------------------------------------------------------+
|            JSON content_blocks Array (Ordered)             |
|   +----------------------------------------------------+   |
|   | Block [0]: HeadingBlock (level: 2, order: 1)       |   |
|   +----------------------------------------------------+   |
|   | Block [1]: ParagraphBlock (text: "...", order: 2)   |   |
|   +----------------------------------------------------+   |
|   | Block [2]: ImageBlock (media_id: 104, order: 3)    |   |
|   +----------------------------------------------------+   |
+------------------------------------------------------------+
```

---

## 2. Article Data Model

The database represents articles using two primary entities: **`Article`** (defining the abstract entity metadata) and **`ArticleTranslation`** (handling localized representations, titles, and content). This 1:N relational structure guarantees that the CMS is natively localized from the ground up.

### Article Metadata
The core `Article` table defines language-agnostic metadata, state constraints, and core relational links:
* **Identification & Routing**: Unique primary keys, `canonical_url` definitions, and unique indexes.
* **Publishing Status**: `status` field utilizing state machine restrictions (`draft`, `review`, `scheduled`, `published`, `archived`) and `visibility` scoping (`public`, `private`, `unlisted`).
* **Temporal Records**: `published_at` and `scheduled_at` timestamps for absolute tracking and automatic celery scheduling.
* **Aggregations**: Denormalized `views_count` for rapid read-time analytics.

### Translation Model
Localized article content is stored in `ArticleTranslation` which references the parent `Article` via a foreign key. The translation stores localization-specific fields:
* **Localization Attributes**: `language_code` and unique composite indexes `(article, language_code)` and `(slug, language_code)`.
* **Standard SEO Overrides**: Localized `seo_title` and `seo_description`.
* **Briefing Elements**: Localized `title`, `excerpt`, and `short_description`.
* **Primary Structured Core**: The native Django/PostgreSQL `JSONField` called **`content_blocks`** which maps directly to a `JSONB` database type.
* **Calculated Values**: `reading_time_sec` determined dynamically during persistence based on word counts.

### Entity Relationship Diagram (ERD)

```
  +-----------------------+                    +------------------------------+
  |        Category       |                    |         AuthorProfile        |
  +-----------------------+                    +------------------------------+
  | id (PK)               |                    | user_id (PK, FK)             |
  | name (CharField)      |                    | display_name (CharField)     |
  | slug (SlugField)      |                    | bio (TextField)              |
  | parent_id (FK, self)  |                    | avatar_id (FK -> Media)      |
  +-----------------------+                    +------------------------------+
              |                                               |
              | 1                                             | 1
              |                                               |
              | N                                             | N
         +---------+------------------------------------------+---------+
         |                                                              |
         v                                                              v
  +-----------------------------------------------------------------------------+
  |                                   Article                                   |
  +-----------------------------------------------------------------------------+
  | id (PK)                                                                     |
  | status (CharField: draft, scheduled, published, etc.)                       |
  | visibility (CharField: public, private, unlisted)                             |
  | is_hot (BooleanField)                                                       |
  | canonical_url (URLField)                                                    |
  | views_count (PositiveIntegerField)                                          |
  | published_at (DateTimeField, Null)                                          |
  | scheduled_at (DateTimeField, Null)                                          |
  | author_id (FK -> AuthorProfile)                                             |
  | category_id (FK -> Category, Null)                                          |
  | series_id (FK -> Series, Null)                                              |
  | cover_image_id (FK -> Media, Null)                                          |
  | og_image_id (FK -> Media, Null)                                             |
  +-----------------------------------------------------------------------------+
         |                                                       |
         | 1                                                     | 1
         |                                                       |
         | N (Translations)                                      | N (Attachments)
         v                                                       v
  +------------------------------------+               +-------------------+
  |         ArticleTranslation         |               |    ArticleMedia   |
  +------------------------------------+               +-------------------+
  | id (PK)                            |               | id (PK)           |
  | article_id (FK -> Article)         |               | article_id (FK)   |
  | language_code (CharField: fa, en) |               | media_id (FK)     |
  | slug (SlugField)                   |               | attachment_type   |
  | title (CharField)                  |               |   (cover, og,     |
  | excerpt (TextField)                |               |    in-content)    |
  | short_description (TextField)      |               +-------------------+
  | content (CKEditor5Field, Legacy)   |
  | content_blocks (JSONField, JSONB)  |
  | reading_time_sec (IntegerField)    |
  | seo_title (CharField)              |
  | seo_description (TextField)        |
  +------------------------------------+
```

---

## 3. Generic Block Engine

### What a Block Is
A Block is an independent, schema-validated dictionary stored inside an ordered array within the `content_blocks` column. Each block encapsulates a single conceptual content type (such as a paragraph, image, quote, or video) containing all the semantic properties, styling flags, and auditing metadata required for rendering and lifecycle execution.

### Independence and Removal of Sections
Historically, CMS designs grouped paragraphs and media together inside pre-structured template areas called "Sections". This layout coupling became a technical bottleneck when rendering on non-web channels (such as iOS/Android Native UI, AMP, RSS, or watchOS).

By transitioning to an **Atomic Independence** pattern:
1. **Sections were completely removed.**
2. Text, Images, and Videos are flattened into independent nodes.
3. Media layout configurations (e.g. alignment, width) are declared strictly inside the block’s metadata or configuration settings rather than being bound to neighboring text elements.

### Block Ordering Logic
The ordering of blocks is managed sequentially. Every block is required to submit an `order` field (an integer). During the save lifecycle, the service layer executes a sorting operation and runs a **Normalization Indexer**. This normalizes the ordering indices into consecutive integers starting from `1` (e.g. blocks submitted with orders `12`, `45`, `99` are re-indexed to `1`, `2`, `3`). This guarantees that block sequences are resilient to drag-and-drop conflicts and omissions.

### Generic Block Schema (Standard Block Envelope)
Every block is structured inside a highly strict container envelope schema to ensure uniform parsing across the system:

```json
{
  "id": "string (Unique identifier, minimum 1 char)",
  "type": "string (Must be a registered block type key)",
  "version": "integer (Supported version matching registry, minimum 1)",
  "order": "integer (Positional rank for rendering)",
  "settings": "object (Optional visual presentation styling attributes)",
  "metadata": "object (Optional auditing, indexing, or authoring data)",
  "data": "object (Required payload dictionary containing block-specific properties)"
}
```

#### Field Specifications:
* **`id`**: Unique block identifier (typically a UUID or unique K-sortable slug) used for DOM reconciliation (e.g. React keying) and real-time collaboration.
* **`type`**: Used by serializers and clients to route block-specific fields to their respective schemas or React/Vue rendering components.
* **`version`**: Tracked scheme version ensuring backward compatibility as individual block structures evolve.
* **`order`**: Numeric sequencing flag normalized sequentially on save.
* **`settings`**: Separates display properties (such as text alignments, padding, margins, or background color codes) from semantic data, allowing headless channels to ignore visual presets entirely.
* **`metadata`**: Houses non-semantic information like timestamps or author tags.
* **`data`**: Encapsulates block-specific fields, isolated from structural container attributes.

---

## 4. Supported Block Types

The engine supports 15 native, built-in block types. Each block class is managed by the registry, defining explicit structural schemas, empty-block constraints, and data validations:

### 1. `heading`
* **Purpose**: Page outlines and section subdivisions.
* **Stored Data Structure**:
  ```json
  { "level": 2, "text": "معماری سیستم", "anchor_id": "arch-section" }
  ```
* **Validation Rules**: `level` must be an integer between `1` and `6`. `text` is required.
* **Rendering Responsibility**: Outputs standard semantic tags (`<h2>` to `<h6>`) with `id` bindings matching `anchor_id`.

### 2. `paragraph`
* **Purpose**: Rich text body paragraphs.
* **Stored Data Structure**:
  ```json
  { "text": "این یک بند متنی شامل <p>محتوای غنی</p> است." }
  ```
* **Validation Rules**: `text` is required. Empty paragraphs are rejected.
* **Rendering Responsibility**: Renders semantic `<p>` blocks supporting sanitized inline HTML.

### 3. `image`
* **Purpose**: Standard inline illustrations.
* **Stored Data Structure**:
  ```json
  { "media_id": 42, "caption": "شکل ۱: نمودار توزیع", "alt": "نمودار معماری", "lazy": true }
  ```
* **Validation Rules**: `media_id` is required, must exist in the database, and must be active.
* **Rendering Responsibility**: Produces an `<figure>` envelope containing `<img src="..." loading="lazy" alt="..." />` and a `<figcaption>`.

### 4. `gallery`
* **Purpose**: Multi-image sliders or responsive grids.
* **Stored Data Structure**:
  ```json
  { "media_ids": [42, 43], "layout": "grid", "aspect_ratio": "16:9" }
  ```
* **Validation Rules**: `media_ids` must be an array of active media IDs. `layout` must be one of `["grid", "slider"]`.
* **Rendering Responsibility**: Renders CSS grid components or swiper-driven carousels.

### 5. `quote`
* **Purpose**: Displaying editorial highlights, pull quotes, or historical citations.
* **Stored Data Structure**:
  ```json
  { "text": "سادگی نهایت پیچیدگی است.", "citation": "لئوناردو داوینچی" }
  ```
* **Validation Rules**: `text` is required.
* **Rendering Responsibility**: Outputs custom `<blockquote cite="...">` and nested `<cite>` components.

### 6. `table`
* **Purpose**: Presenting tabular data.
* **Stored Data Structure**:
  ```json
  { "headers": ["نام", "پورت"], "rows": [["Redis", "6379"], ["Postgres", "5432"]] }
  ```
* **Validation Rules**: `headers` (1D array of strings) and `rows` (2D array of strings) are required.
* **Rendering Responsibility**: Renders responsive styled tables (`<table>`, `<thead>`, `<tbody>`).

### 7. `code`
* **Purpose**: Syntax-highlighted code fragments.
* **Stored Data Structure**:
  ```json
  { "code": "print('Hello World')", "language": "python", "show_line_numbers": true }
  ```
* **Validation Rules**: `code` is required.
* **Rendering Responsibility**: Renders pre-styled wrappers (`<pre><code class="language-python">...`) optimized for tools like Prism.js.

### 8. `divider`
* **Purpose**: Visual section separations.
* **Stored Data Structure**:
  ```json
  { "style": "solid" }
  ```
* **Validation Rules**: `style` must be one of `["solid", "dashed", "dots"]`.
* **Rendering Responsibility**: Outputs `<hr class="divider-solid" />`.

### 9. `video`
* **Purpose**: Multimedia playback support.
* **Stored Data Structure**:
  ```json
  { "media_id": 105, "provider": "local", "external_url": "", "autoplay": false, "controls": true }
  ```
* **Validation Rules**: `provider` must be `["local", "youtube", "vimeo"]`. If local, `media_id` is validated.
* **Rendering Responsibility**: Renders native HTML5 `<video>` elements or interactive YouTube/Vimeo `<iframe>` players.

### 10. `embed`
* **Purpose**: Social media widgets or standard sub-document iframes.
* **Stored Data Structure**:
  ```json
  { "url": "https://twitter.com/post/1", "embed_type": "twitter", "width": 600, "height": 400 }
  ```
* **Validation Rules**: `url` is required. `embed_type` must be `["twitter", "instagram", "iframe"]`.
* **Rendering Responsibility**: Loads standard third-party script embed widgets or responsive responsive layout iframes.

### 11. `button`
* **Purpose**: Inline CTA (Call to Action) link banners.
* **Stored Data Structure**:
  ```json
  { "label": "دانلود مستندات", "url": "/docs", "target": "_blank", "style_preset": "primary" }
  ```
* **Validation Rules**: `label` and `url` are required. `target` must be one of `["_blank", "_self"]`.
* **Rendering Responsibility**: Outputs `<a href="/docs" target="_blank" class="btn btn-primary">...`.

### 12. `accordion`
* **Purpose**: Content accordions.
* **Stored Data Structure**:
  ```json
  { "items": [{ "title": "ویژگی اول", "content": "توضیح کامل در مورد ویژگی اول" }] }
  ```
* **Validation Rules**: `items` is required, containing an array of objects with `title` and `content`.
* **Rendering Responsibility**: Outputs interactive dropdown disclosures (`<details>`, `<summary>`).

### 13. `faq`
* **Purpose**: Search-optimized frequently asked questions.
* **Stored Data Structure**:
  ```json
  { "questions": [{ "q": "چگونه شروع کنیم؟", "a": "کافی است ثبت نام کنید." }] }
  ```
* **Validation Rules**: `questions` array of objects mapping `q` and `a` properties is required.
* **Rendering Responsibility**: Generates visually styled lists accompanied by Google Rich Snippet JSON-LD structured data outputs.

### 14. `timeline`
* **Purpose**: Historic roadmaps or visual chronological steps.
* **Stored Data Structure**:
  ```json
  { "events": [{ "date": "۱۴۰۵/۰۱", "title": "راه‌اندازی فاز ۱", "description": "بهره برداری" }] }
  ```
* **Validation Rules**: `events` array of date/title objects is required.
* **Rendering Responsibility**: Outputs responsive chronological CSS timelines.

### 15. `related_articles`
* **Purpose**: Multi-article recommendation sections.
* **Stored Data Structure**:
  ```json
  { "article_ids": [12, 15, 20] }
  ```
* **Validation Rules**: `article_ids` array of integers is required.
* **Rendering Responsibility**: Renders dynamic preview cards of the target articles.

---

## 5. Block Registry

To keep the platform highly extensible and avoid fragile nested conditional loops (`if type == 'image'`), the system implements a strict, object-oriented **Block Registry Engine** in `posts/blocks.py`.

```
                        +----------------------+
                        |    BlockRegistry     | <--- Register dynamically via register()
                        +----------------------+
                                   |
              +--------------------+--------------------+
              |                                         |
              v                                         v
   +--------------------+                    +--------------------+
   |    HeadingBlock    |                    |   ParagraphBlock   |
   +--------------------+                    +--------------------+
   | - get_data_schema()|                    | - get_data_schema()|
   | - validate()       |                    | - validate()       |
   | - is_empty()       |                    | - is_empty()       |
   | - expand_media()   |                    | - expand_media()   |
   +--------------------+                    +--------------------+
```

### Core Architecture Components

#### 1. Registration & Discovery
The central `BlockRegistry` maintains a map (`self._registry`) of block instances indexed by their type string on initialization. Adding a new block type only requires subclassing `BaseBlock` and registering it with the global singleton. No modifications to serialization pipelines, schemas, or views are required.

#### 2. Envelope & Schema Validation
When a block payload is submitted to the API, the serializer calls `block_registry.validate_block_payload(block_payload)`:
* It verifies the payload is a dictionary and contains a registered `type` key.
* It checks that the block version does not exceed the supported version (`handler.schema_version`).
* It loads the standard envelope schema and joins the block-specific schema returned by `get_data_schema()`.
* It runs the validation routine using the `jsonschema` library.

#### 3. Polymorphic Services
The registry delegates polymorphic operations to the respective block instances, ensuring clean logical decoupling:
* **`get_referenced_media_ids(data)`**: Declares which internal data attributes refer to database Media assets.
* **`is_empty(data)`**: Specifies logic to detect and block empty inputs (such as paragraphs containing only white spaces or HTML tags like `   <p> </p>  `).
* **`expand_media_references(data, media_map)`**: Directs how to inject rich media representations back into the JSON structure before outputting.

---

## 6. Article Lifecycle

The lifecycle of an article ensures complete data integrity from visual authoring to final delivery.

```
 [ Author / Admin UI ]
          |
          v
 [ 1. API Endpoint / Request Ingestion ]
          |
          v
 [ 2. Parser / Hybrid Media Field Processing ]  ---> Auto-uploads multipart inline images
          |
          v
 [ 3. Registry envelope & jsonschema check ]   ---> Validates block container structures
          |
          v
 [ 4. Multi-tiered Business Checks ]            ---> Checks duplicate IDs, orders, empty blocks
          |
          v
 [ 5. Heading Hierarchy Validation ]           ---> Ensures visual outline integrity
          |
          v
 [ 6. BeautifulSoup XSS Sanitizer ]            ---> Strips malicious script/onload strings
          |
          v
 [ 7. Reorder Normalizer ]                     ---> Sequences orders from 1 to N
          |
          v
 [ 8. Media Sync Engine ]                      ---> Intercepts & ties Media to ArticleMedia
          |
          v
 [ 9. DB Persistence ]                         ---> Commits JSONB content arrays to DB
          |
          v
 [ 10. Serializer / Media Expander ]           ---> Passes data to client, expanding Media IDs
          |
          v
 [ Client Native / Headless Render ]
```

### Detailed Lifecycle Stages

1. **Author/Admin Interaction**: Authors write content via visual block editors (such as Alpine.js blocks in Django Admin) or structured REST API calls.
2. **Inbound Serialization**: DRF parses the JSON stream. The customized `HybridMediaField` intercepts cover or open-graph images, supporting either existing media IDs or multipart file uploads.
3. **Registry structural validation**: The block engine validates each block's structural constraints using jsonschema.
4. **Business Validation Rules**: The validation pipeline flags duplicate IDs, duplicate orders, or empty blocks.
5. **Heading Outline Check**: The pipeline validates the semantic ordering of headings, ensuring correct heading levels.
6. **XSS Sanitization**: Text block payloads are sanitized using BeautifulSoup, preventing malicious script injections.
7. **Positional Indexing**: The block list is sorted by `order` and normalized sequentially into consecutive integers starting from `1`.
8. **Media Synchronization**: The system parses the validated block list, extracts all referenced `media_id` identifiers, and syncs them with the `ArticleMedia` relationship table to prevent media files from being deleted accidentally.
9. **Persistence**: The transaction is saved to the database, writing the validated JSON array directly to the PostgreSQL `JSONB` column.
10. **Delivery & Expansion**: On retrieval (GET requests), the detail serializer identifies all `media_id` properties across the block stream, runs a single batched query to fetch the media assets, and embeds the media representations directly into the JSON response.

---

## 7. Validation Pipeline

The system enforces a multi-tiered validation pipeline before committing any content updates:

```
[ Incoming Block Array ]
          |
          +---> [ Layer 1: Payload & Block Count Limits ] (Size < 5MB, Blocks <= 200)
          |
          +---> [ Layer 2: Envelope JSON Schema ] (Verifies ID, Type, Version, Order, Data)
          |
          +---> [ Layer 3: Registry Schema Validation ] (Executes jsonschema checks per type)
          |
          +---> [ Layer 4: Business Integrity & Duplicates ] (Flags Duplicate IDs and Orders)
          |
          +---> [ Layer 5: Media Reference Validation ] (Verifies that media exists and is active)
          |
          +---> [ Layer 6: Content Integrity Verification ] (Filters empty paragraphs or images)
          |
          +---> [ Layer 7: Heading Hierarchy Check ] (Ensures H3 is preceded by H2, etc.)
          v
[ Passed to Sanitizer & Normalization ]
```

### Validation Layers: Detailed Specification

* **Payload & Size Constraints**: POST payloads are limited to 5MB, and articles are restricted to a maximum of 200 blocks. This protects the database from ingestion inflation and prevents Denial of Service (DoS) attacks.
* **Envelope JSON Schema**: Verifies that every block in the collection contains required properties: `id`, `type`, `version`, `order`, and `data`.
* **Registry Schema Validation**: Integrates custom JSON validation schemas for each block type, raising localized errors with exact block positions (e.g., `content_blocks[2].data.media_id`).
* **Business Integrity Checks**: Prevents client-side conflicts by ensuring that every block `id` and `order` is unique.
* **Media Reference Validation**: Checks referenced media library IDs in bulk, raising specific localized errors if any media file is missing or inactive.
* **Content Integrity Verification**: Detects and rejects empty blocks (such as paragraphs containing only empty spaces or HTML containers like `   <p> </p>  `).
* **Heading Hierarchy Check**: Enforces semantic and accessible structure. Heading levels must not skip levels (e.g., jumping from `H1` to `H3` without an intermediate `H2` is blocked).

---

## 8. Media Architecture

Under the clean architecture model, **media is represented strictly as independent blocks or explicit entity properties**. The system prevents "orphan" media files and protects active attachments from being deleted.

### Core Media Flow

```
[ Visual Article Block Layout ]
  - ImageBlock (media_id: 104)
  - GalleryBlock (media_ids: [105, 106])
  - VideoBlock (media_id: 107)
          |
          | Save Trigger
          v
+--------------------------------------------------------+
|               Service: sync_article_media              |
| 1. Extracts all referenced media_ids                   |
| 2. Identifies current ArticleMedia attachments         |
| 3. Computes diff sets to add or remove                 |
+--------------------------------------------------------+
          |
          +---> Adds missing relations to ArticleMedia (type: "in-content")
          |
          +---> Deletes stale relations (type: "in-content")
          v
[ PostgreSQL Relational Database State ]
  - ArticleMedia (article: 1, media: 104, type: "in-content")
  - ArticleMedia (article: 1, media: 105, type: "in-content")
  - ArticleMedia (article: 1, media: 106, type: "in-content")
  - ArticleMedia (article: 1, media: 107, type: "in-content")
```

### Media Synchronization and Protection
* **Reference Extraction**: The service layer uses the polymorphic registry to extract referenced media IDs from the blocks.
* **Relationship Synchronization**: The `sync_article_media` service syncs media references with the intermediate `ArticleMedia` table, mapping attachments to their usage types (`cover`, `og-image`, or `in-content`).
* **Cleanup and Orphan Prevention**: When an article is updated, obsolete relationships in `ArticleMedia` are removed. The system prevents files with active attachments in `ArticleMedia` from being deleted from the media library, preventing broken links.

---

## 9. Serializer Architecture

Serialization is designed to be efficient and prevent common database performance bottlenecks, such as the N+1 query problem.

### The Batch Expansion Pipeline

```
[ Retreive Article request ]
              |
              v
[ Read Raw Article JSONB List from DB ]
  - Block 0: heading  -> data: { "text": "..." }
  - Block 1: image    -> data: { "media_id": 42 }
  - Block 2: gallery  -> data: { "media_ids": [43, 44] }
              |
              v
[ Step 1: Collect Media IDs in one pass ] ---> Collected Set: {42, 43, 44}
              |
              v
[ Step 2: Batch query Media DB ] -----------> Query: Media.objects.filter(id__in={42,43,44})
              |
              v
[ Step 3: Serialize & Map Media ] ----------> Create Media Map: { 42: {...}, 43: {...}, 44: {...} }
              |
              v
[ Step 4: Inject Media objects ] ----------> Mutate block payloads on the fly
              |
              v
[ Output Consolidated REST API Response ]
```

### Serializer Optimization Details
* **Batched Media Expansion**: The detail serializer collects all media IDs across the block list and fetches them in a single database query.
* **Inline File Interceptor**: During updates, the serializer automatically matches inline images in the HTML body to files uploaded in the multipart request, replacing placeholders with real media URLs.
* **On-the-Fly Normalization**: Convert raw dates into Jalali (Persian) formats, transform legacy HTML fields into Markdown dynamically, and inject reading times.

---

## 10. API Output

### Consolidated Response Spec (GET `/api/v1/articles/{slug}/`)

```json
{
  "status": "success",
  "data": {
    "id": 101,
    "slug": "معماری-توزیع-شده",
    "title": "معماری توزیع شده با جنگو",
    "excerpt": "راهنمای جامع پیرامون توسعه میکروسرویس‌ها با بسترهای ابری.",
    "short_description": "بخش ابتدایی شامل بررسی مفاهیم سیستم توزیع‌شده.",
    "reading_time_sec": 120,
    "status": "published",
    "is_hot": true,
    "published_at": "1405/05/07 14:30:00",
    "author": {
      "display_name": "نیما راد",
      "avatar": {
        "id": 1,
        "url": "/media/avatars/nima.png",
        "type": "image",
        "mime": "image/png"
      }
    },
    "category": "برنامه‌نویسی سیستم",
    "cover_image": {
      "id": 42,
      "url": "/media/covers/dist-arch.jpg",
      "type": "image",
      "mime": "image/jpeg"
    },
    "views_count": 1250,
    "likes_count": 85,
    "comments_count": 12,
    "tags": [
      {
        "id": 5,
        "slug": "django",
        "name": "جنگو"
      }
    ],
    "content_blocks": [
      {
        "id": "blk_1",
        "type": "heading",
        "version": 1,
        "order": 1,
        "settings": {
          "text_alignment": "right"
        },
        "data": {
          "level": 2,
          "text": "معماری توزیع شده چیست؟",
          "anchor_id": "intro"
        }
      },
      {
        "id": "blk_2",
        "type": "paragraph",
        "version": 1,
        "order": 2,
        "settings": {},
        "data": {
          "text": "سیستم توزیع‌شده به مجموعه‌ای از سیستم‌های مستقل گفته می‌شود که به عنوان یک سیستم واحد به نظر می‌رسند."
        }
      },
      {
        "id": "blk_3",
        "type": "image",
        "version": 1,
        "order": 3,
        "settings": {
          "display_width": "full_width"
        },
        "data": {
          "media_id": 42,
          "caption": "شکل ۱: نمودار توزیع",
          "alt": "نمودار معماری توزیع شده",
          "lazy": true,
          "media": {
            "id": 42,
            "url": "/media/covers/dist-arch.jpg",
            "type": "image",
            "mime": "image/jpeg"
          }
        }
      }
    ],
    "canonical_url": "https://example.com/canonical-url",
    "series": null,
    "seo_title": "آموزش کامل سیستم‌های توزیع شده",
    "seo_description": "میکروسرویس و توزیع سیستم با Django",
    "og_image": null,
    "media_attachments": [
      {
        "id": 501,
        "media_id": 42,
        "attachment_type": "in-content"
      }
    ],
    "related_articles": []
  },
  "messagesList": []
}
```

#### Consumption by Frontends:
* **Dynamic Router**: The frontend loops over the `content_blocks` list, rendering each block using its matching UI component.
* **Interactivity**: Settings and visual metadata are applied directly as component properties.
* **SEO & Crawlability**: Dynamic metadata fields (SEO title/description) are rendered during SSR to ensure optimal crawlability.

---

## 11. Reading Time

The reading time of localized translations is calculated dynamically using a word-count algorithm.

* **HTML Processing**: Reading time is calculated strictly from text-based content. The system parses content fields with BeautifulSoup to strip HTML tags and extract raw text.
* **Contributions**: Text-based blocks (`heading`, `paragraph`, `quote`, `table`, `accordion`, `faq`, `timeline`) contribute to the word count.
* **Excluded Blocks**: Non-text blocks (`image`, `gallery`, `video`, `divider`, `embed`, `button`, `related_articles`) are ignored.
* **Calculation Speed**: Calculated using an average reading speed of 200 words per minute. The calculated time is saved to the database in seconds (`reading_time_sec`), ensuring rapid read queries.

---

## 12. Django Admin

The Django Admin panel has been updated to support block-based content editing directly within the admin interface.

* **JSON State Sync**: Administrators can edit JSON block collections using a visual editor. The visual layout synchronizes edits with the underlying hidden JSON text field in real-time.
* **Validation & Security**: Form submissions are validated against the same JSON Schema and sanitization pipelines used by the public REST API, preventing XSS injections and structure errors.
* **Visual Workflows**: Administrators can drag, re-order, duplicate, or delete blocks, and select media library assets directly within the visual interface.

---

## 13. Database Changes

* **New Fields**: Added `content_blocks` (PostgreSQL `JSONB` column) and `reading_time_sec` (integer) to the `ArticleTranslation` table.
* **Legacy Fields**: The legacy rich-text `content` field remains in place for backward compatibility, allowing older articles to continue working without data loss.
* **Decoupled Architecture**: Removed complex relationship joins. Articles and blocks are decoupled, storing visual layouts directly within the JSON structures.
* **Migration Strategy**: Existing articles are migrated gracefully. The system reads from `content` if `content_blocks` is empty, ensuring a seamless transition.

---

## 14. Performance

Storing content blocks within PostgreSQL JSONB columns provides excellent performance at scale.

* **No Costly Joins**: Avoids expensive multi-table joins. Block collections are loaded in a single database read operation.
* **GIN Indexes**: Uses a Generalized Inverted Index (GIN) on the `content_blocks` column, allowing PostgreSQL to run complex query structures in milliseconds.
* **Caching Strategy**: API detail responses are cached in Redis, reducing backend database load and delivering fast page load speeds.
* **Batch Expansion**: Collects and fetches referenced media in a single database query, preventing N+1 performance issues.

---

## 15. Security

The CMS protects against common security vulnerabilities using a multi-tiered security model:

* **XSS (Cross-Site Scripting) Mitigation**: Strips harmful HTML tags (such as `<script>`, `<embed>`, or `<iframe>`) from text fields using BeautifulSoup.
* **Content Restrictions**: Enforces strict limit checks on request payload sizes (5MB) and block counts (200) to protect against buffer overflow and DoS attacks.
* **Relational Verification**: Validates all referenced media IDs to verify that assets are active and exist before saving, preventing reference manipulation.

---

## 16. Testing

The block engine is backed by a comprehensive automated test suite.

* **Unit Tests**: Verifies JSON schema validation, heading hierarchy constraints, and HTML sanitization across all block types.
* **Integration Tests**: Validates serialization flows, automatic media synchronization, and reading time calculations.
* **Test Automation**: Run the automated test suite using the following command:
  ```bash
  STATIC_API_KEY=your-secure-static-api-key uv run python manage.py test
  ```

---

## 17. Comparison

| Metric | Traditional Rich Text CMS | Proposed Generic Block Engine |
| :--- | :--- | :--- |
| **API Response** | Raw HTML (requires parsing) | Structured JSON (easy to consume) |
| **Omichannel Compatibility** | Low (web-only markup) | High (headless ready) |
| **Media Safety** | High risk of broken links | Secure (tracked using relational links) |
| **Outlines (SEO)** | Complex regex outlines | Clean sequential headings |
| **Validation** | Basic HTML sanitization | Schema validation & business rules |

---

## 18. Final Architecture Assessment

### Enterprise Readiness Assessment
The backend CMS is fully **Enterprise-Ready**. It handles structured publishing, localization, media safety, and headless integrations in a reliable and secure package.

### Achieved Architectural Goals
* **Atomic Independence**: Successfully decoupled media and text, removing legacy "section" blocks.
* **Polymorphic Extensibility**: Added support for new block types via the central block registry.
* **Robust Security**: Enforced BeautifulSoup sanitization and schema validations across all block structures.

### Limitations & Recommendations
* **No Inline Block Changes**: Block schema updates require manual on-the-fly upgrades or offline data scripts.
* **Dynamic Recommendations**: Custom block types (like `related_articles`) are resolved on retrieval, adding database processing overhead under heavy loads.
* **Future Recommendation**: Implement offline translation pipelines and block caching in Redis to further optimize scale.
