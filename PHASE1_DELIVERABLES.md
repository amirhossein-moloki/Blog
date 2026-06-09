# فاز ۱: ایجاد ساختار پروژه + اپلیکیشن هسته + BaseModel
# Phase 1: Project Structure + Core App + BaseModel

## دستورات مهاجرت (Migration Commands)
در این فاز مهاجرت خاصی برای دیتابیس وجود ندارد زیرا `BaseModel` یک مدل انتزاعی (abstract) است.
There are no specific migrations for this phase as `BaseModel` is an abstract model.

```bash
python manage.py makemigrations core
python manage.py migrate core
```

## منطق انتقال داده (Data Migration Logic)
در این مرحله داده‌ای منتقل نمی‌شود.
No data migration is required in this phase.

## تست (Testing)
برای اجرای تست‌های این فاز:
To run tests for this phase:

```bash
python manage.py test core
```

## طرح بازگشت (Rollback Plan)
برای بازگشت به حالت قبل از این فاز:
To rollback the changes from this phase:

1. حذف اپلیکیشن `core` از `INSTALLED_APPS` در `blog/settings.py`.
   Remove `core` from `INSTALLED_APPS` in `blog/settings.py`.
2. حذف پوشه `core`.
   Delete the `core` directory.
