# Blog Platform API Documentation

This document provides a comprehensive guide to the Blog Platform API. Built with Django REST Framework (DRF), the API follows RESTful principles, uses JWT for authentication, and provides a standardized response format.

---

## 1. Global Standards

### Base URL
- **Production:** `https://api.yourdomain.com/api/`
- **Development:** `http://localhost:8000/api/`

### Standard Response Format
All successful (2xx) responses are wrapped in a standard JSON structure:

```json
{
  "data": { ... },
  "messagesList": [],
  "pagination": {
    "pageNo": 1,
    "pageSize": 10,
    "totalPage": 5,
    "totalCount": 48,
    "lastId": null
  }
}
```

*Note:*
- The `pagination` key is only present in list endpoints (e.g., `list`, `same_category`, `related_posts`).
- `messagesList` contains string messages for the user/developer.
- Errors (4xx/5xx) also follow a similar structure but without the `pagination` key.

### Authentication
The API uses **JWT (JSON Web Token)** authentication.
- Headers: `Authorization: Bearer <your_access_token>`

---

## 2. Global Query Parameters

Supported across most list endpoints:

- `fields`: Comma-separated list of fields to include (e.g., `?fields=slug,title,author`).
- `search`: Search term to filter results by text fields.
- `ordering`: Field to order by (prefix with `-` for descending, e.g., `?ordering=-published_at`).
- `page`: Page number for pagination.
- `page_size`: Number of items per page.

---

## 3. Authentication Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/token/` | Standard Login (returns `access` and `refresh`). |
| `POST` | `/api/token/refresh/` | Refresh access token using `refresh` token. |
| `POST` | `/api/auth/admin-login/` | Specialized login for administrative access. |
| `POST` | `/api/auth/google/login/` | Login via Google OAuth2 (requires `id_token`). |

---

## 4. User Management

| Method | Endpoint | Description | Permissions |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/users/` | List all users. | Staff Only |
| `POST` | `/api/users/` | Create a new user (Register). | Public |
| `GET` | `/api/users/me/` | Get current authenticated user profile. | Authenticated |
| `GET` | `/api/users/{id}/` | Retrieve a user profile. | Staff or Owner |
| `PATCH` | `/api/users/{id}/` | Update user profile. | Staff or Owner |

---

## 5. Blog Posts

### Core Post Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/posts/` | List posts. Supports `category`, `tags`, `is_hot`, `series`, `visibility` filters. |
| `POST` | `/api/posts/` | Create a new post. (Requires `AuthorProfile`). |
| `GET` | `/api/posts/{slug}/` | Retrieve detailed post information (Increments `views_count`). |
| `PUT/PATCH` | `/api/posts/{slug}/` | Update a post. (Owner or Admin). |
| `POST` | `/api/posts/{slug}/publish/` | Transition a post from `draft`/`scheduled` to `published`. |
| `GET` | `/api/posts/{slug}/related/` | Get related posts based on tags. |
| `GET` | `/api/posts/{slug}/same-category/` | Get other posts in the same category (Paginated). |

### Nested & Support Endpoints
- **Comments:** `GET /api/posts/{post_slug}/comments/` (Lists approved comments for the post).
- **Authors:** `GET /api/authors/` (List all author profiles).
- **Categories:** `GET /api/categories/` (Hierarchical post categories).
- **Tags:** `GET /api/tags/` (List of tags).
- **Series:** `GET /api/series/` (Group posts into series).
- **Revisions:** `GET /api/revisions/` (View post edit history).

---

## 6. Media Library

All uploaded images are automatically converted to the **AVIF** format for optimization.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/media/` | List uploaded media files. |
| `POST` | `/api/media/` | Upload media. Body: `file` (Multipart), `alt_text`, `title`. |
| `GET` | `/api/media/{id}/` | Retrieve media details (URL, dimensions, etc.). |
| `GET` | `/api/media/{id}/download/` | Download the media file directly. |

---

## 7. Interactions (Comments & Reactions)

| Method | Endpoint | Description | Permissions |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/comments/` | List all comments. | Staff sees all, Public sees approved. |
| `POST` | `/api/comments/` | Post a new comment. | Authenticated |
| `POST` | `/api/reactions/` | Toggle a reaction (Like/Emoji). | Authenticated |

---

## 8. Pages & Navigation

Used for static content and site structure.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/pages/` | List static pages (e.g., About Us, Terms). |
| `GET` | `/api/menus/` | List site menus (Header, Footer). |
| `GET` | `/api/menu-items/` | List individual links within menus. |

---

## 9. Business Logic Highlights

### Post Lifecycle
1. **Draft:** Created by an author, only visible to them and admins.
2. **Scheduled:** Author sets a future `publish_at` date. Celery workers publish it at the set time.
3. **Published:** Visible to the public.

### Media Sync
When a post is saved, the system automatically scans the content for image URLs and synchronizes them with the `PostMedia` registry to ensure integrity and track usage.

### Auto-Reading Time
The `reading_time_sec` is automatically calculated on save based on the word count of the content (approx. 200 words per minute).

---

## 10. Error Handling
Standard HTTP codes are used:
- `401 Unauthorized`: Token missing or expired.
- `403 Forbidden`: You don't have permission for this action.
- `404 Not Found`: The resource does not exist.
- `400 Bad Request`: Validation errors (details provided in `data`).
- `429 Too Many Requests`: Rate limit or brute-force protection (Axes) triggered.
