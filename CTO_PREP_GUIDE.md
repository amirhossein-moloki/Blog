# CTO Technical Preparation Guide — Blog Platform
# راهنمای آمادگی فنی برای CTO — پلتفرم بلاگ

This document prepares the technical team for potential inquiries from the CTO or technical stakeholders regarding the system's architecture, security, performance, and business logic.
این سند تیم فنی را برای سوالات احتمالی CTO یا ذینفعان فنی در مورد معماری سیستم، امنیت، عملکرد و منطق کسب‌وکار آماده می‌کند.

---

## 1. Architecture & Design Patterns
## ۱. معماری و الگوهای طراحی

**Q: What is the overall architectural pattern of the project?**
**س: الگوی معماری کلی پروژه چیست؟**
> **A:** The project follows a **Modular Monolith** architecture. It is organized into independent Django apps (Users, Posts, Medias, Interactions, etc.) with strict domain boundaries. Business logic is decoupled from Views and Models into a dedicated **Service Layer**, making the system "microservice-ready".
> **ج:** پروژه از معماری **Modular Monolith** پیروی می‌کند. این پروژه در قالب اپلیکیشن‌های مستقل جنگو (کاربران، پست‌ها، رسانه‌ها، تعاملات و غیره) با مرزهای دامنه مشخص سازماندهی شده است. منطق کسب‌وکار از Viewها و Modelها جدا شده و در یک **لایه سرویس (Service Layer)** اختصاصی قرار گرفته است که سیستم را برای تبدیل شدن به میکروسرویس آماده می‌کند.

**Q: Why use a Service Layer?**
**س: چرا از لایه سرویس استفاده شده است؟**
> **A:** To maintain "Thin Views" and "Thin Models". This ensures that business logic (like media synchronization or complex publication flows) is centralized, reusable, and easily testable without being tied to the HTTP request-response cycle or DB schema alone.
> **ج:** برای حفظ "Viewهای لاغر" و "Modelهای لاغر". این کار تضمین می‌کند که منطق کسب‌وکار (مانند همگام‌سازی رسانه‌ها یا جریان‌های پیچیده انتشار) متمرکز، قابل استفاده مجدد و به راحتی قابل تست باشد، بدون اینکه صرفاً به چرخه درخواست-پاسخ HTTP یا طرح پایگاه داده وابسته باشد.

---

## 2. Performance & Scalability
## ۲. عملکرد و مقیاس‌پذیری

**Q: How does the system handle high-resolution media assets?**
**س: سیستم چگونه دارایی‌های رسانه‌ای با رزولوشن بالا را مدیریت می‌کند؟**
> **A:** The system implements automated **AVIF conversion** for images (providing ~50% better compression than JPEG/PNG) and background **video compression** via Celery tasks using FFmpeg. This ensures fast load times for the frontend without sacrificing quality.
> **ج:** سیستم تبدیل خودکار به فرمت **AVIF** را برای تصاویر (که حدود ۵۰٪ فشرده‌سازی بهتری نسبت به JPEG/PNG ارائه می‌دهد) و فشرده‌سازی ویدیو در پس‌زمینه را از طریق تسک‌های Celery با استفاده از FFmpeg پیاده‌سازی کرده است. این کار زمان بارگذاری سریع برای فرانت‌اند را بدون کاهش کیفیت تضمین می‌کند.

**Q: How do you prevent N+1 query problems in listing APIs?**
**س: چگونه از مشکلات کوئری N+1 در APIهای لیست جلوگیری می‌کنید؟**
> **A:** We use optimized QuerySets with `select_related` (for ForeignKeys like Author) and `prefetch_related` (for M2M fields like Tags) within custom **PostManagers** and ViewSet overrides. This collapses multiple DB hits into single, efficient queries.
> **ج:** ما از QuerySetهای بهینه شده با `select_related` (برای کلیدهای خارجی مانند نویسنده) و `prefetch_related` (برای فیلدهای M2M مانند برچسب‌ها) در **PostManager**های سفارشی و بازنویسی‌های ViewSet استفاده می‌کنیم. این کار چندین فراخوانی پایگاه داده را به کوئری‌های واحد و کارآمد تبدیل می‌کند.

---

## 3. Security & Reliability
## ۳. امنیت و قابلیت اطمینان

**Q: What is the authentication and authorization strategy?**
**س: استراتژی احراز هویت و تعیین سطح دسترسی چیست؟**
> **A:** We use stateless **JWT (JSON Web Tokens)** via `rest_framework_simplejwt`. Authorization is enforced through a **Permission Matrix** (Admin, Author, User, Guest) using custom DRF permission classes like `IsOwnerOrAdmin`.
> **ج:** ما از **JWT (JSON Web Tokens)** بدون وضعیت از طریق `rest_framework_simplejwt` استفاده می‌کنیم. تعیین سطح دسترسی از طریق یک **ماتریس دسترسی** (مدیر، نویسنده، کاربر، مهمان) با استفاده از کلاس‌های مجوز سفارشی DRF مانند `IsOwnerOrAdmin` اعمال می‌شود.

**Q: How do you handle race conditions during concurrent view count updates?**
**س: چگونه تداخل‌های احتمالی (Race Conditions) را در هنگام به‌روزرسانی همزمان تعداد بازدیدها مدیریت می‌کنید؟**
> **A:** We use **Atomic F() expressions** in the service layer (`Post.objects.update(views_count=F('views_count') + 1)`). This ensures the increment happens at the database level, preventing data loss during simultaneous requests.
> **ج:** ما از **عبارات اتمیک F()** در لایه سرویس استفاده می‌کنیم (`Post.objects.update(views_count=F('views_count') + 1)`). این کار تضمین می‌کند که افزایش مقدار در سطح پایگاه داده انجام شود و از دست رفتن داده‌ها در طول درخواست‌های همزمان جلوگیری شود.

---

## 4. Key Business Logic
## ۴. منطق کلیدی کسب‌وکار

**Q: How is media synchronized with post content?**
**س: رسانه‌ها چگونه با محتوای پست همگام‌سازی می‌شوند؟**
> **A:** The `sync_post_media` service automatically parses the HTML content of a post for `<img>` tags, extracts the storage keys, and updates the `PostMedia` relationship table. This maintains a clean link between assets and content for auditing and cleanup.
> **ج:** سرویس `sync_post_media` به طور خودکار محتوای HTML یک پست را برای تگ‌های `<img>` تجزیه می‌کند، کلیدهای ذخیره‌سازی را استخراج کرده و جدول رابطه `PostMedia` را به‌روزرسانی می‌کند. این کار پیوند تمیزی بین دارایی‌ها و محتوا برای حسابرسی و پاکسازی حفظ می‌کند.

**Q: How does the scheduling system work?**
**س: سیستم زمان‌بندی چگونه کار می‌کند؟**
> **A:** Posts can be set to "Scheduled" status with a `scheduled_at` timestamp. A **Celery Beat** periodic task runs every minute, calling the `publish_scheduled_posts` service to transition due posts to "Published" status automatically.
> **ج:** پست‌ها می‌توانند با وضعیت "زمان‌بندی شده" و یک برچسب زمانی `scheduled_at` تنظیم شوند. یک تسک دوره‌ای **Celery Beat** هر دقیقه اجرا می‌شود و سرویس `publish_scheduled_posts` را فراخوانی می‌کند تا پست‌های سررسید شده را به طور خودکار به وضعیت "منتشر شده" انتقال دهد.

---

## 5. Documentation & Standards
## ۵. مستندات و استانداردها

**Q: Why is the codebase documented bilingually (EN/FA)?**
**س: چرا کدها به صورت دو زبانه (انگلیسی/فارسی) مستند شده‌اند؟**
> **A:** To ensure maximum clarity for a diverse technical team and stakeholders. Every public function and class follows a mandatory bilingual **Google-style docstring** standard, explaining both the "What" and the "Why" of the implementation.
> **ج:** برای اطمینان از حداکثر شفافیت برای تیم فنی و ذینفعان متنوع. هر تابع و کلاس عمومی از استاندارد اجباری **docstring به سبک گوگل** و به صورت دو زبانه پیروی می‌کند که هم "چیستی" و هم "چرایی" پیاده‌سازی را توضیح می‌دهد.
