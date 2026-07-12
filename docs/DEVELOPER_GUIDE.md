# Developer Guide - Phase 2

Welcome to the Developer Guide for the Enterprise Blog Platform. This document provides an in-depth look at the internal architecture, development workflows, and maintenance procedures.

---

# SECTION 1 — CODE DOCUMENTATION

## Services Documentation

The service layer encapsulates the core business logic of the application, keeping models and views thin.

### Core Services

| Service | Responsibility | Dependencies |
| ------- | -------------- | ------------ |
| `articles.services.sync_post_media` | Synchronizes media attachments (cover, OG, in-content) for a article. | `medias.models.Media`, `Article` |
| `articles.services.publish_scheduled_posts` | Identifies and publishes articles whose scheduled time has passed. | `Article` |
| `articles.services.increment_post_view_count` | Asynchronously increments article views using F() expressions. | `Article` |
| `medias.services.create_media_from_file` | Handles file upload, metadata extraction, and metadata extraction. | `PIL`, `common.utils.images` |
| `interactions.services.create_comment` | Orchestrates comment creation and author notification. | `Comment`, `interactions.tasks` |
| `interactions.services.toggle_reaction` | Manages user reactions (likes) on any content object. | `ContentType`, `Reaction` |

### Detailed Service Descriptions

#### Media Optimization (`medias.services.create_media_from_file`)
- **Purpose:** Centralize media ingestion logic.
- **Inputs:** `uploaded_file`, `uploaded_by`, `alt_text`, `title`.
- **Outputs:** `Media` instance.
- **Business Rules:**  filenames are sanitized; metadata (dimensions) is extracted for images.

#### Article Synchronization (`articles.services.sync_post_media`)
- **Purpose:** Ensure all media referenced in a article (including HTML content) is tracked in the database.
- **Inputs:** `article` instance.
- **Business Rules:** Scans `<img>` tags in content; matches `MEDIA_URL` paths to `Media` storage keys; updates `Media` through model.

---

## Utilities Documentation

### Image Processing (`common/utils/images.py`)

### File Handling (`common/utils/files.py`)
- **`get_sanitized_filename(filename)`**: Uses `slugify` to clean filenames while preserving extensions.
- **`get_sanitized_upload_path(instance, filename)`**: Generates a UUID-based path to prevent collisions.

---

## Custom Managers Documentation

### `PostManager` (`articles.models.PostManager`)
- **Why it exists:** To centralize complex QuerySet optimizations and business filters.
- **Key Methods:**
  - `get_queryset()`: Automatically performs `select_related` on authors/categories and annotates `comments_count` and `likes_count`.
  - `published()`: Filters for articles with `status='published'` and valid publication dates.

---

## Mixins Documentation

### `FileChangeDetectionMixin` (`common/mixins.py`)
- **Purpose:** Tracks if a specific file field has been updated during a `save()` operation.
- **Usage:** Set `MONITORED_FILE_FIELD = 'field_name'`. Check `self.image_has_changed`.

### `DynamicFieldsMixin` (`common/mixins.py`)
- **Purpose:** Allows serializers to filter fields based on an optional `fields` argument.
- **Consumer:** Used by `PostListSerializer`.

---

## Validators Documentation

- **`validate_file`**: Enforces 10MB limit and specific extensions (jpg, png,  mp4, etc.).
- **`validate_sheba` / `validate_card_number`**: Iranian banking standards validation using regex.

---

## Signals Documentation

| Sender | Trigger | Side Effect |
| ------ | ------- | ----------- |
| `User` | `post_save` | Invalidates user dashboard cache (`dashboard:user:{id}`). |
| `User` | `post_delete` | Clears user dashboard cache. |

---

## Permissions Documentation

| Permission | Purpose | Used In |
| ---------- | ------- | ------- |
| `IsAuthorOrAdminOrReadOnly` | Allows safe methods to all; writes only to authors or staff. | `ArticleViewSet` |
| `IsOwnerOrAdmin` | Flexible ownership check (user, author, uploaded_by, etc.) or staff access. | `MediaViewSet`, `CommentViewSet`, `UserViewSet` |
| `IsAdminUserOrReadOnly` | Restricts writes to staff members. | `CategoryViewSet`, `TagViewSet`, `SeriesViewSet` |

---

## Serializers Documentation

### Response Standardization
The project uses a custom `StandardResponseRenderer` and `StandardizedAutoSchema` to ensure every API response follows this structure:
```json
{
  "data": ...,
  "pagination": { ... },
  "messagesList": []
}
```

### Key Serializers
- **`PostDetailSerializer`**: Includes `ContentNormalizationMixin` which converts HTML content to Markdown for frontend flexibility.
- **`JalaliDateTimeField`**: A read-only field that converts standard timestamps to Persian Jalali format.

---

## ViewSets Documentation

### `ArticleViewSet`
- **Purpose:** Main hub for article interactions.
- **Custom Actions:**
  - `similar`: Returns articles in the same category.
  - `by_slug`: Retrieves a article using its unique slug.
  - `publish_post` (Action/Decorator): Allows manual state transition from draft to published.
- **Logic:** Overrides `get_queryset` to handle visibility (Drafts only visible to authors; Published visible to all).

---

# SECTION 2 — DOCSTRING AUDIT

| File | Object | Status |
| ---- | ------ | ------ |
| `articles/services.py` | All functions | **Good** (Bilingual) |
| `medias/services.py` | All functions | **Good** (Bilingual) |
| `common/validators.py` | All functions | **Good** (Bilingual) |
| `*/tests/*.py` | Test Classes | **Missing/Weak** (English only) |
| `*/models.py` | Meta classes | **Missing** |

### Recommended Standard
All public methods and classes must use **Google Style Docstrings** with bilingual (EN/FA) descriptions.

---

# SECTION 3 — TESTING DOCUMENTATION

## Testing Strategy
- **Unit Tests (`app/tests/unit/`)**: Validate individual services, models, and validators in isolation.
- **Integration Tests (`tests/integration/`)**: Validate multi-app flows (e.g., Article Lifecycle, Auth Flow).

## Repository Test Map
| App | Unit Tests | Integration Coverage |
| --- | --- | --- |
| `users` | Auth, Profile, Signals | Auth Flow |
| `articles` | CRUD, Services, Tasks | Article Lifecycle |
| `medias` | Optimization, Storage | Article Lifecycle |
| `interactions`| Comments, Reactions | Engagement Flow |
| `pages` | Content, Meta | Navigation Flow |
| `navigation` | Menus, Items | Navigation Flow |

## Fixtures & Factories
The project uses **FactoryBoy** for generating test data.
- **Location**: `articles/factories.py` contains factories for all major models.
- **Usage Example**:
```python
from articles.factories import PostFactory
article = PostFactory(title="Test Article")
```
- **Mocking**: External services (like Google OAuth) are mocked using `unittest.mock` in `users/tests.py` and `tests/integration/`.

## Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app
python manage.py test articles

# With coverage
coverage run manage.py test
coverage report
```

## Coverage Documentation
| Component | Coverage Risk |
| --------- | ------------- |
| `users.auth_utils` | **Low** (Extensively tested in integration) |
| `articles.services` | **Low** (Covered by unit and integration) |
| `common.exceptions` | **Medium** (Standardized but needs more edge cases) |


---

# SECTION 4 — TROUBLESHOOTING GUIDE

| Issue | Symptoms | Resolution |
| ----- | -------- | ---------- |

| **N+1 Queries** | Slow listing endpoints. | Check `PostManager` and ensure `select_related`/`prefetch_related` are used. |
| **Migration Conflict** | `InconsistentMigrationHistory`. | The project removed `phonenumber_field`. Check `users/migrations` for CharField overrides. |

---

# SECTION 5 — DEVELOPMENT WORKFLOW

### Adding a New API Endpoint
1. Define business logic in `services.py`.
2. Create Serializer in `serializers.py` (inherit `DynamicFieldsMixin` if listing).
3. Create ViewSet in `views.py` (inherit `DynamicSerializerViewMixin`).
4. Register route in `urls.py`.
5. Add unit tests in `tests/unit/test_views.py`.

### Code Review Checklist
- [ ] **Security**: Are `permission_classes` correctly applied? Is `IsOwnerOrAdmin` used where appropriate?
- [ ] **Performance**: Are QuerySets optimized with `select_related` or `prefetch_related`? Any N+1 risks?
- [ ] **Testing**: Are there unit tests for the new service/logic?
- [ ] **Documentation**: Are bilingual docstrings (EN/FA) provided for all public symbols?
- [ ] **Maintainability**: Does the logic belong in a Service instead of a View/Model?

---

# SECTION 6 — CHANGELOG

- **v1.2.0**: Removed phone/OTP authentication; transitioned to CharField for `phone_number`.
- **v1.1.0**: Implemented bilingual documentation standard.
- **v1.0.0**: Initial release with core Blog, Media, and Interaction features.

---

# SECTION 7 — MAINTAINABILITY REPORT

### Technical Debt
- **Tight Coupling**: `Article.save()` directly calls `sync_post_media`. Consider using signals for better decoupling.
- **Large Modules**: `articles/views.py` is growing large; consider splitting into `views/` directory.

### Improvement Recommendations
- **High Priority**: Complete bilingual docstrings for all models.
- **Medium Priority**: Implement a soft-delete mechanism for Articles and Comments.
- **Low Priority**: Transition from `markdownify` to a dedicated Markdown field if HTML storage is no longer required.
