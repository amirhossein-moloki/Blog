# MAPPING SUMMARY & RISK NOTES

## 1. Mapping Summary (Django → Prisma)

| Django Concept | Prisma Implementation | Notes |
| :--- | :--- | :--- |
| `BaseModel` | Explicit fields on each model | `isActive`, `createdAt`, `updatedAt` are replicated across models. |
| `User` (Custom) | `User` model | Mapped standard fields + profile attributes. |
| `AuthorProfile` | `AuthorProfile` model | Maintained OneToOne relationship with User. |
| `Post` | `Post` model | Translated all status/visibility choices to enums. |
| `Category` | `Category` model | Self-referencing relationship for hierarchy. |
| `Tag` | `Tag` model + `PostTag` pivot | Explicit M2M mapping using a join table. |
| `Media` | `Media` model | Categorized file types into a `MediaType` enum. |
| `PostMedia` | `PostMedia` model | Association table for media usage within posts. |
| `Comment` | `Comment` model | Self-referencing relationship for threaded replies. |
| `Reaction` | `Reaction` model | Simulated GFK using `contentType` and `objectId`. |
| `Page` | `Page` model | Static content with SEO attributes. |
| `Menu` / `MenuItem` | `Menu` / `MenuItem` models | Explicit hierarchy and location enums. |

## 2. Design Choices
- **Naming Convention**: Models use `PascalCase` and fields use `camelCase`, adhering to Prisma best practices while mapping to original snake_case table names via `@@map`.
- **Primary Keys**: Switched from Django's auto-incrementing integers to `uuid()` for better scalability in a distributed system, unless specified otherwise.
- **Explicit Relations**: All relationships are explicitly defined with `fields` and `references` to ensure Prisma's referential integrity.
- **Indexing**: Slugs, statuses, and common foreign keys are indexed to maintain performance parity with the Django implementation.

## 3. Risk Notes & Ambiguity
- **Generic Foreign Keys (GFK)**: Django's `Reaction` model uses `ContentType` and `object_id`. Prisma does not natively support polymorphic relations. The current implementation uses a string-based `contentType` and `objectId`, which requires application-level logic to enforce referential integrity.
- **CKEditor Content**: Content is stored as raw HTML strings in `String @db.Text`. The logic for parsing this content (e.g., in `sync_post_media`) must be replicated in the Express.js service layer.
- **Reading Time Logic**: The automated calculation of reading time performed in Django's `save()` method must be implemented as a Prisma middleware or within the service layer in Express.js.
- **Media Optimization**: The analysis noted that optimization logic was recently removed/disabled. If it is re-introduced, the `Media` model may need additional fields for different versions/formats (e.g., AVIF, WebP).
- **Date Conversion**: The system uses Jalali dates in the frontend/API. While the DB stores standard `DateTime` (UTC), any server-side logic involving date formatting must be carefully ported to Node.js (e.g., using `jalaali-js`).
