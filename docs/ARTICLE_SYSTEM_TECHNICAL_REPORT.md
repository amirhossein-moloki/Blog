# Final Technical Report — Article Architecture: Generic Block Engine

Welcome to the comprehensive technical report for the next-generation, Enterprise-grade **Block-Based Article System**. This document has been prepared for backend developers joining the engineering team to provide a deep, production-level understanding of how an Article is structured, validated, processed, stored, and served in the current block-based architecture.

This report focuses exclusively on the Article subsystem, its architectural transition to the Generic Block Engine, and its complete lifecycle from authoring to frontend rendering.

---

## 1. Article Overview

An **Article** in our system represents the core unit of editorial content. It houses not only the semantic content blocks that readers consume but also the rich metadata, categorization, search signals, localized variants, SEO attributes, and media relationships that power our omnichannel delivery.

### Responsibilities of the Article System
The Article system is built to achieve several key engineering objectives:
1. **Multi-Platform Consistency**: Serving the exact same content natively to Headless Web Apps (Next.js), Mobile Apps (iOS/Android), and Syndication channels (RSS/AMP).
2. **Dynamic Composition**: Empowering editors to construct rich visual layouts through atomic, decoupled content elements.
3. **Data Integrity**: Enforcing absolute database and relational validation across JSON storage boundaries.
4. **Localization (i18n)**: Decoupling core article metadata (status, author, classification) from localized text fields and layouts.

### How It Differs From the Previous Implementation
In the legacy architecture, articles were bound to a "Document-oriented" structure. Content was composed either in a single massive HTML string via a rich-text editor (CKEditor) or bound to highly restrictive, hardcoded database tables (e.g., "Sections" with fixed images and text).

This legacy approach introduced significant technical debt:
- **Coupled Media and Text**: Media elements were tightly coupled with text layout parameters (such as `media_position` flags). This made it nearly impossible to repurpose images or format text on non-web platforms.
- **Brittle Schema Migrations**: Adding a new design element or content block required running expensive and risky database migrations to add columns or child tables.
- **Poor Multi-Platform API Consumption**: Mobile applications had to parse and strip complex HTML tags, inline styles, and proprietary classes to render a native layout.
- **Relational Overhead**: Querying nested sub-components required multiple SQL joins, slowing down read performance under heavy traffic.

With the migration to the **Generic Block Engine**, the legacy rich-text CKEditor and Section tables have been replaced. Content is now modeled as an array of structured, polymorphic **JSON Blocks** stored in a native PostgreSQL `JSONB` column. The backend serves raw, structured JSON to client applications, enabling true headless publishing while retaining absolute clean architecture separations.

---

## 2. Internal Article Structure

The Article architecture is built on a highly normalized, multi-tiered database structure that cleanly separates global metadata from localized content blocks.

### Component Breakdown

* **Article**: The root model representing the identity of the publication. It holds non-translatable global attributes: status, visibility, publication dates, author relationships, categories, series, and cover/OG images.
* **ArticleTranslation**: The localized translation model linked 1-to-N with the Article. It stores language-specific attributes (`language_code`, `slug`, `title`, `excerpt`, `short_description`) and the central `content_blocks` JSONB column.
* **Metadata**: Fields storing analytical and administrative data such as `views_count`, `likes_count`, and `comments_count`.
* **SEO**: Strategic search engine signals (`seo_title`, `seo_description`, `canonical_url`) residing in the localized and global models.
* **Categories**: The hierarchical `Category` model, allowing nested parent-child taxonomies for article organization.
* **Cover Media**: Foreign key references to the central `Media` table (`cover_image`, `og_image`), allowing media files to be managed and tracked independently of the article body.
* **Tags**: Label taxonomies managed through an explicit intermediate table `ArticleTag` for high-performance indexing and querying.
* **Status**: Core workflow states: `draft`, `review`, `scheduled`, `published`, and `archived`.
* **Author**: Reference to the `AuthorProfile` model, which extends the base User model with bios, avatars, and display names.
* **content_blocks**: The `JSONB` field on the `ArticleTranslation` model where the collection of independent content blocks is persisted.

### Architectural Hierarchy Diagram

```
+---------------------------------------------------------------------------------+
|                                    ARTICLE                                      |
|  - id (Primary Key)                                                             |
|  - status (draft | review | scheduled | published | archived)                    |
|  - visibility (public | private | unlisted)                                     |
|  - published_at / scheduled_at (DateTime)                                       |
|  - views_count (Integer)                                                        |
|  - canonical_url (URL)                                                          |
|  - is_hot (Boolean)                                                             |
+---------------------------------------------------------------------------------+
      |                 |               |               |                   |
      | 1:N             | 1:1           | N:1           | N:1               | N:M (via ArticleTag)
      v                 v               v               v                   v
+--------------+ +-------------+ +-------------+ +-------------+    +---------------+
| Translation  | |   Author    | |  Category   | |   Series    |    |      Tag      |
| (Multi-lang) | |   Profile   | | (Hierarch.) | | (Grouping)  |    | - slug (UQ)   |
+--------------+ +-------------+ +-------------+ +-------------+    | - name        |
                                                                    +---------------+

Detailed ArticleTranslation Structure:
+---------------------------------------------------------------------------------+
|                              ARTICLETRANSLATION                                 |
|  - id (Primary Key)                                                             |
|  - article_id (Foreign Key -> ARTICLE)                                          |
|  - language_code (CharField: "fa" | "en" | "ar")                                  |
|  - slug (SlugField - Unique per language)                                       |
|  - title / excerpt / short_description (CharField / TextField)                   |
|  - seo_title / seo_description (CharField / TextField)                           |
|  - reading_time_sec (PositiveInteger)                                           |
|  - content_blocks (JSONB Column)                                                |
+---------------------------------------------------------------------------------+
                                       |
                                       | Holds ordered list of blocks
                                       v
+---------------------------------------------------------------------------------+
|                                 CONTENT_BLOCKS                                  |
| [                                                                               |
|   { "id": "blk_1", "type": "heading", "order": 1, "data": {...} },              |
|   { "id": "blk_2", "type": "paragraph", "order": 2, "data": {...} },            |
|   { "id": "blk_3", "type": "image", "order": 3, "data": {"media_id": 42} }      |
| ]                                                                               |
+---------------------------------------------------------------------------------+
```

---

## 3. The Block-Based Article

Under the Generic Block Engine, an article is no longer a structured "document" split into predetermined sections. It is an ordered, flat list of independent **Blocks**.

### Core Architecture Philosophy
The design of the block-based content engine is guided by several structural axioms:

1. **Atomic Independence**: Every block is an entirely self-contained entity. A block does not know or care about the block preceding it or following it. It possesses its own ID, configuration parameters, validation logic, and presentation rules.
2. **Deterministic Ordering**: The rendering order of the article content is dictated solely by the sorting of the blocks. The layout is determined by sequential positions in the array, making content layout dynamic and infinitely configurable.
3. **Decoupled Associations**: Relations between blocks are completely decoupled. Specifically, media assets are never embedded or nested within text-based fields.
   - *Legacy Approach*: A paragraph contained HTML like `<img src="path.jpg" align="left" />` alongside rich text.
   - *New Architecture*: The text is isolated inside a `ParagraphBlock`. The image is an autonomous `ImageBlock` that sits as a sibling in the block array. This ensures that a mobile application can choose to render the image full-screen, slide it, or hide it altogether, without complex HTML parsing.

### Conceptual Block Layout

```
                  LEGACY DOCUMENT                                 NEW BLOCK ENGINE
         +---------------------------------+             +---------------------------------+
         |             Title               |             |             Title               |
         +---------------------------------+             +---------------------------------+
         |  +---------------------------+  |             +---------------------------------+
         |  | Image (Embedded in HTML)  |  |             |      Heading Block (order: 1)   |
         |  +---------------------------+  |             +---------------------------------+
         |  This is a paragraph of rich-   |             +---------------------------------+
         |  text which surrounds the left- |   ======>   |    Paragraph Block (order: 2)   |
         |  aligned image, creating complex|             +---------------------------------+
         |  styling dependencies...        |             +---------------------------------+
         |                                 |             |      Image Block (order: 3)     |
         +---------------------------------+             +---------------------------------+
         |        [Section Border]         |             +---------------------------------+
         |  Another hardcoded paragraph... |             |    Paragraph Block (order: 4)   |
         +---------------------------------+             +---------------------------------+
```

By structuring the content as a stream of independent, clean data blocks, the presentation layer (whether it is SSR HTML, a native mobile View, or JSON feed) is freed from layout logic, allowing complete flexibility and extreme responsiveness.

---

## 4. Article Content Model

All block content resides within the `content_blocks` field of the `ArticleTranslation` model, utilizing PostgreSQL's native `JSONB` data type. Each block in the collection is enclosed in a standard container envelope.

### Standard Block Envelope Parameters

Every block contains the following core parameters:

* **`id` (String)**: A globally unique identifier for the block instance (typically prefixed with `blk_` or formatted as a UUID).
  * *Purpose*: Used as a unique key (`key={block.id}`) in modern reactive frontend frameworks (React/Vue) to prevent visual layout shifts and unnecessary component re-renders. It is also required for real-time collaborative editing (CRDTs).
* **`type` (String)**: The block identification tag (e.g., `heading`, `paragraph`, `image`).
  * *Purpose*: Acts as the polymorphism discriminator used by serializers to route validation and by rendering engines to dispatch content to components.
* **`version` (Positive Integer)**: The schema version of the specific block type.
  * *Purpose*: Allows smooth schema evolution. If a future iteration of a block requires a schema change, older blocks remain at `version: 1` and are migrated dynamically during retrieval.
* **`order` (Integer)**: An explicit sequential index.
  * *Purpose*: Provides a robust, deterministic ordering index that survives array serialization and drag-and-drop actions.
* **`settings` (Object - Optional)**: Presentation-specific styles and configurations (e.g., alignments, background colors, custom spacing).
  * *Purpose*: Separates visual appearance configuration from semantic content data, maintaining headless capability.
* **`metadata` (Object - Optional)**: Contextual tracking and auditing parameters (creation timestamps, editor IDs).
* **`data` (Object)**: The core content payload unique to the block type.

### Envelope JSON Schema Example

```json
{
  "id": "blk_a9e5b87c-129d-4e2a-89bc-993dcf50b86a",
  "type": "paragraph",
  "version": 1,
  "order": 2,
  "settings": {
    "text_alignment": "justify",
    "font_size": "medium",
    "background_color": "#f9f9f9"
  },
  "metadata": {
    "created_at": "2026-03-31T14:22:10Z",
    "last_edited_by": 12
  },
  "data": {
    "text": "معماری بلاک‌محور پایداری فوق‌العاده‌ای برای توسعه سیستم‌های بزرگ مقیاس فراهم می‌کند."
  }
}
```

---

## 5. Supported Content Blocks

The system provides a rich catalog of 15 registered, production-ready block types. Each block type registers with the `BlockRegistry` (defined in `posts/blocks.py`), defining its validation, data schema, media relationships, and empty-state detections.

### Supported Block Catalog

| Block Type | Purpose | Stored Data Schema | Validation Rules | Rendering Role |
| :--- | :--- | :--- | :--- | :--- |
| **`heading`** | Content structural headers | `{"level": 1-6, "text": "...", "anchor_id": "..."}` | Level must be between 1 and 6. Text is sanitized. | Outputs standard semantic heading tags (`<h2>`-`<h6>`). |
| **`paragraph`** | Body copy and rich-text | `{"text": "..."}` | Cannot be empty (stripped of HTML tags before validation). | Renders a standard `<p>` tag, supporting clean inline HTML (`<strong>`, etc.). |
| **`image`** | Single media presentation | `{"media_id": int, "caption": "...", "alt": "...", "lazy": bool}` | `media_id` must represent an active media asset in the DB. | Renders responsive images with alt text, captions, and lazy loading. |
| **`gallery`** | Carousel or grid of images | `{"media_ids": [int], "layout": "grid"\|"slider", "aspect_ratio": "..."}` | Array of `media_ids` must contain valid, active IDs. | Displays a layout-specific gallery (carousel or CSS grid). |
| **`quote`** | Highlighted text citations | `{"text": "...", "citation": "..."}` | Sanitized quote text. | Outputs blockquote HTML elements with a cite tag. |
| **`table`** | Tabular structured data | `{"headers": [str], "rows": [[str]]}` | Headers and rows must be arrays. | Renders secure, fully responsive standard HTML tables. |
| **`code`** | Syntax-highlighted code | `{"code": "...", "language": "...", "show_line_numbers": bool}` | Code must be string. Language must be valid identifier. | Feeds code content into highlight libraries (Prism.js / Shiki). |
| **`divider`** | Visual content splitters | `{"style": "solid"\|"dashed"\|"dots"}` | Enforces style options enum. | Renders `<hr>` tags with custom class styles. |
| **`video`** | Video player block | `{"media_id": int, "provider": "local"\|"youtube"\|"vimeo", "external_url": "...", "autoplay": bool, "controls": bool}` | Requires valid media ID or external URL. | Spawns a custom HTML5 player or iframe embed. |
| **`embed`** | Third-party service embeds | `{"url": "...", "embed_type": "twitter"\|"instagram"\|"iframe", "width": int, "height": int}` | Enforces provider options enum. | Renders social media widgets or secure sandbox iframes. |
| **`button`** | Call to Actions (CTA) | `{"label": "...", "url": "...", "target": "_blank"\|"_self", "style_preset": "..."}` | Enforces target enum and requires label/URL. | Renders a clean button link component. |
| **`accordion`** | Interactive collapsible tabs | `{"items": [{"title": "...", "content": "..."}]}` | Array of objects, title and content required. | Renders collapse/expand sections (frequently used for FAQ details). |
| **`faq`** | Semantic FAQ metadata | `{"questions": [{"q": "...", "a": "..."}]}` | Array of Q&A blocks. | Outputs collapsible UI elements and builds Google JSON-LD schema. |
| **`timeline`** | Chronological event lists | `{"events": [{"date": "...", "title": "...", "description": "..."}]}` | Date and title required. | Renders timeline graphics with date-ordered lists. |
| **`related_articles`**| Contextual article lists | `{"article_ids": [int]}` | IDs must map to active Article rows in the DB. | Resolves and injects previews of related articles. |

### Concrete Article Block Structure Example

The following JSON represents a fully validated, normalized content block collection:

```json
[
  {
    "id": "blk_heading_1",
    "type": "heading",
    "version": 1,
    "order": 1,
    "data": {
      "level": 2,
      "text": "مقدمه‌ای بر معماری میکروسرویس",
      "anchor_id": "microservice-intro"
    }
  },
  {
    "id": "blk_para_1",
    "type": "paragraph",
    "version": 1,
    "order": 2,
    "data": {
      "text": "معماری میکروسرویس به عنوان یکی از کلیدی‌ترین رویکردها در دنیای مدرن..."
    }
  },
  {
    "id": "blk_img_1",
    "type": "image",
    "version": 1,
    "order": 3,
    "data": {
      "media_id": 14,
      "caption": "نمودار ارتباطات سرویس‌ها",
      "alt": "Microservices Communication Diagram",
      "lazy": true
    }
  },
  {
    "id": "blk_divider_1",
    "type": "divider",
    "version": 1,
    "order": 4,
    "data": {
      "style": "dashed"
    }
  }
]
```

---

## 6. Article Creation Workflow

Creating a new block-based article executes a multi-tiered validation, sanitization, normalization, and relational linking pipeline inside the backend.

### Execution Flow Pipeline

```
 [ AUTHOR / EDITOR ]
          |
          | Submits Article Payload (JSON)
          v
 [ API BOUNDARY ] ---------------------> [ Payload Size Check ]
          |                                (Must be <= 5 Megabytes)
          v
 [ SERIALIZER VALIDATION ] ------------> [ Max Block Count Check ]
          |                                (Must be <= 200 blocks)
          |
          +----------------------------> [ Block Registry Schema Validation ]
          |                                (Conform to jsonschema envelopes & data)
          |
          +----------------------------> [ Business Logic Checks ]
          |                                (Uniqueness of block IDs and positions)
          |
          +----------------------------> [ Heading Hierarchy Validation ]
          |                                (Verify proper visual heading outline)
          |
          +----------------------------> [ Media Reference Check ]
          |                                (Query DB to verify all media exist & active)
          |
          +----------------------------> [ Empty Block Filtering ]
          |                                (Reject blank paragraph/image blocks)
          |
          v
 [ NORMALIZATION ] --------------------> [ Block Order Normalizer ]
          |                                (Sort blocks and make orders contiguous 1..N)
          v
 [ SANITIZATION ] ---------------------> [ BeautifulSoup HTML Sanitizer ]
          |                                (Strip <script>, onload attributes, etc.)
          v
 [ MEDIA SYNC ] -----------------------> [ MediaReferenceSynchronizer ]
          |                                (Link/unlink ArticleMedia in DB)
          v
 [ DATABASE WRITES ] ------------------> [ PostgreSQL Transaction ]
                                           (Commit Article and ArticleTranslation)
```

### In-Depth Stage Walkthrough

#### 1. API Boundary
The client app performs a `POST` request to `/api/v1/articles/` containing the global fields and the `content_blocks` JSON array. The backend's Web Application Firewall (WAF) and middleware verify the request headers.
- *Payload Limit*: The request body size is checked; if it exceeds **5MB**, the transaction is immediately terminated, protecting the application servers from DoS buffer allocation exploits.

#### 2. Serializer Validation
The payload is captured by `ArticleCreateUpdateSerializer` (in `posts/serializers.py`). If `content_blocks` is supplied, it invokes the custom `validate_content_blocks()` validation routine:
- **Block Count Check**: Validates that the number of blocks is within safe performance parameters (maximum **200 blocks**).
- **Generic Envelope Checks**: Iterates through each block, passing the payload to `block_registry.validate_block_payload()` (in `posts/blocks.py`). This verifies that core properties (`id`, `type`, `version`, `order`, `data`) exist with correct data types.
- **Specific Schema Validation**: Delegates schema validation to the corresponding `BaseBlock` subclass. The subclass evaluates the block's `data` payload using draft-07 `jsonschema`.
- **Identity & Order Uniqueness**: Verifies that every block in the array has a completely unique `id` and a unique initial `order`.
- **Heading Hierarchy Check**: Scans the document outline. If headings jump levels incorrectly (e.g., heading level 3 appears without a preceding level 2), it fails immediately to protect screen reader accessibility.
- **Media Relational Check**: Extracts all `media_id` fields referenced in image, gallery, and video blocks. It performs a single bulk query in PostgreSQL: `Media.objects.filter(id__in=extracted_ids, is_active=True)`. If any media is missing or inactive, it throws a localized, detailed error structure mapping precisely to the offending block index.
- **Empty Content Filtering**: Invokes the `.is_empty()` check on each block subclass. It flags empty paragraphs (e.g., `"<p>   </p>"` after stripping tag wrappers) and media blocks missing resource markers.

#### 3. Normalization
The block collection is sorted by the incoming `order` properties. The backend re-indexes each block's order value sequentially starting from **1** (e.g., array orders `[5, 12, 100]` are normalized cleanly to `[1, 2, 3]`), correcting editor spacing inconsistencies and preparing a predictable sequence.

#### 4. Sanitization
To prevent XSS (Cross-Site Scripting) injection attacks, all string fields inside the block's `data` payload undergo comprehensive HTML sanitization. The service parses raw string values with `BeautifulSoup` using a strict HTML tag safelist:
- Strips `<script>`, `<style>`, `<embed>`, `<object>`, and `<iframe>` (except verified embeds).
- Scrubs attributes starting with `on` (e.g., `onload`, `onclick`) and strips Javascript execution URIs (e.g., `src="javascript:..."`).
- Safely retains formatting tags like `<strong>`, `<em>`, `<a>`, and `<code>`.

#### 5. Media Synchronization
The database service layer processes the synchronized blocks to maintain relational tracking via the `ArticleMedia` intermediate table:
- Analyzes all referenced media across active blocks and cover/OG configurations.
- Executes bulk insertions and deletions on the `ArticleMedia` relationship table, locking the media assets to this article.

#### 6. Database Commit
All validations and formatting tasks are bundled inside an atomic PostgreSQL database transaction (`transaction.atomic()`). On success, the parent `Article` row and its localized child `ArticleTranslation` are written to disk.

---

## 7. Article Editing Workflow

Editing an article modifies the existing state of the block-based layout. When an editor submits a revised block list, the engine maintains absolute stability and consistency.

### Common Editing Operations

#### 1. Adding a Block
When an editor inserts a block in the middle of an article (e.g., placing an `ImageBlock` between paragraph 2 and paragraph 3):
- The frontend UI generates a unique UUID `id` and assigns a fractional or temporary order.
- On save, the backend receives the updated array, validates the new block schema, merges it into the validation flow, and runs the **Block Order Normalizer** to re-index the sequence (making the new image block `order: 3` and shifting subsequent blocks to `order: 4`, `order: 5`, etc.).

#### 2. Deleting a Block
When a block is deleted:
- The block is omitted from the submitted list.
- The backend processes the remaining list, recalculating contiguous indices.
- The **MediaReferenceSynchronizer** detects that a previously associated `media_id` is no longer present in the block sequence and automatically purges the corresponding row from `ArticleMedia` table.

#### 3. Reordering Blocks
When an editor drags and drops blocks in the admin editor:
- The UI rearranges block indices.
- On save, the backend uses the updated sequence array, resolves order conflicts, and rewrites the unified, normalized contiguous indices sequentially starting from 1.

#### 4. Replacing Media
When an image or video source is updated inside a block:
- The editor modifies `media_id` inside the visual block settings.
- The backend verifies that the new media ID represents a valid, active media asset.
- The relational sync system updates `ArticleMedia` links accordingly, freeing the old media from the article and linking the new file.

#### 5. Changing Headings
When modifying heading styles or levels:
- The heading level validation checks the new structural configuration against preceding headings, preventing layout changes from breaking heading outline standards.

### Ensuring System-Wide Consistency
By storing the block data within a single native `JSONB` array in `ArticleTranslation` and tracking media relationships through a separate table, the backend ensures:
- **No Orphaned Layout Rows**: Deleting or editing content blocks updates the parent record in a single transaction. There are no dangling orphaned section rows in secondary tables.
- **Accurate Media Tracking**: The `ArticleMedia` table remains synchronized with JSON block content in real-time, preventing the accidental deletion of referenced media assets.

---

## 8. Validation

Data integrity is the foundation of our content system. Because JSON fields are schema-less by default in relational databases, the backend implements a strict, multi-tiered validation pipeline before writing to PostgreSQL.

### Validation Pipeline Steps

```
[ Incoming Block JSON ]
          |
          v
1. Payload & Limit Check --------> [ Blocks limit: 200, Payload limit: 5MB ]
          |
          v
2. Schema Envelope Validation ----> [ Validates JSON layout via Registry ]
          |
          v
3. Duplicate Detection ----------> [ Rejects duplicate Block IDs and orders ]
          |
          v
4. Business Logic Validation -----> [ Conforms Heading Hierarchies & Block content ]
          |
          v
5. Media Referential Integrity ---> [ Validates and queries DB media references ]
          |
          v
6. HTML Sanitization -------------> [ BeautifulSoup Anti-XSS cleaning ]
          |
          v
[ Committed to Database ]
```

### In-Depth Validation Breakdown

#### 1. JSON Schema Envelope Validation
Every block must pass structurally. It is validated against the base schema envelope defined in `posts/blocks.py`:
- Checks for required keys: `id`, `type`, `version`, `order`, `data`.
- Enforces data types: `id` (string), `version` (integer), `order` (integer), `data` (object).
- Schema Version Verification: Rejects the request if the block's version number is higher than what is currently registered for that block type in the system registry, protecting against data corruption from incompatible schemas.

#### 2. Block-Specific Sub-Schema Validation
If the envelope is correct, the block type is checked against the registered types. The corresponding block class uses `jsonschema` to validate the `data` object structure:
- `heading`: Checks that `level` is an integer in the set `[1, 2, 3, 4, 5, 6]` and `text` is a string.
- `gallery`: Checks that `media_ids` is an array of positive integers, and visual options conform to the allowed layouts (`grid` or `slider`).
- `embed`: Validates that the URL matches provider specifications and checks parameters against allowed options (`twitter`, `instagram`, `iframe`).

#### 3. Duplicate Detection
- **Duplicate ID**: Verifies that every block in the collection has a unique ID, preventing conflicts when the frontend tracks elements.
- **Duplicate Order**: Ensures that no two blocks share the same `order` in the payload. While the normalizer fixes minor issues, explicit order conflicts (such as two completely different blocks sharing the same order number) are flagged as validation errors to prevent content loss.

#### 4. Heading Hierarchy Validation
The validation engine scans the entire list of blocks and extracts heading levels sequentially. It applies strict hierarchical accessibility rules:
- An article can start with any heading level.
- Subsequent heading jumps must be incremental. You can skip levels downward (e.g., an `H2` followed by an `H4` is forbidden, but an `H4` followed by an `H2` is valid as it represents a return to a parent section).
- Heading levels must not skip preceding levels (e.g., an `H3` must have a preceding `H2` in the document outline). This ensures the generated layout is accessible to search engines and screen readers.

#### 5. Payload Limits
- **Maximum Block Limit**: Restricts the block array size to **200 blocks** per article translation, ensuring rapid serialization and rendering.
- **Size Limit**: Enforces a absolute limit of **5MB** on the request size, protecting system memory from large-payload exploits.

#### 6. Media Validation
The validator checks all referenced `media_id` and `media_ids` fields:
- Queries the database in a single query to verify that all referenced media exist and are marked as `is_active=True`.
- Provides localized validation messages. If the article translation is Persian, the system returns a localized error response:
  `"رسانه‌ای با شناسه <ID> در کتابخانه رسانه‌ها وجود ندارد."`
  For other languages, it returns:
  `"Media with ID <ID> does not exist in the media library."`
  This error points directly to the invalid block index (e.g., `content_blocks[2].data.media_id`).

#### 7. HTML Sanitization
Finally, all strings within the block's `data` payload are parsed and sanitized using `BeautifulSoup` to strip out dangerous tags and script injection vectors, keeping client browsers safe.

---

## 9. Media inside Articles

Binary media assets are treated with the highest level of isolation. Rather than embedding files as inline base64 or static markup, they are managed via strict **Media References**.

### Media Blocks and Referenced Assets
Three dedicated blocks handle visual content:
1. **`image`**: References a single `Media` asset via `media_id`.
2. **`gallery`**: References multiple `Media` assets via a list of `media_ids`.
3. **`video`**: References a single video asset via `media_id` or links to an external service (YouTube/Vimeo).

### Automatic Expansion Pattern
During API delivery, the `ArticleDetailSerializer` intercepts the raw blocks:
- Gathers all referenced `media_id` parameters across the block array in a single pass.
- Runs a single optimized SQL query to pull the matching rows from the `medias_media` table, preventing N+1 queries.
- Serializes the media attributes (`id`, `url`, `mime_type`, `width`, `height`, `title`) and injects them under the block's nested `media` property (or `medias` for galleries) on the fly.

### Synchronization with ArticleMedia & Prevention of Orphans
To prevent the accidental deletion of media files currently in use, the backend relies on an active synchronization routine:
- When an article is created or updated, the system triggers `sync_article_media()`.
- This function scans the active blocks, aggregates all media IDs in use, and syncs them with the `ArticleMedia` intermediate table under the `"in-content"` attachment type.
- The media library uses these relational links as "locks". A media asset cannot be deleted from the system as long as it has active records in the `ArticleMedia` table, preventing broken images and video links across published articles.

### Media Lifecycle Diagram

```
[ Upload File ]
       |
       v
[ Media Library Asset Created ] ------> Assigns unique media_id (e.g., ID: 42)
       |
       v
[ Linked in Article Block ] ---------> Block data: {"media_id": 42}
       |
       v
[ Sync Article Media Service ] -------> Creates record in ArticleMedia table
       |                                (Binds ID 42 to Article, attachment_type: "in-content")
       v
[ API Detail Fetch ] ----------------> Serializer expands media_id with URL & meta
       |
       v
[ Content Deleted / Updated ] -------> sync_article_media detects ID 42 is gone,
                                       removes row from ArticleMedia, releasing the "lock"
```

---

## 10. Reading Time

The system calculates reading times automatically, saving editors from manual estimation.

### Calculation Methodology
- **Trigger**: The calculation runs automatically within the `save()` method of `ArticleTranslation` when `content_blocks` are modified.
- **Measurement Unit**: The reading time is calculated and stored in the database in **seconds** (`reading_time_sec`).

### Processing Rules
1. **Contributory Blocks**: The reading time is calculated only from blocks that contain parseable textual content, specifically:
   - `paragraph` (the body copy).
   - `heading` (the headers).
   - `quote` (the text block).
   - `accordion` and `faq` (titles and answers).
2. **Ignored Blocks**: Purely visual or structural blocks (such as `divider`, `image`, `gallery`, `video`, `related_articles`, `button`) are skipped.
3. **HTML Parsing**: For every contributory block, the service extracts the text content and runs it through `BeautifulSoup` to strip any formatting tags. This ensures that only raw, visible words are counted (preventing HTML tag strings from bloating the count).
4. **Word Count Algorithm**: The system extracts words using a regex pattern (`r"\w+"`) that supports multi-character languages (including English, Persian, Arabic).
5. **Reading Speed Formula**:
   $$\text{Reading Time in Seconds} = \left( \frac{\text{Word Count}}{200} \right) \times 60$$
   *(Based on a standard reading speed of 200 words per minute).*

---

## 11. API Representation

When client applications request an article detail, the API serves a fully-formed, unified response.

### Realistic API JSON Response (200 OK)

**Endpoint**: `/api/v1/articles/clean-architecture-django/?lang=fa`

```json
{
  "status": "success",
  "data": {
    "id": 142,
    "slug": "clean-architecture-django",
    "title": "معماری تمیز در جنگو",
    "excerpt": "آموزش گام‌به‌گام پیاده‌سازی الگوهای تمیز در فریم‌ورک جنگو",
    "short_description": "چگونه کدهای جنگوی خود را مقیاس‌پذیر و تست‌پذیر بنویسیم.",
    "reading_time_sec": 120,
    "status": "published",
    "is_hot": true,
    "published_at": "1405/01/10 12:00:00",
    "author": {
      "display_name": "نیما راد",
      "avatar": {
        "id": 5,
        "url": "https://cdn.example.com/medias/avatars/nima.png",
        "mime": "image/png"
      }
    },
    "category": "برنامه‌نویسی",
    "cover_image": {
      "id": 12,
      "url": "https://cdn.example.com/medias/covers/clean-arch.jpg",
      "mime": "image/jpeg"
    },
    "views_count": 1054,
    "likes_count": 42,
    "comments_count": 5,
    "tags": [
      {
        "id": 1,
        "slug": "django",
        "name": "جنگو"
      },
      {
        "id": 2,
        "slug": "architecture",
        "name": "معماری"
      }
    ],
    "content_blocks": [
      {
        "id": "blk_heading_1",
        "type": "heading",
        "version": 1,
        "order": 1,
        "settings": {
          "text_alignment": "right"
        },
        "data": {
          "level": 2,
          "text": "چرا معماری تمیز؟",
          "anchor_id": "why-clean-architecture"
        }
      },
      {
        "id": "blk_para_1",
        "type": "paragraph",
        "version": 1,
        "order": 2,
        "settings": {},
        "data": {
          "text": "در این مقاله یاد می‌گیریم که چطور کدهایی توسعه دهیم که مستقل از ابزارها باشند."
        }
      },
      {
        "id": "blk_img_1",
        "type": "image",
        "version": 1,
        "order": 3,
        "settings": {
          "display_width": "full"
        },
        "data": {
          "media_id": 14,
          "caption": "ارتباط لایه‌ها در معماری تمیز",
          "alt": "Clean Architecture Layers",
          "lazy": true,
          "media": {
            "id": 14,
            "url": "https://cdn.example.com/medias/layers-clean.png",
            "mime": "image/png",
            "width": 1200,
            "height": 800,
            "title": "Layers Chart"
          }
        }
      }
    ],
    "canonical_url": "https://example.com/clean-architecture-django",
    "series": null,
    "seo_title": "آموزش معماری تمیز در جنگو | مستندات فنی",
    "seo_description": "آموزش کامل پیاده‌سازی اصول معماری تمیز در پروژه‌های Django.",
    "og_image": {
      "id": 13,
      "url": "https://cdn.example.com/medias/og/clean-arch-og.jpg",
      "mime": "image/jpeg"
    },
    "media_attachments": [
      {
        "id": 512,
        "media": {
          "id": 14,
          "url": "https://cdn.example.com/medias/layers-clean.png",
          "mime": "image/png"
        },
        "attachment_type": "in-content"
      }
    ],
    "related_articles": []
  },
  "messagesList": []
}
```

### Property Dictionary and Consumption Guidance

* **`reading_time_sec`**: Integer. Used by the frontend to display a "X min read" label (e.g. `Math.ceil(reading_time_sec / 60)`).
* **`published_at`**: Jalali string formatted representation. Injected directly into localized Persian views.
* **`content_blocks`**: Array of polymorphic objects. Sorted strictly by `order`. The client-side application loops through this collection to construct the article layout.
* **`media_attachments`**: List of all media linked to the article (cover, OG, inline), which helps client prefetchers load assets early.

---

## 12. Frontend Rendering

The headless frontend (Next.js / React) consumes the API's structured block array to generate semantic, highly interactive layouts.

### Processing Pipeline
The frontend converts the JSON payload into an interactive UI following this pipeline:

```
[ API Response: content_blocks ]
               |
               v
[ 1. Sort and Map Blocks ] -------> Sort blocks by "order" index (safety check)
               |
               v
[ 2. Layout Dispatcher Loop ] ----> Map block.type to dynamic React component
               |
               +------------------> "heading"   -> <HeadingBlock ... />
               +------------------> "paragraph" -> <ParagraphBlock ... />
               +------------------> "image"     -> <ImageBlock ... />
               |
               v
[ 3. Component Rendering ] --------> Inject semantic markup, styles, animations
               |
               v
[ 4. Hydration & Interactive UI ] -> Hydrate clients, enable lazy-loading viewport
```

### Component Dispatcher Code Pattern
```typescript
import React from 'react';
import { Paragraph, Heading, ImageComponent, Quote } from '@/components/blocks';

interface Block {
  id: string;
  type: string;
  data: any;
  settings?: any;
}

const BLOCK_MAP: Record<string, React.FC<any>> = {
  heading: Heading,
  paragraph: Paragraph,
  image: ImageComponent,
  quote: Quote,
};

export const ArticleRenderer: React.FC<{ blocks: Block[] }> = ({ blocks }) => {
  // Enforce deterministic sequence
  const sortedBlocks = [...blocks].sort((a, b) => a.order - b.order);

  return (
    <article className="article-content-wrapper">
      {sortedBlocks.map((block) => {
        const Component = BLOCK_MAP[block.type];
        if (!Component) {
          // Graceful fallback prevents the application from crashing on unknown block types
          console.warn(`Unsupported block type: ${block.type}`);
          return null;
        }
        return (
          <Component
            key={block.id}
            data={block.data}
            settings={block.settings}
          />
        );
      })}
    </article>
  );
};
```

### Advantages of the Dispatcher Pattern
- **Dynamic CSS/JS Bundling**: Using dynamic imports (`next/dynamic`), components like `CodeBlock` or `TimelineBlock` are loaded only if the article contains those block types, reducing initial bundle sizes.
- **Lazy Loading Viewports**: Blocks below the fold can be wrapped in a lazy-load viewport boundary (`IntersectionObserver`), preventing non-visible media blocks from downloading assets prematurely.

---

## 13. Performance

The transition from raw HTML content fields to the Generic Block Engine brings significant performance improvements across our entire tech stack.

### Operational Improvements

```
       LEGACY HTML-BASED CMS                        NEW BLOCK ENGINE CMS
   +---------------------------+                +---------------------------+
   |   Single database read    |                |   Single database read    |
   |   of massive HTML string  |                |   of highly indexed JSONB |
   +---------------------------+                +---------------------------+
                 |                                            |
                 v                                            v
   +---------------------------+                +---------------------------+
   | Complex backend Regex /   |                |  Batch prefetching of all |
   | DOM parsing on every view |                |  referenced media in block|
   +---------------------------+                +---------------------------+
                 |                                            |
                 v                                            v
   +---------------------------+                +---------------------------+
   | Slow, dynamic N+1 media   |                | Fast CDN caching and page |
   | asset queries per image   |                | generation (Next.js SSR)  |
   +---------------------------+                +---------------------------+
```

### 1. Serialization
- Under the old system, inserting relational media elements into HTML content required slow, recursive Regex lookups and string manipulations.
- With JSON blocks, the serializer collects all `media_id` properties across the block array in a single loop and runs a single optimized database query. It then map-associates media definitions instantly before returning the response.

### 2. Database Queries
- Storing blocks in a single PostgreSQL `JSONB` column eliminates the need to run SQL joins across separate layout tables (such as a legacy Sections table). The database engine fetches the complete article content in a single row query.

### 3. Caching Strategies
The CMS leverages a high-performance **Redis Cache-Aside** layer alongside edge caching:
- **Redis Cache**: Detailed API responses, including fully expanded media objects, are cached under structured keys:
  `active_article:detail:{language_code}:{slug}`
  This reduces database hits for read operations down to zero.
- **CDN Caching**: Edge CDN nodes cache responses using custom headers (`Cache-Control: public, max-age=31536000, s-maxage=604800, stale-while-revalidate=60`). This allows read traffic to be offloaded to edge nodes closest to the user.
- **Background Invalidation**: When an article is updated, database signals trigger background tasks (via Celery) to purge CDN caches and update Redis.

### 4. CDN Media Optimization
- Expanded media responses provide width, height, and format metadata. This allows the frontend to request optimized, modern image formats (like `AVIF`, `WebP`) with explicit sizes, preventing layout shifts and lowering bandwidth usage.

---

## 14. Security

The Generic Block Engine has been engineered to secure content publish-pipelines against common security vulnerabilities.

### Security Defenses

* **Cross-Site Scripting (XSS) Mitigation**: The backend processes all incoming content strings using a strict BeautifulSoup sanitization parser. Any hazardous elements (such as `<script>`, `<style>`, `<embed>`, or `<object>` tags, as well as `onload` inline event scripts) are completely stripped out before content is saved.
* **Payload Size Constraints**: The backend strictly enforces a **5MB limit** on request payloads. This prevents memory exhaustion and Denial of Service (DoS) attacks on the application servers.
* **Database Isolation**: Storing block configurations as structured JSON fields eliminates the risk of SQL Injection within content layouts. Input is parsed directly through safe ORM parameters.
* **Media Ownership Validation**: The serializer verifies that referenced `media_id` assets are marked as active and exist in the database, protecting against unauthorized or broken file references.

---

## 15. Database Architecture

Our database architecture keeps data highly organized and normalized, and handles older, legacy articles gracefully.

### Database ERD Outline

```
  +--------------------+             1:N             +--------------------+
  |   posts_article    | --------------------------> |posts_articletrans. |
  |--------------------|                             |--------------------|
  | id (PK)            |                             | id (PK)            |
  | status             |                             | article_id (FK)    |
  | category_id (FK)   |                             | language_code      |
  | cover_image_id(FK) |                             | slug               |
  | og_image_id (FK)   |                             | content_blocks     |
  +--------------------+                             | reading_time_sec   |
           |                                         +--------------------+
           |                                                   |
           | 1:N                                               | Generates refs
           v                                                   v
  +-----------------------+      N:1 References      +--------------------+
  |  medias_articlemedia  | -----------------------> |    medias_media    |
  |-----------------------|                          |--------------------|
  | id (PK)               |                          | id (PK)            |
  | article_id (FK)       |                          | storage_key        |
  | media_id (FK)         |                          | url, mime_type     |
  | attachment_type       |                          +--------------------+
  +-----------------------+
```

### Storing JSONB Blocks
The system uses PostgreSQL's native `JSONB` column on the `ArticleTranslation` model to store content blocks. This binary format:
- Compresses whitespace and speeds up retrieval.
- Supports fast, GIN-indexed structural queries (e.g., `SELECT * FROM posts_articletranslation WHERE content_blocks @> '[{"type": "video"}]';` executes in milliseconds).

### Backward Compatibility with Legacy Content
To support older articles written before the Generic Block Engine migration, the `ArticleTranslation` model retains a fallback path:
- **Fallback Content Rendering**: If `content_blocks` is empty, the serializer checks the legacy `content` HTML field.
- **Automatic Conversion**: A background migration script parses the legacy HTML string using BeautifulSoup. It splits paragraphs into `ParagraphBlocks`, headers into `HeadingBlocks`, and embedded images into sequential `ImageBlocks`, converting legacy content into structured JSON blocks without manual editing.

---

## 16. Enterprise Assessment

The Generic Block Engine transition is a major technical milestone that provides our CMS platform with enterprise-grade stability and scalability.

### Architectural Evaluation

* **Scalability**: Fetching complete layouts in a single JSONB query reduces database CPU usage, allowing the platform to serve high-volume traffic with ease.
* **Maintainability**: Centralizing block logic in `posts/blocks.py` keeps the system clean and decoupled. Developers can maintain individual blocks without affecting the core publishing pipeline.
* **Extensibility & Future Blocks**: Adding a new block type (e.g., `related_articles` or a custom CTA) is highly straightforward:
  - Subclass `BaseBlock` in `posts/blocks.py`.
  - Define its data schema.
  - Register it in `BlockRegistry`.
  - The new block is instantly available across serializers, validators, and client apps without needing any database migrations.
* **Flexibility**: The layout is decoupled from visual design. If the corporate branding updates, only the frontend components need to change—the database blocks remain clean and semantic.

### Key Technical Accomplishments
1. **Zero Layout Table Overhead**: Eliminated database joins for content layout sections.
2. **Dynamic Media Locking**: Designed the `ArticleMedia` synchronization tracker to protect assets from being deleted while in use.
3. **Robust Anti-XSS Protection**: Integrated strict BeautifulSoup parsing on all block text elements, keeping client browsers secure.

### Remaining Limitations and Future Improvements
- **Block Version Upgrades**: Over time, block schemas will evolve. The system should introduce an automated, run-time schema upgrade engine to migrate blocks on-the-fly when reading older version arrays.
- **Collaborative Editing Locks**: Implementing real-time editing (like Google Docs) requires field-level locking or CRDT synchronization on individual block elements within the JSONB array.
- **Block Search Indexing**: Full-text searching currently reads the entire JSONB block payload. We can optimize search performance by building a dedicated PostgreSQL index that extracts and indexes only textual content blocks.
