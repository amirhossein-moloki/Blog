# Database Documentation

The Blog Platform uses PostgreSQL as its primary transactional database. All models inherit from a common base for consistency.

---

## Base Model (`core.base_models.BaseModel`)
All entities share these fields:
| Field | Type | Nullable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `is_active` | Boolean | No | `True` | Soft-deactivation flag. |
| `created_at` | DateTime | No | `now()` | Audit: When created. |
| `updated_at` | DateTime | No | `now()` | Audit: Last modification. |

---

## Core Models

### 1. `users.User`
Extends `AbstractUser`.
- `profile_picture`: `ImageField`.

### 2. `posts.Article`
The central content entity.
| Field | Type | Description |
| :--- | :--- | :--- |
| `canonical_url` | URLField | Canonical URL for SEO. |
| `is_hot` | Boolean | Flag indicating trending/hot articles. |
| `status` | Choice | Draft, Review, Scheduled, Published, Archived. |
| `visibility` | Choice | Public, Private, Unlisted. |
| `published_at` | DateTime | Publication timestamp. |
| `scheduled_at` | DateTime | Scheduled publication time. |
| `author` | ForeignKey | References `AuthorProfile`. |
| `category` | ForeignKey | References `Category`. |
| `series` | ForeignKey | References `Series`. |
| `cover_image` | ForeignKey | References `medias.Media` (cover image). |
| `og_image` | ForeignKey | References `medias.Media` (OG image). |
| `views_count` | Integer | Total page views tracker. |
| `related_articles` | ManyToManyField | Self-referential manual relation mapping. |

### 3. `posts.ArticleTranslation`
Localized content per language.
| Field | Type | Description |
| :--- | :--- | :--- |
| `article` | ForeignKey | References `Article`. |
| `language_code` | CharField | Language identifier (e.g., 'en', 'fa'). |
| `slug` | SlugField | Localized slug. |
| `title` | CharField | Localized title. |
| `excerpt` | TextField | Short summary of the article. |
| `short_description` | TextField | Optional localized short description metadata. |
| `content` | RichText | CKEditor 5 HTML content. |
| `reading_time_sec` | Integer | Automatically calculated word-count based estimate. |
| `seo_title` | CharField | Custom SEO title. |
| `seo_description` | TextField | Custom SEO meta description. |

### 4. `posts.Category`
Hierarchical taxonomy for grouping articles.
| Field | Type | Description |
| :--- | :--- | :--- |
| `slug` | SlugField | Unique URL identifier. |
| `name` | CharField | Category name. |
| `parent` | ForeignKey | Self-referential parent category link. |
| `description` | TextField | Optional description. |
| `order` | Integer | Display ordering order. |
| `icon` | FileField | Category icon, supports **SVG** format. |

### 5. `medias.Media`
Centralized asset registry.
- `storage_key`: The path in the storage backend (Local/S3).
- `type`: `image`, `video`, `file`, `audio`.
- `width` / `height`: Metadata extracted from images.

### 6. `interactions.Comment`
- `parent`: Self-referential FK for nested threads.
- `status`: Moderation state (Pending, Approved, Rejected).

### 7. `posts.PodcastCategory`
Taxonomy categories for podcasts.
| Field | Type | Description |
| :--- | :--- | :--- |
| `title` | CharField | Category title. |
| `slug` | SlugField | Unique slug for SEO and routing. |
| `icon` | FileField | Category icon supporting SVGs. |

### 8. `posts.Podcast`
Podcast episodes containing media streams and metadata.
| Field | Type | Description |
| :--- | :--- | :--- |
| `title` | CharField | Episode title. |
| `slug` | SlugField | Unique localized slug. |
| `category` | ForeignKey | References `PodcastCategory`. |
| `episode_number` | Integer | Episode sequence number. |
| `cover_image` | ImageField | Artwork/Cover of the episode. |
| `audio_file` | FileField | Uploaded MP3/audio track file. |
| `media_type` | Choice | `audio` or `video` media type. |
| `video_file` | FileField | Uploaded MP4/video track file. |
| `video_url` | URLField | External streaming/embedding video URL. |
| `description` | RichText | Episode show notes (CKEditor 5 HTML). |
| `duration` | Integer | Duration in minutes. |
| `published_date` | DateTime | Release timestamp. |
| `view_count` | Integer | View count (incremented automatically). |
| `related_podcasts` | ManyToManyField | Self-referential association for recommendation. |

### 9. `posts.GalleryItem`
A visual Polaroid item in a slider/list.
| Field | Type | Description |
| :--- | :--- | :--- |
| `image` | ImageField | Polaroid photo. |
| `caption` | CharField | Small descriptive caption/text. |
| `order` | Integer | Ordering index for custom sorting. |
| `link` | URLField | Optional destination target link. |

---

## Custom Managers & QuerySets

### `ArticleManager.published()`
Filters articles where `status='published'` and optimized with `select_related` on author and category to avoid N+1 query issues.

### `ArticleManager.get_queryset()`
Automatically annotates articles with `comments_count` and `likes_count` using Django's `Coalesce` and `Count`.

---

## Relationships & Constraints
- **One-to-One:** `AuthorProfile` → `User` (Shared primary key).
- **Many-to-Many:**
    - `Article` ↔ `Tag` (via `ArticleTag` through model).
    - `Article` ↔ `Article` (self-referential `related_articles` for manual recommendations).
    - `Podcast` ↔ `Podcast` (self-referential `related_podcasts` for episode recommendations).
- **Generic Relation:** `Reaction` can link to any model using `content_type` and `object_id`.
- **Unique Together:**
    - `Reaction`: `user`, `content_type`, `object_id`, `reaction` (Prevents duplicate reactions).
    - `ArticleTag`: `article`, `tag`.
    - `ArticleMedia`: `article`, `media`, `attachment_type`.
    - `ArticleTranslation`: `article` + `language_code` & `slug` + `language_code`.

---

## Business Rules
1. **Reading Time:** Calculated in `ArticleTranslation.save()` based on word count (approx. 200 words/min).
2. **Slug Uniqueness:** Slugs are unique and immutable once published to preserve SEO.
3. **Media Sync:** Automated cleanup of orphaned content-media links.
4. **Podcast Views Tracking:** Ingesting retrieve details of `Podcast` automatically increments its `view_count` atomically to prevent race conditions.
