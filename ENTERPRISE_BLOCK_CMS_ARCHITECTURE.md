# Enterprise Headless Block-Based CMS Architecture Specification

This document presents the finalized technical design and architectural specification for our next-generation, Enterprise-grade **Presentation-Agnostic Block-Based Content Engine** conforming strictly to headless CMS standards.

---

## 1. Core Design Philosophy

Our platform uses a purely **Block-Based Content Philosophy** inspired by modern headless standards (Notion, Sanity, and Storyblok).

### Principal Headless Axioms

1. **Atomic Independence**: An article is modeled strictly as a flat, ordered list of independent, presentation-agnostic Blocks. A Block is the minimal, indivisible unit of content.
2. **Deterministic Ordering**: The relative order of Blocks in the storage array is the sole arbiter of rendering sequence.
3. **Decoupled Associations**: No implicit or explicit relationship exists between different types of blocks unless declared as structured data.
4. **Presentation-Agnostic Structure**: The backend is prohibited from rendering HTML, housing UI templates, managing stylesheet links, or containing CSS framework details.
5. **Zero Frontend Coupling**: The backend has **zero knowledge** of frontend component identifiers or component names (such as "ImageBlock" or "ParagraphBlock"). The client application is entirely responsible for mapping typed payload schemas (`type`) to native display elements.

### ASCII Conceptual Diagram

```
+-----------------------------------------------------------------------+
|                             Article                                   |
|   - article_schema_version: 2                                         |
|   - structured_data: [ {"@type": "FAQPage"}, {"@type": "Video"} ]    |
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

## 2. Universal Block Structure & JSON Design

Every block conforms to a uniform, standard container envelope.

### Standard Block Envelope

```json
{
  "id": "blk_9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "type": "paragraph",
  "version": 1,
  "order": 3,
  "settings": {
    "align": "justify",
    "spacing": "md",
    "theme": "default",
    "visibility": "visible",
    "animation": "fade-in",
    "width": "contained",
    "container": "default",
    "responsive": {},
    "custom_class": null
  },
  "meta": {
    "locked": false,
    "hidden": false,
    "created_by": 42,
    "updated_by": null,
    "draft": false,
    "deleted": false,
    "internal_notes": "Internal review complete"
  },
  "data": {
    "content": [
      {
        "type": "text",
        "value": "معماری بلاک‌محور پایداری فوق‌العاده‌ای برای مدیریت تغییرات ارائه می‌دهد."
      }
    ]
  }
}
```

### Property Dictionary

* **`id` (UUIDv4 or Custom K-Sortable ID)**: Globally unique identifier for the block instance.
* **`type` (String)**: Polymorphism key (e.g., `heading`, `paragraph`, `image`). Client maps `type -> Component` internally.
* **`version` (Positive Integer)**: The schema version of the specific block type.
* **`order` (Integer)**: Explicit rendering rank.
* **`settings` (Object)**: Standardized presentational properties (`align`, `spacing`, `theme`, `visibility`, `animation`, `width`, `container`, `responsive`, `custom_class`, `variant`, `appearance`).
* **`meta` (Object)**: Internal editor/runtime metadata (`locked`, `hidden`, `created_by`, `updated_by`, `draft`, `deleted`, `internal_notes`). Not returned as display data.
* **`data` (Object)**: Core semantic payload of the block.

---

## 3. Improved Block Types

Below is the definitive catalogue of block data schemas:

### 1. `heading`
* *Data Schema*: `{"level": 1|2|3|4|5|6, "text": "...", "anchor_id": "..."}`

### 2. `paragraph`
* *Data Schema*: Recursive node arrays with no raw HTML dependencies.
* *Supported Node Types*: `text`, `strong`, `code`, `italic`, `underline`, `strike`, `link`, `inline_code`, `emoji`, `mention`, `highlight`, `subscript`, `superscript`, `keyboard`, `small`, `mark`.
* *Example Node payload*:
  ```json
  {
    "type": "link",
    "href": "https://example.com",
    "title": "Example Website",
    "children": [
      {
        "type": "strong",
        "value": "Visit Site"
      }
    ]
  }
  ```

### 3. `image`
* *Data Schema*: Extended to include performant responsive and focal settings.
* *Attributes*:
  ```json
  {
    "media_id": 42,
    "caption": "My Image Caption",
    "alt": "Accessible Alt Text",
    "lazy": true,
    "link": "https://example.com",
    "target": "_blank",
    "object_fit": "cover",
    "focal_point": {"x": 0.5, "y": 0.5},
    "loading": "lazy",
    "decoding": "async",
    "fetch_priority": "high",
    "responsive_behavior": "responsive"
  }
  ```

---

## 4. Enhanced Media & Variants Payload

Exposes comprehensive runtime media metadata for client-side optimization:

```json
{
  "id": 42,
  "url": "https://cdn.example.com/medias/2026/03/pic.jpg",
  "type": "image",
  "mime": "image/jpeg",
  "width": 1920,
  "height": 1080,
  "size_bytes": 145020,
  "alt_text": "Clean Architecture",
  "title": "Clean Architecture",
  "uploaded_by": 1,
  "created_at": "2026/03/31 12:00:00",
  "updated_at": "2026/03/31 12:05:00",
  "status": "Ready",
  "is_deleted": false,
  "content_hash": "a8f6c...",
  "checksum": "a8f6c...",
  "checksum_algorithm": "SHA256",
  "dominant_color": "#ffffff",
  "blur_hash": "L6PZf9e.D%f_00%~9FpI_3WBMybH",
  "placeholder": null,
  "is_animated": false,
  "storage_provider": "local",
  "metadata": {
    "width": 1920,
    "height": 1080,
    "mime": "image/jpeg",
    "size": 145020
  },
  "variants": {
    "thumbnail": "https://cdn.example.com/medias/2026/03/pic_thumb.jpg"
  }
}
```

---

## 5. Media Attachment Management Statistics

Article-level media attachments serve exclusively administrative purposes and are completely optional for rendering. They include metadata tracking:

```json
{
  "media": { "id": 42, "url": "..." },
  "attachment_type": "in-content",
  "usage_count": 2,
  "referenced_by": ["blk_1", "blk_5"],
  "lock_status": true
}
```

---

## 6. Article-Level Structured SEO (JSON-LD)

To prevent individual block pollution, blocks register SEO metadata dynamically. The backend aggregates these contributions into a top-level `structured_data` array:

```json
{
  "structured_data": [
    {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "What is Headless?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Headless decouples content from display."
          }
        }
      ]
    }
  ]
}
```

This ensures complete presentation independence while giving the client-side framework ready-to-inject JSON-LD metadata.
