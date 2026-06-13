# System Audit & Design Report

This document provides a comprehensive professional-grade design documentation and audit of the Blog Platform, reverse-engineered from the Django/DRF implementation.

---

## SECTION 1 — CLASS DIAGRAM

```mermaid
classDiagram
    class BaseModel {
        <<abstract>>
        +BooleanField is_active
        +DateTimeField created_at
        +DateTimeField updated_at
    }

    class User {
        +OptimizedImageField profile_picture
        +list role
    }

    class AuthorProfile {
        +OneToOneField user
        +CharField display_name
        +TextField bio
        +ForeignKey avatar
    }

    class Category {
        +SlugField slug
        +CharField name
        +ForeignKey parent
        +TextField description
        +IntegerField order
    }

    class Tag {
        +SlugField slug
        +CharField name
        +TextField description
    }

    class Series {
        +SlugField slug
        +CharField title
        +TextField description
        +CharField order_strategy
    }

    class Post {
        +SlugField slug
        +URLField canonical_url
        +CharField title
        +TextField excerpt
        +BooleanField is_hot
        +CKEditor5Field content
        +PositiveIntegerField reading_time_sec
        +CharField status
        +CharField visibility
        +DateTimeField published_at
        +DateTimeField scheduled_at
        +ForeignKey author
        +ForeignKey category
        +ForeignKey series
        +ForeignKey cover_media
        +CharField seo_title
        +TextField seo_description
        +ForeignKey og_image
        +PositiveIntegerField views_count
    }

    class PostTag {
        +ForeignKey post
        +ForeignKey tag
    }

    class Revision {
        +ForeignKey post
        +ForeignKey editor
        +CKEditor5Field content
        +CharField title
        +TextField excerpt
        +CharField change_note
    }

    class Media {
        +CharField storage_key
        +URLField url
        +CharField type
        +CharField mime
        +PositiveIntegerField width
        +PositiveIntegerField height
        +PositiveIntegerField duration
        +PositiveIntegerField size_bytes
        +CharField alt_text
        +CharField title
        +ForeignKey uploaded_by
    }

    class PostMedia {
        +ForeignKey post
        +ForeignKey media
        +CharField attachment_type
    }

    class Comment {
        +ForeignKey post
        +ForeignKey user
        +ForeignKey parent
        +CKEditor5Field content
        +CharField status
        +GenericIPAddressField ip
        +CharField user_agent
    }

    class Reaction {
        +ForeignKey user
        +CharField reaction
        +ForeignKey content_type
        +PositiveIntegerField object_id
    }

    class Menu {
        +CharField name
        +CharField location
    }

    class MenuItem {
        +ForeignKey menu
        +ForeignKey parent
        +CharField label
        +CharField url
        +PositiveIntegerField order
        +BooleanField target_blank
    }

    class Page {
        +SlugField slug
        +CharField title
        +CKEditor5Field content
        +CharField status
        +DateTimeField published_at
        +CharField seo_title
        +TextField seo_description
    }

    BaseModel <|-- AuthorProfile
    BaseModel <|-- Category
    BaseModel <|-- Tag
    BaseModel <|-- Series
    BaseModel <|-- Post
    BaseModel <|-- PostTag
    BaseModel <|-- Revision
    BaseModel <|-- Media
    BaseModel <|-- PostMedia
    BaseModel <|-- Comment
    BaseModel <|-- Reaction
    BaseModel <|-- Menu
    BaseModel <|-- MenuItem
    BaseModel <|-- Page

    User "1" -- "1" AuthorProfile : owns
    AuthorProfile "1" -- "*" Post : writes
    Category "1" -- "*" Post : categorizes
    Category "0..1" -- "*" Category : sub-category
    Post "1" -- "*" PostTag : has
    Tag "1" -- "*" PostTag : applied-to
    Series "1" -- "*" Post : grouping
    Post "1" -- "*" Revision : history
    User "1" -- "*" Revision : edits
    Media "1" -- "*" AuthorProfile : avatar
    Media "1" -- "*" Post : cover/og
    Post "1" -- "*" PostMedia : attachments
    Media "1" -- "*" PostMedia : attached-as
    User "1" -- "*" Media : uploads
    Post "1" -- "*" Comment : contains
    User "1" -- "*" Comment : writes
    Comment "0..1" -- "*" Comment : replies
    User "1" -- "*" Reaction : performs
    Reaction "*" -- "1" Post : generic-target
    Reaction "*" -- "1" Comment : generic-target
    Menu "1" -- "*" MenuItem : contains
    MenuItem "0..1" -- "*" MenuItem : nested-link
```

---

## SECTION 2 — USE CASE DIAGRAM

```mermaid
flowchart LR
    subgraph Actors
        G[Guest]
        U[Authenticated User]
        A[Author]
        AD[Admin]
        S[System/Background Jobs]
    end

    subgraph "Authentication & User"
        UC1(Login / Register / Google OAuth)
        UC2(Token Refresh)
        UC3(Manage Profile / View 'me')
        UC4(User Management)
    end

    subgraph "Content & Engagement"
        UC5(View Posts / Pages / Menus)
        UC6(Comment on Post)
        UC7(React to Post/Comment)
        UC8(Search & Filter Posts)
    end

    subgraph "Authoring & Media"
        UC9(Create / Edit Post)
        UC10(Manage Series / Tags)
        UC11(Upload Media / AVIF Conversion)
    end

    subgraph "Admin & System"
        UC12(Manage Pages / Menus)
        UC13(Publish Scheduled Posts)
        UC14(Send Notifications)
    end

    G --> UC1
    G --> UC5
    G --> UC8
    U --> UC2
    U --> UC3
    U --> UC6
    U --> UC7
    A --> UC9
    A --> UC10
    A --> UC11
    AD --> UC4
    AD --> UC12
    S --> UC13
    S --> UC14
```

---

## SECTION 3 — ACTIVITY DIAGRAMS

### 1. Login Flow (Standard & Google OAuth)
```mermaid
flowchart TD
    Start[Start] --> Type{Login Type?}
    Type -->|Standard| Creds[Provide Username/Password]
    Type -->|Google| GAuth[Provide Google ID Token]

    Creds --> Valid{Valid?}
    Valid -->|No| Error[Return 401 Unauthorized]
    Valid -->|Yes| JWT[Generate JWT Tokens]

    GAuth --> GVerify{Verify with Google}
    GVerify -->|Fail| GError[Return 400/503 Error]
    GVerify -->|Success| UserExists{User Exists?}
    UserExists -->|No| Register[Create User / 404 Error]
    UserExists -->|Yes| JWT

    JWT --> End[Return Access & Refresh Tokens]
```

### 2. Post Creation Flow (with Media Sync)
```mermaid
flowchart TD
    Start[Author Submits Post] --> Auth{Is Author?}
    Auth -->|No| Deny[Return 403 Forbidden]
    Auth -->|Yes| Val[Validate Fields & Tags]
    Val --> Status{Status == 'published'?}
    Status -->|Yes| Date{publish_at > Now?}
    Date -->|Yes| Sched[Set 'scheduled' status]
    Date -->|No| Pub[Set 'published' status]
    Status -->|No| SaveDraft[Save as Draft/Review]

    Sched --> DB[Save to Database]
    Pub --> DB
    SaveDraft --> DB

    DB --> Sync[Trigger sync_post_media]
    Sync --> Media[Scan content for <img> tags]
    Media --> Link[Create/Update PostMedia links]
    Link --> End[Return 201 Created]
```

### 3. Scheduled Publishing (Background)
```mermaid
flowchart TD
    Beat[Celery Beat Trigger] --> Check[Check DB for scheduled posts]
    Check --> Due{scheduled_at <= Now?}
    Due -->|Yes| Publish[Update Status to 'published']
    Publish --> Time[Set published_at = scheduled_at]
    Time --> Clear[Clear scheduled_at]
    Clear --> Log[Log Success]
    Due -->|No| Finish[End Cycle]
```

---

## SECTION 4 — SEQUENCE DIAGRAMS

### 1. Authentication Flow (JWT)
```mermaid
sequenceDiagram
    participant User
    participant API as CustomTokenObtainPairView
    participant Serializer as CustomTokenObtainPairSerializer
    participant DB as PostgreSQL

    User->>API: POST /api/token/ (username, password)
    API->>Serializer: is_valid(data)
    Serializer->>DB: Query User
    DB-->>Serializer: User Object
    Serializer->>Serializer: Check Password
    Serializer-->>API: Validated Data (access, refresh)
    API-->>User: 200 OK
```

### 2. Post Creation Flow
```mermaid
sequenceDiagram
    participant Author
    participant API as PostViewSet
    participant Serializer as PostCreateUpdateSerializer
    participant Service as sync_post_media
    participant DB as PostgreSQL

    Author->>API: POST /api/posts/ (content, images)
    API->>Serializer: is_valid()
    Serializer->>Serializer: _handle_publication_date()
    API->>DB: perform_create (Save Post)
    DB-->>API: Post instance
    API->>Service: sync_post_media(post)
    Service->>DB: Create/Delete PostMedia links
    API-->>Author: 201 Created
```

---

## SECTION 5 — SYSTEM DESIGN DOCUMENT (SDD)

### 1. System Overview
*   **Purpose:** A modern, scalable blog platform with Persian/Jalali support and optimized media management.
*   **Architecture Type:** Modular Monolith. The system is organized into distinct apps (Users, Posts, Medias, Interactions, Pages, Navigation) with a shared Core.

### 2. Architecture Diagram
```mermaid
flowchart TD
    Client[Web/Mobile Client] --> Nginx[Nginx Reverse Proxy]
    Nginx --> Gunicorn[Gunicorn / Django]
    Gunicorn --> PostgreSQL[(PostgreSQL)]
    Gunicorn --> Redis[(Redis Cache/Queue)]
    Celery[Celery Workers] --> Redis
    Celery --> PostgreSQL
    Gunicorn --> S3[Local/S3 Media Storage]
```

### 3. Data Architecture
*   **Database:** PostgreSQL 14.
*   **ORM:** Django ORM with extensive use of `select_related` and `prefetch_related` for performance.
*   **Relationships:** Mix of standard Foreign Keys and Django ContentTypes (Generic Relations) for reactions.

### 4. API Architecture
*   **Structure:** Django REST Framework with ViewSets.
*   **Standardization:** Custom Renderers and Schemas ensure all responses follow the `{"data": ..., "messagesList": ...}` format.
*   **Authentication:** JWT (SimpleJWT) and Google OAuth2.

### 5. Security Architecture
*   **Permissions:** Multi-layered access control (`IsOwnerOrAdmin`, `IsAuthorOrAdminOrReadOnly`).
*   **Data Protection:** Django Axes for brute-force protection, input sanitization via CKEditor5 and file validation.

### 6. Scaling Strategy
*   **Horizontal Scaling:** Stateless Django application allows multiple Gunicorn instances.
*   **Caching:** Redis used for session management and distributed task brokering.
*   **Async Processing:** Celery handles high-latency tasks (Media processing, scheduled publishing, notifications).

---

## SECTION 6 — DEPLOYMENT DIAGRAM

```mermaid
flowchart TD
    Internet[Internet] --> LB[Load Balancer / Cloud Gateway]
    LB --> Nginx[Nginx Container]
    Nginx --> Gunicorn[Django Gunicorn Container]

    subgraph "Application Cluster"
        Gunicorn
        CH[Celery High Priority]
        CD[Celery Default]
        CL[Celery Low Priority]
        CB[Celery Beat]
    end

    Gunicorn --> DB[(PostgreSQL 14)]
    Gunicorn --> Cache[(Redis Cache)]

    CH --> Cache
    CD --> Cache
    CL --> Cache
    CB --> Cache

    CH --> DB
    CD --> DB
    CL --> DB

    Gunicorn --> Storage[Static/Media Volume]
```

---

## SECTION 7 — CONSISTENCY & AUDIT REPORT

### Issues Found
1.  **Legacy Code in Permissions:** The `users/permissions.py` file contains logic for 'Support Tickets', 'Tournament Reports', and 'Winner Submissions' which do not exist in the current project scope.
2.  **Redundant Permission Implementation:** There are two `IsOwnerOrReadOnly` classes (one in `users/permissions.py` and another in `common/permissions.py`) with slightly different implementations.
3.  **Missing Global Error Handling for Non-API Paths:** While API 404s are handled with JSON, other external paths redirect to a hardcoded URL which might not exist.

### Missing Documentation
1.  **Filter Logic Documentation:** The specific filtering capabilities of `PostFilter` are not fully documented in the code docstrings.
2.  **AVIF Conversion Side Effects:** The automatic conversion of all images to AVIF in `create_media_from_file` is a significant business rule not explicitly highlighted in the high-level README.

### Design Weaknesses
1.  **Synchronous Media Sync:** The `sync_post_media` service is called synchronously in `Post.save()`. For posts with many images, this could cause slow response times and potential timeouts.
2.  **Hardcoded Paths:** Some services (e.g., `increment_post_view_count`) use hardcoded error messages and logging strings rather than localized or standardized constants.

### Inconsistencies
*   **Permissions vs. Models:** The `IsOwnerOrAdmin` permission checks for a `ticket` attribute, but no Ticket model is present in the codebase.
*   **Serialization vs. Storage:** Images are stored as AVIF but the model fields are standard `OptimizedImageField`, leading to a potential discrepancy if the field logic expects standard formats (JPG/PNG).

### Audit Summary
The system is well-structured as a modular monolith with a clean separation of concerns. However, it carries significant "technical debt" in the form of legacy permission logic from a previous iteration of the project (likely a tournament management system). Cleaning up these legacy references and moving `sync_post_media` to an asynchronous Celery task would significantly improve maintainability and performance.
