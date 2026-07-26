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
    ARTICLE ||--o{ ARTICLE_TRANSLATION : "has"
    ARTICLE }o--o{ ARTICLE : "related to (self)"

    ARTICLE ||--o{ ARTICLE_MEDIA : "attaches"
    MEDIA ||--o{ ARTICLE_MEDIA : "linked via"

    COMMENT ||--o{ COMMENT : "parent of (nested)"

    REACTION }o--|| CONTENT_TYPE : "targets"

    MENU ||--o{ MENU_ITEM : "contains"
    MENU_ITEM ||--o{ MENU_ITEM : "parent of"

    PODCAST_CATEGORY ||--o{ PODCAST : "classifies"
    PODCAST }o--o{ PODCAST : "related to (self)"

    class ARTICLE {
        string canonical_url
        boolean is_hot
        string status
        string visibility
        datetime published_at
        datetime scheduled_at
        int views_count
    }

    class ARTICLE_TRANSLATION {
        string language_code
        string slug
        string title
        text excerpt
        text short_description
        text content
        int reading_time_sec
        string seo_title
        text seo_description
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

    class PODCAST_CATEGORY {
        string title
        string slug
        file icon
    }

    class PODCAST {
        string title
        string slug
        int episode_number
        file cover_image
        file audio_file
        string media_type
        file video_file
        string video_url
        text description
        int duration
        datetime published_date
        int view_count
    }

    class GALLERY_ITEM {
        file image
        string caption
        int order
        string link
    }
```

---

## Junction Tables
- **`ArticleTag`:** Connects `Article` and `Tag`.
- **`ArticleMedia`:** Connects `Article` and `Media` with an `attachment_type` (cover, og-image, in-content).
- **`related_articles`:** Self-referential junction table for `Article`.
- **`related_podcasts`:** Self-referential junction table for `Podcast`.
