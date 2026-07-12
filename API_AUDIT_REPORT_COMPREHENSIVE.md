# API Authentication & Access Control Audit Report

## 1. Executive Summary
A comprehensive security and access control audit of the Blog Platform API was performed. This audit covers all exposed Django Rest Framework (DRF) viewsets, custom API views, function-based views, middleware integration, authentication backends, and permission classes.

The main purpose of this audit is to:
- Identify all exposed API routes and their HTTP methods.
- Document the current authentication mechanisms and permission requirements for each endpoint.
- Define client usage (who consumes each API and for what purpose).
- Provide structural recommendations for security hardening, risk mitigation, and access standardisation.

### Current System Architecture context
- **Primary Authentication:** JSON Web Token (JWT) using `rest_framework_simplejwt`.
- **Alternative/Development Authentication:** `StaticAPIKeyAuthentication` which intercepts the `X-API-Key` header and maps it to a superuser or a specific user configured via `X-Test-User`.
- **Response Format:** Custom standard renderer `StandardResponseRenderer` and exception handler `custom_exception_handler` wrap all responses inside an envelope containing `data`, `pagination`, and `messagesList`.
- **Internal Integration:** Daphne is the ASGI server, Celery runs the background tasks, and Nginx acts as the reverse proxy.

---

## 2. Audit Metrics & Summary Statistics
- **Total Paths Discovered:** 47
- **Total Unique Endpoint Operations (Method + Path):** 95
- **Public APIs (No Authentication Required):** 43
- **User Protected APIs (Requires Registered/Authenticated User):** 24
- **Admin Protected APIs (Requires Staff/Superuser Status):** 26
- **Internal APIs (Admin/CMS System Integrations):** 2
- **APIs with Unclear Access Rules:** 0 (All identified APIs have explicitly defined permissions via view classes, serializer methods, or queryset filters).
- **Security Concerns Found:** 4 (See Section 5 for deep-dive details).

*Note: Some endpoints exhibit dynamic/overridden behavior depending on the HTTP method or user role (e.g., standard listing is public, while create/update operations are restricted). These are counted separately under each respective category to show accurate granularity.*

---

## 3. Core Authentication & Authorization Components

### 3.1 Authentication Classes
Configured globally in `blog/settings.py` under `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]`:
1. **`common.authentication.StaticAPIKeyAuthentication`**
   - **Header:** `X-API-Key` (required) & `X-Test-User` (optional, for testing).
   - **Mechanism:** Validates against the `STATIC_API_KEY` environment variable. If matched, it logs in as the username passed in `X-Test-User` or falls back to the first superuser.
2. **`rest_framework_simplejwt.authentication.JWTAuthentication`**
   - **Header:** `Authorization: Bearer <token>`
   - **Mechanism:** Standard JWT Bearer token authentication.

### 3.2 Authorization / Permission Classes
Defined across `common/permissions.py` and `users/permissions.py`:
- **`AllowAny`**: Completely open access to all visitors.
- **`IsAuthenticated`**: Denies access to unauthenticated requests.
- **`IsAuthenticatedOrReadOnly`**: Safe methods (`GET`, `HEAD`, `OPTIONS`) are open; writing requires authentication.
- **`IsAdminUser`**: Restricts access solely to staff members (`is_staff=True`).
- **`IsAdminUserOrReadOnly`**: Open read access (`GET`); writing is strictly restricted to staff users.
- **`IsAuthorOrAdminOrReadOnly`**:
  - Safe methods allowed for everyone.
  - Write methods require the user to be staff (`is_staff`) or have an associated `AuthorProfile`.
  - Object-level updates/deletes require the user to be the author or staff.
- **`IsOwnerOrReadOnly`**: Safe methods allowed for everyone. Write operations allowed only if the user is the owner of the object (`user`, `author`, or `uploaded_by`).
- **`IsOwnerOrAdmin`**: Safe methods allowed for everyone. Write operations allowed for owners or staff.

---

## 4. Comprehensive API Inventory and Recommendations

### 4.1 Token & Auth Endpoints
| Method | Endpoint | Module / Feature | Current Auth | Current Permission Rules | Required Headers | Response Purpose | Recommended Auth | Recommendation Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/api/token/` | Auth / JWT | None | `AllowAny` | None | Obtain access & refresh token pair | **Public** | Necessary for initial authentication. |
| **POST** | `/api/token/refresh/` | Auth / JWT | None | `AllowAny` | None | Renew expired access token | **Public** | Essential for maintaining session lifecycle. |
| **POST** | `/api/auth/admin-login/` | Auth / Custom | None | `AllowAny` | None | Specialized admin JWT token generation | **Public** | Required for administrative CMS login forms. |

### 4.2 Users Module (`/api/users/`)
- **Consuming Client:** Public website visitors (registration), registered users (profile management), administrators (user directory).
- **Current Behavior:** `UserViewSet` restricts non-staff in `get_queryset` so they only see themselves.

| Method | Endpoint | Module / Feature | Current Auth | Current Permission Rules | Required Headers | Response Purpose | Recommended Auth | Recommendation Reason & Security Risks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/api/users/` | Users | None | `AllowAny` | None | Register a new user | **Public** | Public registration must remain open unless invitation-only. Rate limiting should be added. |
| **GET** | `/api/users/` | Users | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | List all users | **Admin Protected** | Listing all users should be strictly limited to staff to prevent username/email enumeration. |
| **GET** | `/api/users/{id}/` | Users | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Get profile details | **User Protected** | Allowed for self and admins. Public profiles can be exposed via author profiles instead. |
| **PUT** | `/api/users/{id}/` | Users | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Replace profile details | **User Protected** | Restrict edits strictly to owners or admin staff. |
| **PATCH**| `/api/users/{id}/` | Users | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Update profile details | **User Protected** | Prevent unauthorized modifications. |
| **DELETE**| `/api/users/{id}/`| Users | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Delete user account | **Admin Protected**| Account deletion should either be self-deactivation (User) or deletion (Admin). |
| **GET** | `/api/users/me/` | Users | JWT / API Key | `IsAuthenticated` | `Authorization` or `X-API-Key` | Retrieve active session details | **User Protected** | Context-specific endpoint for logged-in user dashboard. |

---

### 4.3 Articles, Comments & CMS Features (`/api/articles/`)
- **Consuming Client:** Public visitor frontend, writer dashboard, publisher CMS panel.

| Method | Endpoint | Module / Feature | Current Auth | Current Permission Rules | Required Headers | Response Purpose | Recommended Auth | Recommendation Reason & Security Risks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/api/articles/` | Articles | None | `IsAuthenticatedOrReadOnly` | None | List blog articles | **Public** | Visitors must read posts. Backend filters draft/scheduled posts. |
| **POST** | `/api/articles/` | Articles | JWT / API Key | `IsAuthorOrAdminOrReadOnly` | `Authorization` or `X-API-Key` | Create a draft article | **User Protected** | Restricted to users with `AuthorProfile` or `is_staff`. |
| **GET** | `/api/articles/{slug}/` | Articles | None | `IsAuthenticatedOrReadOnly` | None | Read single article | **Public** | Increments view count. Handled properly by visibility filters. |
| **PUT** | `/api/articles/{slug}/` | Articles | JWT / API Key | `IsAuthorOrAdminOrReadOnly` | `Authorization` or `X-API-Key` | Update article | **User Protected** | Restricted to original author or admin staff. |
| **PATCH**| `/api/articles/{slug}/` | Articles | JWT / API Key | `IsAuthorOrAdminOrReadOnly` | `Authorization` or `X-API-Key` | Partially edit article | **User Protected** | Restricted to original author or admin staff. |
| **DELETE**| `/api/articles/{slug}/`| Articles | JWT / API Key | `IsAuthorOrAdminOrReadOnly` | `Authorization` or `X-API-Key` | Delete article | **Admin Protected**| Hard deletions should be restricted to admins; authors should use "archived" status. |
| **POST** | `/api/articles/{slug}/publish/` | Articles | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Publish draft/scheduled article | **User Protected** | restricted to original author or admin staff. |
| **GET** | `/api/articles/{slug}/related/` | Articles | None | `AllowAny` | None | Fetch related posts by tags | **Public** | Used for recommended content widget. |
| **GET** | `/api/articles/{slug}/similar/` | Articles | None | `AllowAny` | None | Fetch similar posts in category | **Public** | Used for sidebar recommendations. |
| **GET** | `/api/articles/{slug}/same-category/` | Articles | None | `AllowAny` | None | Fetch paginated same category posts | **Public** | Used for bottom slider feed. |
| **GET** | `/api/articles/slug/{slug}/` | Articles | None | `AllowAny` | None | Fetch post details by localized slug | **Public** | Vital public SEO endpoint. |
| **GET** | `/api/articles/{article_slug}/comments/` | Articles | None | `IsAuthenticatedOrReadOnly` | None | List approved comments | **Public** | Reading post discussions should remain open to everyone. |
| **GET** | `/api/articles/{article_slug}/comments/{id}/` | Articles | None | `IsAuthenticatedOrReadOnly` | None | Retrieve specific comment | **Public** | Public read-only view of a comment. |

---

### 4.4 Authors, Categories, Tags & Series
- **Consuming Client:** Public visitors, administration dashboard.

| Method | Endpoint | Module / Feature | Current Auth | Current Permission Rules | Required Headers | Response Purpose | Recommended Auth | Recommendation Reason & Security Risks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/api/authors/` | Authors | None | `IsAuthenticatedOrReadOnly` | None | List author profiles | **Public** | Public directory of team authors/contributors. |
| **POST** | `/api/authors/` | Authors | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Create author profile | **Admin Protected** | Standard users should not be allowed to elevate themselves to authors arbitrarily. |
| **GET** | `/api/authors/{user}/` | Authors | None | `IsAuthenticatedOrReadOnly` | None | Get specific author details | **Public** | Public author biography display. |
| **PUT/PATCH**| `/api/authors/{user}/` | Authors | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Update author bio/details | **User Protected** | Restrict to profile owner or staff. |
| **DELETE**| `/api/authors/{user}/`| Authors | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Delete author profile | **Admin Protected**| Restrict to admins. |
| **GET** | `/api/categories/` | Categories | None | `IsAdminUserOrReadOnly` | None | List categories | **Public** | Required for frontend site navigation. |
| **POST/PUT/PATCH/DELETE** | `/api/categories/` (and subpaths) | Categories | JWT / API Key | `IsAdminUserOrReadOnly` | `Authorization` or `X-API-Key` | Manage categories | **Admin Protected**| Modifying classification taxonomy is strictly an admin feature. |
| **GET** | `/api/tags/` | Tags | None | `IsAdminUserOrReadOnly` | None | List tags | **Public** | Required for post tagging UI on frontend. |
| **POST/PUT/PATCH/DELETE** | `/api/tags/` (and subpaths) | Tags | JWT / API Key | `IsAdminUserOrReadOnly` | `Authorization` or `X-API-Key` | Manage tags | **Admin Protected**| Restricts brand tag pollution. |
| **GET** | `/api/series/` | Series | None | `IsAdminUserOrReadOnly` | None | List series | **Public** | Used for grouped posts list. |
| **POST/PUT/PATCH/DELETE** | `/api/series/` (and subpaths) | Series | JWT / API Key | `IsAdminUserOrReadOnly` | `Authorization` or `X-API-Key` | Manage series | **Admin Protected**| Group management should remain administrative. |

---

### 4.5 Revisions, Podcasts & Gallery Items
- **Consuming Client:** Public visitors, editors, admins.

| Method | Endpoint | Module / Feature | Current Auth | Current Permission Rules | Required Headers | Response Purpose | Recommended Auth | Recommendation Reason & Security Risks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/api/revisions/` | Revisions | None | `IsAuthenticatedOrReadOnly` | None | List post revision logs | **Admin Protected**| **Security Concern:** Revisions contain internal drafting logs, confidential edits, and deleted blocks. Safe methods are currently open to the public, which is a major data leak risk. |
| **POST** | `/api/revisions/` | Revisions | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Create revision | **User Protected** | Allowed for authors and admins. |
| **GET** | `/api/revisions/{id}/` | Revisions | None | `IsAuthenticatedOrReadOnly` | None | View revision diff details | **Admin Protected**| **Security Concern:** Same leakage risks as above. Should require admin access. |
| **PUT/PATCH/DELETE** | `/api/revisions/{id}/` | Revisions | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Manage revisions | **Admin Protected**| Editing history is highly sensitive. |
| **GET** | `/api/podcast-categories/` | Podcasts | None | `IsAdminUserOrReadOnly` | None | List podcast categories | **Public** | Required for frontend navigation. |
| **POST/PUT/PATCH/DELETE** | `/api/podcast-categories/{id}/` | Podcasts | JWT / API Key | `IsAdminUserOrReadOnly` | `Authorization` or `X-API-Key` | Manage podcast categories | **Admin Protected**| Restricted to staff. |
| **GET** | `/api/podcasts/` | Podcasts | None | `IsAdminUserOrReadOnly` | None | List podcast episodes | **Public** | Feed for visitor audio streaming. |
| **GET** | `/api/podcasts/{slug}/` | Podcasts | None | `IsAdminUserOrReadOnly` | None | Listen to single episode | **Public** | Streaming view + counts tracking. |
| **POST/PUT/PATCH/DELETE** | `/api/podcasts/` (and subpaths) | Podcasts | JWT / API Key | `IsAdminUserOrReadOnly` | `Authorization` or `X-API-Key` | Manage podcasts | **Admin Protected**| Episode publishing and file uploads. |
| **GET** | `/api/gallery/` | Gallery | None | `IsAdminUserOrReadOnly` | None | Fetch gallery items | **Public** | Feed of pictures for front page slider. |
| **POST/PUT/PATCH/DELETE** | `/api/gallery/` (and subpaths) | Gallery | JWT / API Key | `IsAdminUserOrReadOnly` | `Authorization` or `X-API-Key` | Manage gallery items | **Admin Protected**| Managing slide carousel items. |

---

### 4.6 Media Library (`/api/media/`)
- **Consuming Client:** Registered editors/authors uploading assets, public streaming.

| Method | Endpoint | Module / Feature | Current Auth | Current Permission Rules | Required Headers | Response Purpose | Recommended Auth | Recommendation Reason & Security Risks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/api/media/` | Media Library | None | `IsAuthenticatedOrReadOnly` | None | List uploaded assets | **Admin Protected**| **Security Concern:** Any visitor can list all uploads in the media library. This allows discovery of private attachments, draft images, and resource harvesting. |
| **POST** | `/api/media/` | Media Library | JWT / API Key | `IsAuthenticatedOrReadOnly` | `Authorization` or `X-API-Key` | Upload file | **User Protected** | Safe writes restricted to authenticated users. |
| **GET** | `/api/media/{id}/` | Media Library | None | `IsAuthenticatedOrReadOnly` | None | Retrieve file details | **User Protected** | Reading metadata of media assets should be restricted to authenticated accounts. |
| **PUT/PATCH**| `/api/media/{id}/` | Media Library | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Edit file details | **User Protected** | Restricted to uploader or staff. |
| **DELETE**| `/api/media/{id}/`| Media Library | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Delete file | **Admin Protected**| Restricts deletion of site assets to staff. |
| **GET** | `/api/media/{media_id}/download/` | Media Library | None | Public Django View | None | Download physical asset file | **Public** | Direct file download endpoint. Throttling is highly recommended to prevent DoS. |

---

### 4.7 Comments, Reactions, Static Pages & Navigation Menu
- **Consuming Client:** Interactive widgets, public visitor frontend, site administration.

| Method | Endpoint | Module / Feature | Current Auth | Current Permission Rules | Required Headers | Response Purpose | Recommended Auth | Recommendation Reason & Security Risks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/api/comments/` | Interactions | None | `IsAuthenticatedOrReadOnly` | None | List comments globally | **Public** | Public visitor reviews stream. |
| **POST** | `/api/comments/` | Interactions | JWT / API Key | `IsAuthenticatedOrReadOnly` | `Authorization` or `X-API-Key` | Create a comment | **User Protected** | Requires authenticated user (associated uploader account). |
| **GET** | `/api/comments/{id}/` | Interactions | None | `IsAuthenticatedOrReadOnly` | None | View comment | **Public** | Public details of a comment. |
| **PUT/PATCH**| `/api/comments/{id}/` | Interactions | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Edit comment content | **User Protected** | Only the original author or admin can edit comments. |
| **DELETE**| `/api/comments/{id}/`| Interactions | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Delete comment | **User Protected** | Only owner or admin. |
| **GET** | `/api/reactions/` | Interactions | JWT / API Key | `IsAuthenticated` | `Authorization` or `X-API-Key` | List reactions | **User Protected** | Filtered to show own reactions (staff see all). |
| **POST** | `/api/reactions/` | Interactions | JWT / API Key | `IsAuthenticated` | `Authorization` or `X-API-Key` | React to item (like, etc) | **User Protected** | Must be authenticated to vote/like content. |
| **GET** | `/api/reactions/{id}/` | Interactions | JWT / API Key | `IsAuthenticated` | `Authorization` or `X-API-Key` | Get reaction details | **User Protected** | Restricted to own reaction. |
| **PUT/PATCH/DELETE** | `/api/reactions/{id}/` | Interactions | JWT / API Key | `IsOwnerOrAdmin` | `Authorization` or `X-API-Key` | Modify/Remove reaction | **User Protected** | Restrict strictly to uploader or admin. |
| **GET** | `/api/pages/` | Pages | None | `IsAdminUserOrReadOnly` | None | List static pages | **Public** | Displays page options (About Us, etc.). |
| **POST/PUT/PATCH/DELETE** | `/api/pages/` (and subpaths) | Pages | JWT / API Key | `IsAdminUserOrReadOnly` | `Authorization` or `X-API-Key` | Manage pages | **Admin Protected**| Restrict page management to admins. |
| **GET** | `/api/menus/` | Navigation | None | `IsAdminUserOrReadOnly` | None | Fetch site menus | **Public** | Renders header/footer menus. |
| **POST/PUT/PATCH/DELETE** | `/api/menus/` (and subpaths) | Navigation | JWT / API Key | `IsAdminUserOrReadOnly` | `Authorization` or `X-API-Key` | Manage menus | **Admin Protected**| Menu building is strictly administrative. |
| **GET** | `/api/menu-items/` | Navigation | None | `IsAdminUserOrReadOnly` | None | List individual menu links | **Public** | Frontend renders tree structures. |
| **POST/PUT/PATCH/DELETE** | `/api/menu-items/` (and subpaths) | Navigation | JWT / API Key | `IsAdminUserOrReadOnly` | `Authorization` or `X-API-Key` | Manage menu links | **Admin Protected**| Restricted to admins. |

---

### 4.8 System Integrations & CKEditor
- **Consuming Client:** Administration dashboard and richer rich-text editors during post creations.

| Method | Endpoint | Module / Feature | Current Auth | Current Permission Rules | Required Headers | Response Purpose | Recommended Auth | Recommendation Reason & Security Risks |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/api/editor/upload/` | System / Rich Text | Session / CSRF | Custom check (`login_required` + is staff/author) | Session Cookie, CSRF token | CKEditor 5 image uploader backend | **Internal / CMS** | Handles content generation. Requires logged-in writers and is properly configured. |
| **POST** | `/ckeditor5/image_upload/` | System / Rich Text | Session | `ckeditor5_upload` (is_staff check) | Session Cookie | CKEditor 5 upload fallback | **Internal / CMS** | Restricts upload of image assets to staff. |
| **GET** | `/sitemap.xml` | SEO | None | None | None | Generate Sitemap XML structure | **Public** | Required for indexing search engines (Googlebot, Bing). |

---

## 5. Security Concerns & Vulnerabilities Discovered

### 5.1 Public Listing of Private Revisions (`/api/revisions/`)
- **Severity: High**
- **Issue:** The list and retrieve methods for article revisions use `IsAuthenticatedOrReadOnly`. This means that any anonymous, unauthenticated visitor can call `GET /api/revisions/` and read full revision diffs, change logs, and historical edits.
- **Risk:** Sensitive unpublished text, comments between editors, or private content can be leaked.
- **Recommendation:** Change permission to `IsAdminUser` or restrict access dynamically based on article status.

### 5.2 Public Listing of Media Assets (`/api/media/`)
- **Severity: Medium**
- **Issue:** The list method for media files allows unauthenticated visitors (`IsAuthenticatedOrReadOnly`) to discover all uploaded assets.
- **Risk:** Resource harvesting, downloading of confidential attachments, and leaking of draft media content.
- **Recommendation:** Restrict `GET /api/media/` list endpoint to `IsAdminUser` so only administrative CMS panels can view the library catalog, while keeping download files direct.

### 5.3 Static API Key Authentication Default Override Behavior (`StaticAPIKeyAuthentication`)
- **Severity: Low**
- **Issue:** If the `X-API-Key` matches the `STATIC_API_KEY` but no `X-Test-User` header is specified, the system logs in as the **first superuser** in the database.
- **Risk:** If a static API key is leaked or compromised, an attacker gains full superuser privileges automatically.
- **Recommendation:** In production systems, disable `StaticAPIKeyAuthentication` or restrict it to read-only API access without superuser fallback.

### 5.4 Brute Force on Sensitive Auth Endpoints
- **Severity: Low**
- **Issue:** The authentication token endpoints do not currently have DRF rate limits (throttling) applied.
- **Risk:** Susceptibility to password spraying or automated brute-forcing.
- **Recommendation:** Implement `rest_framework.throttling` (e.g., `ScopedRateThrottle` or `UserRateThrottle`) on `/api/token/` and `/api/auth/admin-login/`.

---

## 6. Blog-Specific Access Rules Summary

### 6.1 Public Content Access Control
The following core blog features should **remain public**:
- Articles search, list, detail (using visibility filters).
- Podcast listings, stream.
- Category catalog, Tag clouds, Navigation menus.
- Gallery sliders.
- Sitemap, static pages, and RSS feeds.

*Security measure applied:* These endpoints must never expose unpublished or scheduled posts. The querysets must keep filtering by `status="published"` and `published_at__lte=timezone.now()`.

### 6.2 Registered User Access Control
The following widgets require **active user account authentication**:
- Writing comments (`POST /api/comments/`).
- Managing own reactions (`GET/POST /api/reactions/`).
- Getting own session information (`GET /api/users/me/`).

### 6.3 Admin & Staff Access Control
All CRUD capabilities across taxonomies and content must be locked to **authenticated staff**:
- Article creation, publishing (`/api/articles/{slug}/publish/`), updates, deletions.
- Category management, Tag control, Navigation building.
- Media inventory browsing.
- User accounts moderation.
- Post Revision logs.

---

## 7. Standard API Access Control Matrix

Below is the structured overview of all APIs mapping their current and recommended configuration.

| Method | Endpoint | Purpose | Current Auth | Recommended Auth | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/api/token/` | Obtain JWT token pair | Public | Public | Standard authentication gateway. |
| **POST** | `/api/token/refresh/` | Renew JWT access token | Public | Public | Token lifecycle management. |
| **POST** | `/api/auth/admin-login/` | Admin specific JWT generation | Public | Public | Secure portal access authentication. |
| **POST** | `/api/users/` | Public user registration | Public | Public | Enables self-registration. |
| **GET** | `/api/users/` | Directory of users | User/Admin Protected | Admin Protected | Prevent email and username enumeration. |
| **GET** | `/api/users/{id}/` | View user profile details | User/Admin Protected | User Protected | Restrict private profile access. |
| **PUT/PATCH**| `/api/users/{id}/` | Modify user profile | User/Admin Protected | User Protected | Restrict updates to profile owner. |
| **DELETE**| `/api/users/{id}/` | Remove user account | User/Admin Protected | Admin Protected | Controlled user deletion. |
| **GET** | `/api/users/me/` | Get current active user profile | User Protected | User Protected | Returns contextual self-profile. |
| **GET** | `/api/articles/` | List published articles | Public | Public | Frontend content delivery. |
| **POST** | `/api/articles/` | Create a draft article | User Protected | User Protected | Writing restricted to authorized authors. |
| **GET** | `/api/articles/{slug}/` | View full article content | Public | Public | Frontend article delivery. |
| **PUT/PATCH**| `/api/articles/{slug}/` | Edit article content | User Protected | User Protected | Allowed only for author/editor. |
| **DELETE**| `/api/articles/{slug}/` | Remove article from database | User Protected | Admin Protected | Hard deletion limited to admins. |
| **POST** | `/api/articles/{slug}/publish/` | Manually publish draft | User Protected | User Protected | Author/Editor publishing control. |
| **GET** | `/api/articles/{slug}/related/` | Fetch similar tagged posts | Public | Public | Enhances visitor recommendation feed. |
| **GET** | `/api/articles/{slug}/similar/` | Fetch similar categorized posts | Public | Public | Enhances sidebar recommendation feed. |
| **GET** | `/api/articles/{slug}/same-category/` | Paginated category feed | Public | Public | Dynamic content slider rendering. |
| **GET** | `/api/articles/slug/{slug}/` | Fetch article by localized slug | Public | Public | Direct SEO navigation. |
| **GET** | `/api/articles/{article_slug}/comments/` | List comments for an article | Public | Public | Facilitates public discussions. |
| **GET** | `/api/articles/{article_slug}/comments/{id}/` | Retrieve single comment details | Public | Public | Public comment viewing. |
| **GET** | `/api/authors/` | List active writers profiles | Public | Public | Contributor directory. |
| **POST** | `/api/authors/` | Register new team author profile | User/Admin Protected | Admin Protected | Only staff can register official authors. |
| **GET** | `/api/authors/{user}/` | Retrieve author profile details | Public | Public | Contributor landing page bio. |
| **PUT/PATCH**| `/api/authors/{user}/` | Edit writer description | User/Admin Protected | User Protected | Profile owner self-service biography. |
| **DELETE**| `/api/authors/{user}/` | Remove author profile record | User/Admin Protected | Admin Protected | Managed staff roster. |
| **GET** | `/api/categories/` | List available classifications | Public | Public | Taxonomy catalog mapping. |
| **POST/PUT/PATCH/DELETE**| `/api/categories/` | Manage taxonomic categories | Admin Protected | Admin Protected | Roster hierarchy control. |
| **GET** | `/api/tags/` | Fetch all metadata tags | Public | Public | Site search optimization labels. |
| **POST/PUT/PATCH/DELETE**| `/api/tags/` | Control tags database | Admin Protected | Admin Protected | Prevents duplicate taxonomy pollution. |
| **GET** | `/api/series/` | Fetch post sequences collections | Public | Public | Allows visitors to follow stories. |
| **POST/PUT/PATCH/DELETE**| `/api/series/` | Manage group collections | Admin Protected | Admin Protected | Sequence orchestration control. |
| **GET** | `/api/revisions/` | Browse revisions logs | Public | Admin Protected | **Major leak risk.** Should be admin-only. |
| **GET** | `/api/revisions/{id}/` | Read revision content changes | Public | Admin Protected | **Major leak risk.** Private text disclosure. |
| **POST/PUT/PATCH/DELETE**| `/api/revisions/` | Maintain article history logs | User Protected | Admin Protected | Sensitive drafting log actions. |
| **GET** | `/api/podcast-categories/` | Fetch podcast directories | Public | Public | Navigational categorization. |
| **POST/PUT/PATCH/DELETE**| `/api/podcast-categories/` | Podcast taxonomy directory management | Admin Protected | Admin Protected | Catalog setup control. |
| **GET** | `/api/podcasts/` | Listing audio content | Public | Public | Direct user streaming access. |
| **GET** | `/api/podcasts/{slug}/` | Get podcast episode details | Public | Public | Streams track information. |
| **POST/PUT/PATCH/DELETE**| `/api/podcasts/` | Publish new episode media | Admin Protected | Admin Protected | CMS episode scheduling. |
| **GET** | `/api/gallery/` | Fetch picture slides | Public | Public | Carousel homepage gallery. |
| **POST/PUT/PATCH/DELETE**| `/api/gallery/` | Manage homepage images slider | Admin Protected | Admin Protected | Curated landing pages design. |
| **GET** | `/api/media/` | List all uploaded files | Public | Admin Protected | **Information disclosure.** Restrict list access. |
| **POST** | `/api/media/` | Upload direct file assets | User Protected | User Protected | Enables post attachment uploading. |
| **GET** | `/api/media/{id}/` | Get media record properties | Public | User Protected | Metadata lookup. |
| **PUT/PATCH**| `/api/media/{id}/` | Modify media description/alt | User Protected | User Protected | Uploader-only descriptions editing. |
| **DELETE**| `/api/media/{id}/` | Delete server asset | User/Admin Protected | Admin Protected | Prevents broken links on the web. |
| **GET** | `/api/media/{media_id}/download/` | Fetch file binaries | Public | Public | Streaming access. Needs rate-limiting. |
| **GET** | `/api/comments/` | Global comments search | Public | Public | Blog reviews activity stream. |
| **POST** | `/api/comments/` | Post a feedback comment | User Protected | User Protected | Engagement requires user profile verification. |
| **GET** | `/api/comments/{id}/` | Retrieve feedback properties | Public | Public | Direct review URL access. |
| **PUT/PATCH**| `/api/comments/{id}/` | Self-edit feedback content | User/Admin Protected | User Protected | Restricted strictly to the commenter. |
| **DELETE**| `/api/comments/{id}/` | Remove feedback comment | User/Admin Protected | User Protected | Commenter deletion capability. |
| **GET/POST** | `/api/reactions/` | Maintain own reaction actions | User Protected | User Protected | Personalized likes tracking. |
| **GET** | `/api/reactions/{id}/` | Retrieve single vote properties | User Protected | User Protected | Personal session lookup. |
| **PUT/PATCH/DELETE**| `/api/reactions/{id}/` | Change reaction (like/dislike) | User Protected | User Protected | Revoke choice capacity. |
| **GET** | `/api/pages/` | List static text documents | Public | Public | Site layout guidelines (T&C, Privacy). |
| **POST/PUT/PATCH/DELETE**| `/api/pages/` | Manage static document contents | Admin Protected | Admin Protected | CMS text controller. |
| **GET** | `/api/menus/` | List navigational navigation sets | Public | Public | Framework layouts. |
| **POST/PUT/PATCH/DELETE**| `/api/menus/` | Orchestrate navigation sets | Admin Protected | Admin Protected | Admin layouts structural control. |
| **GET** | `/api/menu-items/` | Fetch tree sub-links listings | Public | Public | Layout nodes delivery. |
| **POST/PUT/PATCH/DELETE**| `/api/menu-items/` | Reorder navigation sub-links | Admin Protected | Admin Protected | Links management. |
| **POST** | `/api/editor/upload/` | Inline content creator uploader | User Protected | Internal / CMS | Integrated editor uploads handler. |
| **POST** | `/ckeditor5/image_upload/` | Administrative rich-text uploader | Admin Protected | Internal / CMS | Backend panel rich upload. |
| **GET** | `/sitemap.xml` | SEO Sitemap feed | Public | Public | Required search engine crawlers. |
