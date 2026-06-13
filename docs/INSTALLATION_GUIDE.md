# Installation & Setup Guide

This guide provides comprehensive instructions for setting up the Blog Platform development environment.

---

## Prerequisites

Before you begin, ensure you have the following installed:
- **Docker & Docker Compose:** Required for the containerized environment.
- **Python 3.12+:** Required for local development.
- **Node.js (Optional):** Required only if you intend to run the [Mock API Server](../mock-server/).
- **Git:** For version control.

---

## Development Setup (Local)

If you prefer to run the application directly on your host machine:

### 1. Environment Configuration
Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Database and Cache
Ensure **PostgreSQL** and **Redis** are running. Create a database named `blog_db`.

### 3. Environment Variables
Copy the template and update the values:
```bash
cp .env.example .env
```
Key variables to check:
- `DATABASE_URL`: `postgres://user:password@localhost:5432/blog_db`
- `REDIS_URL`: `redis://localhost:6379/0`

### 4. Initialization
```bash
python manage.py migrate
python manage.py createsuperuser
```

---

## Docker Setup (Containerized)

The recommended approach for consistent environments.

### 1. Service Architecture
The `docker-compose.yml` defines the following services:
- `web`: Django application (Daphne/ASGI).
- `db`: PostgreSQL 14.
- `cache`: Redis 8.2.
- `celery_high_priority`: Worker for critical tasks (e.g., Auth emails).
- `celery_default`: Worker for standard tasks (e.g., Post publishing).
- `celery_low_priority`: Worker for heavy processing (e.g., Video optimization).
- `celery-beat`: Scheduler for periodic tasks.
- `nginx`: Reverse proxy serving static/media files.

### 2. Launching the Stack
```bash
docker-compose up --build
```

### 3. Networks & Volumes
- **Networks:** Services communicate over a default internal network.
- **Volumes:**
    - `postgres_data`: Persistent DB storage.
    - `static_volume`: Shared volume for collected static files.
    - `media_volume`: Shared volume for user uploads.

---

## Local Development Workflow

### Dependency Management
The project uses `requirements.txt`. If you add new packages:
1. Add them to `requirements.in`.
2. Compile using `pip-compile` (if using `pip-tools`).
3. Rebuild docker images: `docker-compose build web`.

### Code Quality
Run linters and formatters before committing:
```bash
flake8 .
black .
```

---

## Testing Workflow

### Running Tests
The project uses Django's built-in test runner.

**Local:**
```bash
python manage.py test
```

**Docker:**
```bash
docker-compose exec web python manage.py test
```

### Coverage
To check coverage:
```bash
coverage run manage.py test
coverage report
```

---

## Production Deployment Considerations

When moving to production, ensure:
1. **DEBUG:** Set to `False` in `.env`.
2. **SECRET_KEY:** Use a strong, unique value.
3. **ALLOWED_HOSTS:** Define your production domain.
4. **SSL/TLS:** Handled by Nginx or a cloud load balancer.
5. **Storage:** Set `STORAGE_BACKEND=s3` and provide AWS credentials.
6. **Logging:** Centralized logging is configured in `settings.py` via `LOGGING` dict.
