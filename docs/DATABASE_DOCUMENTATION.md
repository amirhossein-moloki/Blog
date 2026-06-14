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

### 2. `posts.Post`
The central content entity.
| Field | Type | Description |
| :--- | :--- | :--- |
| `slug` | Slug | Unique URL identifier. |
| `status` | Choice | Draft, Review, Scheduled, Published, Archived. |
| `visibility` | Choice | Public, Private, Unlisted. |
| `content` | RichText | CKEditor 5 HTML content. |
| `reading_time_sec` | Integer | Automatically calculated word-count based estimate. |

### 3. `medias.Media`
Centralized asset registry.
- `storage_key`: The path in the storage backend (Local/S3).
- `type`: `image`, `video`, `file`, `audio`.
- `width` / `height`: Metadata extracted from images.

### 4. `interactions.Comment`
- `parent`: Self-referential FK for nested threads.
- `status`: Moderation state (Pending, Approved, Rejected).

---

## Custom Managers & QuerySets

### `PostManager.published()`
Filters posts where `status='published'` and optimized with `select_related` on author and category to avoid N+1 query issues.

### `PostManager.get_queryset()`
Automatically annotates posts with `comments_count` and `likes_count` using Django's `Coalesce` and `Count`.

---

## Relationships & Constraints
- **One-to-One:** `AuthorProfile` → `User` (Shared primary key).
- **Many-to-Many:** `Post` ↔ `Tag` (via `PostTag` through model).
- **Generic Relation:** `Reaction` can link to any model using `content_type` and `object_id`.
- **Unique Together:**
    - `Reaction`: `user`, `content_type`, `object_id`, `reaction` (Prevents duplicate reactions).
    - `PostTag`: `post`, `tag`.
    - `PostMedia`: `post`, `media`, `attachment_type`.

---

## Business Rules
1. **Reading Time:** Calculated in `Post.save()` based on word count (approx. 200 words/min).
2. **Slug Uniqueness:** Slugs are unique and immutable once published to preserve SEO.
3. **Media Sync:** Automated cleanup of orphaned content-media links.
