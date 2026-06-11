# Deployment and CI/CD Guide

This document describes the CI/CD pipeline and deployment procedures for the Blog Backend project.

## CI/CD Pipeline

The project uses GitHub Actions for CI/CD.

### CI Workflow (`ci.yml`)
Triggered on: Pull Requests and Pushes to `main`, `master`, and `develop`.

Tasks:
1. **Linting**: Runs `black`, `isort`, and `flake8`.
2. **Testing**:
   - Sets up a PostgreSQL service.
   - Installs system and Python dependencies.
   - Runs `python manage.py check`.
   - Validates migrations using `python manage.py makemigrations --check`.
   - Executes the test suite with `coverage`.
   - Enforces 91% test coverage (interim target).
   - Uploads coverage reports to Codecov.

### CD Workflows (`deploy-staging.yml` and `deploy-production.yml`)
Triggered on: Pushes to `develop` (Staging) and `main`/`master` (Production).

Tasks:
1. **Build**: Builds a Docker image and pushes it to Docker Hub.
2. **Deploy**:
   - Connects to the target server via SSH.
   - Performs a `docker-compose pull` and `docker-compose up -d`.
   - Runs migrations and collects static files.
   - Performs a health check against the enhanced `/api/health/` endpoint.

## Environment Variables and Secrets

### Required GitHub Secrets
To enable the pipeline, the following secrets must be configured in the GitHub repository:

| Secret Name | Description |
|-------------|-------------|
| `DOCKERHUB_USERNAME` | Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `STAGING_SSH_HOST` | Staging server IP/hostname |
| `STAGING_SSH_USER` | SSH user for staging |
| `STAGING_SSH_KEY` | SSH private key for staging |
| `PROD_SSH_HOST` | Production server IP/hostname |
| `PROD_SSH_USER` | SSH user for production |
| `PROD_SSH_KEY` | SSH private key for production |
| `CODECOV_TOKEN` | Token for Codecov integration |

### Application Environment Variables
Managed via `.env` files on the servers:
- `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`
- `DATABASE_URL` (or `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`)
- `USE_REDIS`, `REDIS_URL`
- `STORAGE_BACKEND`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.
- `GOOGLE_OAUTH_CLIENT_ID`

## Deployment Strategy

### Dockerized Orchestration
The project uses `docker-compose` to manage services:
- `web`: Django application (Daphne/ASGI)
- `db`: PostgreSQL 14
- `redis`: Redis for Caching and Celery
- `celery_high_priority`, `celery_default`, `celery_low_priority`: Celery workers
- `celery-beat`: Periodic task scheduler
- `nginx`: Reverse proxy handling static/media files and SSL

### Enhanced Health Check
The `/api/health/` endpoint verifies:
- Application responsiveness.
- Database connectivity.
- Redis (Cache) availability.

If any critical service is down, it returns a `503 Service Unavailable` status, which triggers a deployment failure in the CD pipeline.

## Rollback Strategy

### Automated Rollback (Production)
The production workflow includes a health check with retries. If it fails after 5 attempts, it attempts to tag the previous working image back to `latest` and redeploy.

### Manual Rollback
If an automated rollback is insufficient:
1. **Identify the previous stable image tag** (e.g., a specific Git SHA).
2. **SSH into the server**.
3. **Update the image tag** in `docker-compose.yml` or your environment.
4. **Deploy the previous version**:
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

## Security Recommendations

1. **Least Privilege**: The SSH user used for deployment should have limited permissions, ideally restricted to the application directory and Docker commands.
2. **Secrets Management**: Never commit `.env` files. Use GitHub Secrets for CI/CD and secure vault solutions for production.
3. **SSL/TLS**: Always use HTTPS. The provided Nginx configuration includes Certbot for Let's Encrypt.
