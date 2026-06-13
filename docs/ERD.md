# Database ERD

The following diagram illustrates the core models and their relationships.

```mermaid
erDiagram
    USER ||--o| AUTHOR_PROFILE : "has one"
    USER ||--o{ MEDIA : "uploads"
    USER ||--o{ COMMENT : "writes"
    USER ||--o{ REACTION : "performs"

    AUTHOR_PROFILE ||--o{ POST : "authors"

    POST ||--o{ COMMENT : "contains"
    POST ||--o{ REVISION : "has"
    POST }o--o{ TAG : "tagged with"
    POST }o--|| CATEGORY : "belongs to"
    POST }o--o| SERIES : "part of"

    POST ||--o{ POST_MEDIA : "attaches"
    MEDIA ||--o{ POST_MEDIA : "linked via"

    COMMENT ||--o{ COMMENT : "parent of (nested)"

    REACTION }o--|| CONTENT_TYPE : "targets"

    MENU ||--o{ MENU_ITEM : "contains"
    MENU_ITEM ||--o{ MENU_ITEM : "parent of"

    class POST {
        string slug
        string title
        text content
        string status
        int views_count
    }

    class MEDIA {
        string storage_key
        string type
        string url
        int size_bytes
    }

    class COMMENT {
        text content
        string status
    }
```

---

## Junction Tables
- **`PostTag`:** Connects `Post` and `Tag`.
- **`PostMedia`:** Connects `Post` and `Media` with an `attachment_type` (cover, og-image, in-content).
