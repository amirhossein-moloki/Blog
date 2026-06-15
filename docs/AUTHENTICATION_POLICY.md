# Authentication Policy (سیاست احراز هویت)

## Overview (نمای کلی)
This document outlines the authentication policy for the Blog Platform, detailng the supported methods, their intended use cases, and technical implementation.

این سند سیاست احراز هویت پلتفرم وبلاگ را تشریح می‌کند و روش‌های پشتیبانی شده، موارد استفاده مورد نظر و پیاده‌سازی فنی آن‌ها را توضیح می‌دهد.

---

## 1. JWT Authentication (احراز هویت با JWT)
**Target:** Regular users, authors, and client applications.
**هدف:** کاربران عادی، نویسندگان و اپلیکیشن‌های کلاینت.

### Flows (جریان‌ها)
1. **Standard Login (ورود استاندارد):**
   - **Endpoint:** `/api/token/`
   - **Method:** `POST`
   - **Fields:** `username`, `password`
2. **Admin Login (ورود مدیران):**
   - **Endpoint:** `/api/auth/admin-login/`
   - **Method:** `POST`
   - **Fields:** `username`, `password`
3. **Token Refresh (بروزرسانی توکن):**
   - **Endpoint:** `/api/token/refresh/`
   - **Method:** `POST`
   - **Fields:** `refresh`

### Usage (نحوه استفاده)
Include the access token in the header:
`Authorization: Bearer <access_token>`

توکن دسترسی را در هدر قرار دهید:
`Authorization: Bearer <access_token>`

---

## 2. Static API Key Authentication (احراز هویت با کلید API ثابت)
**Target:** Automated tests, developers, and internal services.
**هدف:** تست‌های خودکار، توسعه‌دهندگان و سرویس‌های داخلی.

### Implementation (پیاده‌سازی)
This method is primarily used for testing and bypasses the need for generating short-lived JWT tokens.

این روش عمدتاً برای تست استفاده می‌شود و نیاز به تولید توکن‌های کوتاه مدت JWT را از بین می‌برد.

### Headers (هدرها)
- `X-API-Key`: The static secret key (configured via `STATIC_API_KEY` environment variable).
- `X-Test-User` (Optional): The username to authenticate as. If omitted, the system defaults to the first superuser.

- `X-API-Key`: کلید مخفی ثابت (تنظیم شده از طریق متغیر محیطی `STATIC_API_KEY`).
- `X-Test-User` (اختیاری): نام کاربری برای احراز هویت به عنوان آن کاربر. در صورت حذف، سیستم به صورت پیش‌فرض اولین ابرکاربر را انتخاب می‌کند.

---

## 3. Policy Changes & Removals (تغییرات و موارد حذف شده)
- **Google OAuth2 Removal:** Google login has been entirely removed from the system to simplify the authentication surface and focus on core identity management.
- **حذف گوگل OAuth2:** ورود با گوگل به طور کامل از سیستم حذف شده است تا سطح احراز هویت ساده‌تر شود و بر مدیریت هویت اصلی تمرکز شود.

---

## 4. Security Measures (تدابیر امنیتی)
- **Brute Force Protection:** Managed via `django-axes` to prevent multiple failed login attempts.
- **محافظت در برابر حملات Brute Force:** مدیریت شده از طریق `django-axes` برای جلوگیری از تلاش‌های مکرر ناموفق برای ورود.
- **Environment Based:** The API Key must be configured via environment variables for security.
- **مبتنی بر محیط:** کلید API برای امنیت باید از طریق متغیرهای محیطی تنظیم شود.
