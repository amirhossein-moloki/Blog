# Blog and User Management System

This is a Django-based blog and user management system. It provides a robust backend for managing posts, categories, tags, comments, and user authentication with profile management.

## Features

*   **User Management:**
    *   Registration and authentication (JWT-based).
    *   Google OAuth2 login support.
    *   User profile management.
    *   Role-based access control (Admin, Author, User).
*   **Blog System:**
    *   Modular architecture (Posts, Medias, Interactions, Pages, Navigation).
    *   Post creation with rich text editor (CKEditor 5).
    *   Post scheduling and automated publishing.
    *   Taxonomies (Categories, Tags, and Series).
    *   Comment system with nested replies and moderation.
    *   Revisions and reactions for posts and comments.
    *   Media management with automatic image optimization (AVIF conversion and resizing).
*   **Technical Features:**
    *   Standardized API responses.
    *   Asynchronous video optimization using Celery and FFmpeg.
    *   Admin interface using Unfold.
    *   API documentation with `drf-spectacular`.
    *   Dockerized environment for easy deployment.

## Getting Started

### Prerequisites

*   Python 3.12+
*   PostgreSQL
*   Redis
*   Docker and Docker Compose (recommended)

### Running with Docker

This is the recommended way to run the project for development and production.

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd blog-backend
    ```

2.  **Set up environment variables:**
    Copy the example environment file and fill in your details.
    ```bash
    cp .env.example .env
    ```
    Ensure `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` are correctly set.

3.  **Build and run the application:**
    ```bash
    docker-compose up --build
    ```
    The application will be available at `http://localhost:8000` (or `http://localhost` if using Nginx).

4.  **Create a superuser:**
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

### Local Development (without Docker)

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run migrations:**
    ```bash
    python manage.py migrate
    ```

3.  **Run the development server:**
    ```bash
    python manage.py runserver
    ```

## API Documentation

Once the server is running, you can access the API documentation at:
*   Swagger UI: `http://localhost:8000/api/docs/`

## Project Structure

```
.
├── posts/                # Posts application (Core content, Taxonomies)
├── medias/               # Medias application (Centralized asset management)
├── interactions/         # Interactions application (Comments, Reactions)
├── pages/                # Pages application (Static content)
├── navigation/           # Navigation application (Dynamic Menus)
├── users/                # User management application (Auth, Profiles)
├── core/                 # Core logic and Base models
├── common/               # Shared utilities, standardized renderers, and mixins
├── blog/                 # Project configuration and settings
├── templates/            # HTML templates
├── manage.py             # Django management script
├── Dockerfile            # Docker configuration for the web app
└── docker-compose.yml    # Docker Compose configuration
```

## Contributing

Contributions are welcome! Please follow the standard pull request process.
