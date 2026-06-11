# Backend Integration Analysis & Documentation

## Architecture Overview

### Modules
*   **users:** Authentication (JWT, Google OAuth2), Profile management.
*   **posts:** Blog posts, categories, tags, series, revisions.
*   **medias:** Centralized media management, image optimization, file attachments.
*   **interactions:** Comments and Reactions (Generic Foreign Keys).
*   **pages:** Static content management.
*   **navigation:** Dynamic menus and menu items.
*   **core:** Base models and shared core logic.
*   **common:** Standardized responses, exceptions, pagination, and utility functions.

### Components
*   **Controllers (Views):** DRF ViewSets and APIViews for all modules.
*   **Services:** Business logic encapsulated in `services.py` within each app.
*   **Repositories:** Django ORM models.
*   **Middleware:** Authentication, Axes (rate limiting/lockout), Silk (profiling), CORS.
*   **Background Jobs:** Celery tasks for media optimization, scheduled publishing, and notifications.
*   **External APIs:** Google OAuth2, SMS.ir (simulated in services).
*   **Authentication:** JWT tokens via `rest_framework_simplejwt`.

## Integration Boundaries

### Application ↔ Database
*   **CRUD:** Standard model operations.
*   **Relationships:** Many-to-Many (Post-Tag), One-to-One (User-AuthorProfile), Foreign Keys, Generic Foreign Keys (Reaction).
*   **Transactions:** Service layer usage of `transaction.atomic`.

### Controller ↔ Service
*   Views delegate business logic to services (e.g., `PostViewSet.publish` -> `publish_post_service`).

### Service ↔ External APIs
*   `GoogleLoginView` interacts with Google's token verification.

### Service ↔ Message Broker (Celery)
*   `create_comment` service triggers `notify_author_on_new_comment` task.
*   `sync_post_media` (triggered on Post save) handles media associations.
*   `publish_scheduled_posts` task runs on a schedule.

---

## Module-Specific Integration Documentation

### 1. Authentication (Users Module)
*   **Integration Scope:** `users.views.UserViewSet`, `users.views.CustomTokenObtainPairView`, `SimpleJWT`, `users.views.GoogleLoginView`.
*   **Test Scenarios:**
    *   User Registration: Valid and invalid payloads.
    *   JWT Login: Username/Password authentication.
    *   Token Refresh: Obtaining new access tokens.
    *   Google OAuth2 Login: Mocked token verification.
*   **Test Implementation:** `tests/integration/test_auth_flow.py`
*   **Test Data Setup:** `UserFactory` for existing users.
*   **Environment Requirements:** Database.
*   **Coverage Report:** Covers registration, JWT, and Google OAuth2 flows.
*   **Risks:** Google API changes or transport errors.

### 2. Posts & Medias Module
*   **Integration Scope:** `posts.views.PostViewSet`, `posts.services.sync_post_media`, `posts.services.publish_scheduled_posts`, `medias.models.Media`.
*   **Test Scenarios:**
    *   Create Post with embedded images in HTML -> Auto-sync `PostMedia` attachments.
    *   Scheduled post publishing lifecycle.
    *   Post creation with cover and OG images.
*   **Test Implementation:** `tests/integration/test_post_lifecycle.py`
*   **Test Data Setup:** `AuthorProfileFactory`, `MediaFactory`, `PostFactory`.
*   **Environment Requirements:** Database, Media storage (default_storage).
*   **Coverage Report:** Covers post-media association logic and scheduling service.
*   **Risks:** Regex-based media parsing from HTML might miss edge cases.

### 3. Interactions Module
*   **Integration Scope:** `interactions.views.CommentViewSet`, `interactions.views.ReactionViewSet`, `interactions.tasks.notify_author_on_new_comment`.
*   **Test Scenarios:**
    *   Post comment and verify author notification task trigger.
    *   Nested replies structure.
    *   Toggle reaction on Posts and Comments.
    *   Prevent duplicate reactions (UniqueTogether).
*   **Test Implementation:** `tests/integration/test_engagement_flow.py`
*   **Test Data Setup:** `PostFactory`, `CommentFactory`, `UserFactory`.
*   **Environment Requirements:** Database, Celery (mocked in tests).
*   **Coverage Report:** 100% of core engagement flows.
*   **Risks:** High concurrency on reaction counts (mitigated by Django F expressions).

### 4. Pages & Navigation Module
*   **Integration Scope:** `pages.views.PageViewSet`, `navigation.views.MenuViewSet`.
*   **Test Scenarios:**
    *   Admin-only page creation and guest-accessible listing.
    *   Dynamic menu structure retrieval.
    *   Permission checks for static content.
*   **Test Implementation:** `tests/integration/test_pages_navigation.py`
*   **Test Data Setup:** `PageFactory`, `MenuFactory`, `MenuItemFactory`.
*   **Environment Requirements:** Database.
*   **Coverage Report:** Covers basic CMS and navigation functionality.
*   **Risks:** Large menu structures affecting performance.

### 5. System-wide (Common Module)
*   **Integration Scope:** `common.renderers.StandardResponseRenderer`, `common.exceptions.custom_exception_handler`.
*   **Test Scenarios:**
    *   List and Detail responses standardization.
    *   Global 404, 401/403, and 400 error formatting.
*   **Test Implementation:** `tests/integration/test_system_wide.py`
*   **Coverage Report:** Validates global API consistency.
*   **Risks:** Third-party app responses might bypass standardized renderers.
