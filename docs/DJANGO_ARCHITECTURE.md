# Django Architecture Documentation

This section details the internal architecture of the Blog Platform, focusing on Django-specific configurations and patterns.

---

## Settings Architecture
The settings are centralized in `blog/settings.py`. Key architectural decisions include:
- **Dynamic Database Selection:** Automatically switches between SQLite (for local/test) and PostgreSQL (for production/docker).
- **Environment-Driven Configuration:** Uses `python-dotenv` to load secrets and toggles.
- **Bilingual Documentation Standards:** All settings include bilingual comments (EN/FA) explaining their business and technical rationale.

---

## URL Architecture
The project uses a hierarchical routing system:
1. **Root (`blog/urls.py`):** Includes third-party routes (Djoser, Admin, Spectacular) and prefixes all app routes with `api/`.
2. **App-Level URLs:** Use `DefaultRouter` for ViewSets and explicit paths for specialized actions (e.g., `google-login`).

---

## Middleware Stack

| Middleware | Purpose |
| :--- | :--- |
| `SecurityMiddleware` | Handles HSTS, XSS-Filter, and Content-Type sniffing. |
| `WhiteNoiseMiddleware` | Efficiently serves static files directly from the Django process. |
| `CorsMiddleware` | Manages Cross-Origin Resource Sharing. |
| `LocaleMiddleware` | Handles internationalization and language selection. |
| `AxesMiddleware` | Brute-force protection; tracks login attempts and locks out suspicious IPs/Usernames. |
| `HistoryRequestMiddleware` | Provided by `django-simple-history` to track "Who changed what". |

---

## Authentication Architecture
The system supports multiple authentication flows managed by DRF and Djoser:
- **Static API Key:** Primary method for API access. A fixed key is expected in the `X-API-Key` header.
- **Social Auth:** Handled via a custom `GoogleLoginView` that validates Google ID Tokens and exchanges them for local access.
- **Staff Auth:** Uses `CustomTokenObtainPairView` for administrative access.
- **Session Auth:** Used exclusively for the Unfold Admin Panel.

---

## Permissions Architecture
A hybrid permission model is used:
- **Global Permissions:** `IsAuthenticated`, `IsAdminUser`.
- **Custom Logic:**
    - `IsOwnerOrAdmin`: Allows the creator or an administrator to modify an object.
    - `IsAuthorOrAdminOrReadOnly`: Restricts write operations to authors or admins while allowing public reads.
- **Object-Level Permissions:** Integrated with `django-guardian` for granular control if needed.

---

## Signals
Signals are used for decoupled side effects:
- **`user_post_save` / `user_post_delete`:** Automatically invalidates user-specific dashboard caches.
- **`sync_post_media`:** Triggered during `Post.save()` to ensure media attachments match the HTML content.

---

## Reusable Mixins
- **`DynamicFieldsMixin`:** Allows clients to specify exactly which fields they want in the response via the `?fields=` query parameter.
- **`ContentNormalizationMixin`:** Ensures consistent text formatting (e.g., Persian character normalization) across all content.

---

## Management Commands

| Command | Purpose | Usage |
| :--- | :--- | :--- |
| `create_random_posts` | Seeds the database with dummy data for UI testing. | `python manage.py create_random_posts` |
