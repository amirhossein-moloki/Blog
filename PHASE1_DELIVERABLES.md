# [HISTORICAL REFERENCE] Phase 1: Project Structure + Core App + BaseModel

> **Note:** This document describes the initial phase of the project and is kept for historical reference. The project has since undergone significant refactoring into a modular architecture.

## Migration Commands
There are no specific migrations for this phase as `BaseModel` is an abstract model.

```bash
python manage.py makemigrations core
python manage.py migrate core
```

## Data Migration Logic
No data migration is required in this phase.

## Testing
To run tests for this phase:

```bash
python manage.py test core
```

## Rollback Plan
To rollback the changes from this phase:

1. Remove `core` from `INSTALLED_APPS` in `blog/settings.py`.
2. Delete the `core` directory.
