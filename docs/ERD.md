# Database ERD

The following diagram illustrates the core models and their relationships.

```mermaid
erDiagram
    USER ||--o| AUTHOR_PROFILE : "has one"
    USER ||--o{ MEDIA : "uploads"
    USER ||--o{ COMMENT : "writes"
    USER ||--o{ REACTION : "performs"

    AUTHOR_PROFILE ||--o{ ARTICLE : "authors"

    ARTICLE ||--o{ COMMENT : "contains"
    ARTICLE ||--o{ REVISION : "has"
    ARTICLE }o--o{ TAG : "tagged with"
    ARTICLE }o--|| CATEGORY : "belongs to"
    ARTICLE }o--o| SERIES : "part of"

    ARTICLE ||--o{ ARTICLE_MEDIA : "attaches"
    MEDIA ||--o{ ARTICLE_MEDIA : "linked via"

    COMMENT ||--o{ COMMENT : "parent of (nested)"

    REACTION }o--|| CONTENT_TYPE : "targets"

    MENU ||--o{ MENU_ITEM : "contains"
    MENU_ITEM ||--o{ MENU_ITEM : "parent of"

    class ARTICLE {
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
- **`ArticleTag`:** Connects `Article` and `Tag`.
- **`Media`:** Connects `Article` and `Media` with an `attachment_type` (cover, og-image, in-content).
