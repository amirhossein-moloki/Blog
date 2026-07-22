# سند جامع استراتژی و سیاست‌گذاری کشینگ پروژه (Cache Policy Report)

این گزارش به بررسی جامع وضعیت فعلی وب‌سایت بلاگ، ساختار APIها، و تحلیل رفتار داده‌ای برنامه‌ها پرداخته و یک ساختار کشینگ پیشرفته مبتنی بر **Redis** برای پروژه طراحی و پیشنهاد می‌کند. هدف این طراحی افزایش سرعت پاسخ‌دهی به درخواست‌ها (کاهش Latency)، بهبود پایداری سیستم در ترافیک‌های بالا، و به حداقل رساندن لود روی دیتابیس اصلی (PostgreSQL) است.

---

## ۱. ارزیابی وضعیت فعلی پروژه و زیرساخت‌ها

پروژه به صورت یک **Modular Monolith** با فریمورک جنگو و فریمورک قدرتمند Django REST Framework (DRF) توسعه یافته است. در حال حاضر، زیرساخت کش آماده‌سازی شده است:
- **Redis** به عنوان بروکر فرآیندهای پس‌زمینه (Celery) و چنل‌های وب‌سوکت (Django Channels) استفاده می‌شود.
- در فایل `settings.py` تنظیمات کش سیستم به صورت زیر پیکربندی شده است:
  - در حالت توسعه و تست از کش حافظه محلی (`LocMemCache`) استفاده می‌شود.
  - در حالت تولید از درایور `django_redis.cache.RedisCache` متصل به پایگاه داده ۱ در Redis (`DB 1`) برای جداسازی از فرآیندهای Celery/WebSockets (که روی `DB 0` هستند) استفاده شده است.

این تفکیک دیتابیس‌ها در Redis به ما اجازه می‌دهد که بدون نگرانی از اختلال در صف‌های Celery، عملیات پاک‌سازی و مدیریت کش مربوط به لایه وب را انجام دهیم.

---

## ۲. دسته‌بندی سطح کلیدهای کش (Caching Tiers)

برای این پروژه، APIها بر اساس نرخ خواندن به نوشتن (Read-to-Write Ratio)، حساسیت به به‌روز بودن داده (Staleness Tolerance)، و بار پردازشی کوئری‌ها به ۳ سطح اصلی کش تقسیم می‌شوند:

### الف) سطح ۱: داده‌های بسیار پویا (Highly Dynamic Data) - بدون کش یا کش بسیار کوتاه
این دسته شامل داده‌هایی است که اطلاعات امنیتی، حساس یا دائماً در حال تغییر کاربران و سیستم را نگه می‌دارند. کش کردن این داده‌ها ریسک‌های امنیتی یا ناهماهنگی شدید اطلاعات را در بر دارد.

- **اندپوینت‌های کاندید:**
  - فرآیندهای احراز هویت و توکن: `/api/token/`، `/api/token/refresh/`، `/api/auth/admin-login/`
  - مدیریت اطلاعات کاربر: `/api/users/`، `/api/users/me/`
  - فرآیندهای لایک و ری‌اکشن: `/api/reactions/`
- **سیاست پیشنهادی:** **عدم استفاده از کش سمت سرور (No-Cache).** برای این موارد استفاده از کش مرورگر با سربرگ `Cache-Control: private, no-store` پیشنهاد می‌شود.

---

### ب) سطح ۲: داده‌های نیمه‌پویا (Semi-Dynamic Data) - کش میان‌مدت با ابطال هوشمند (Smart Invalidation)
این داده‌ها لود بسیار سنگینی از سرور می‌گیرند اما در فواصل زمانی نامنظم به‌روز می‌شوند. کاربران انتظار دارند با به‌روزرسانی محتوا، تغییرات را به سرعت مشاهده کنند. این گروه قلب تپنده وبلاگ است.

- **اندپوینت‌های کاندید:**
  - لیست مقالات و جزئیات آن‌ها: `/api/articles/`، `/api/articles/{slug}/`، `/api/articles/slug/{slug}/`
  - مقالات مرتبط و هم‌دسته‌بندی: `/api/articles/{slug}/related/`، `/api/articles/{slug}/same-category/`
  - لیست نظرات تایید شده مقالات: `/api/articles/{article_slug}/comments/`
  - پادکست‌ها و گالری‌ها: `/api/podcasts/`، `/api/gallery/`
- **زمان انقضا (TTL):** بین **۲ ساعت تا ۱ روز** (مثلاً ۲ ساعت برای لیست مقالات داینامیک و ۱۲ ساعت برای جزئیات مقالات).
- **مکانیسم ابطال کش (Invalidation):** استفاده از سیگنال‌های جنگو (Post-Save/Post-Delete) روی مدل‌های مربوطه برای پاک کردن فوری کش کلیدهای خاص، بلافاصله پس از تغییرات توسط نویسندگان یا مدیران.

---

### ج) سطح ۳: داده‌های ایستا (Highly Static Data) - کش بلندمدت
داده‌هایی که ساختار کلی سایت را تعریف می‌کنند و تغییرات در آن‌ها به ندرت (ماهانه یا هفتگی) رخ می‌دهد. کش کردن سنگین این بخش‌ها لود دیتابیس را به شدت کاهش می‌دهد.

- **اندپوینت‌های کاندید:**
  - منوهای ناوبری و آیتم‌های منو: `/api/menus/`، `/api/menu-items/`
  - صفحات ایستای سایت (مانند درباره ما، قوانین و...): `/api/pages/`
  - دسته‌بندی‌ها و برچسب‌ها: `/api/categories/`، `/api/tags/`
  - فایل سیت‌مپ سایت: `/sitemap.xml`
- **زمان انقضا (TTL):** بین **۷ روز تا ۳۰ روز** (با انقضای دستی یا ابطال از طریق پنل ادمین در صورت ویرایش منو یا اضافه شدن تگ جدید).
- **سیاست پیشنهادی:** کش کردن پاسخ‌های آماده شده (Response-level caching) با استفاده از مکانیسم درونی DRF یا دکوراتورهای جنگو.

---

## ۳. سیاست‌های اختصاصی کش و فرمت کلیدها (Cache Key Strategy)

برای پیاده‌سازی کشینگ بدون خطا، ساختار کلیدهای ذخیره شده در Redis باید منظم، یکتا و دارای پیشوند ساختاریافته باشد.

### ساختار نام‌گذاری کلیدها (Naming Convention):
```
blog_cache:<app_name>:<model_or_view>:<identifier>:<query_params_hash>
```

### نمونه‌های کاربردی تولید کلید کش:
۱. **کش کردن مقاله خاص بر اساس زبان و اسلاگ:**
   - فرمت کلید: `blog_cache:posts:article:detail:<slug>:<language_code>`
   - نمونه: `blog_cache:posts:article:detail:getting-started-django:fa`

۲. **کش کردن لیست مقالات صفحه اصلی با پارامترهای فیلتر:**
   ما با استفاده از یک تابع هش‌کننده پارامترهای ورودی URL (مانند `page`, `category`, `tag`, `lang`) را به یک هش MD5 تبدیل می‌کنیم تا هر صفحه کش اختصاصی خود را داشته باشد.
   - فرمت کلید: `blog_cache:posts:article:list:<language_code>:<query_params_hash>`
   - نمونه: `blog_cache:posts:article:list:fa:9a12c4b5d6e7f8`

۳. **کش کردن منوهای سایت:**
   - فرمت کلید: `blog_cache:navigation:menus:all`

---

## ۴. استراتژی هوشمند ابطال کش (Cache Invalidation Strategy)

بزرگترین چالش در استفاده از کش، اطمینان از به‌روز بودن داده‌ها برای کاربران است. برای پروژه بلاگ، ما رویکردهای زیر را برای ابطال هوشمند کش پیشنهاد می‌دهیم:

### الف) ابطال مبتنی بر سیگنال‌های جنگو (Signal-Based Invalidation)
با تعریف سیگنال‌های `post_save` و `post_delete` در جنگو، بلافاصله پس از اضافه شدن، ویرایش یا حذف یک مدل، کلیدهای مرتبط با آن را از Redis حذف می‌کنیم:

1. **مدل مقاله‌ها (`Article`):**
   در صورت ویرایش مقاله:
   - حذف کلید جزئیات مقاله: `blog_cache:posts:article:detail:<slug>:*` (تمام نسخه‌های زبانی)
   - حذف تمام کلیدهای لیست مقالات: `blog_cache:posts:article:list:*`
   - حذف کلیدهای مربوط به مقالات مرتبط (`related`) و هم‌دسته‌بندی (`same-category`).

2. **مدل دسته‌بندی‌ها و تگ‌ها (`Category` / `Tag`):**
   - به محض ویرایش دسته‌بندی یا تگ، کلیدهای مربوط به لیست مقالات و لیست دسته‌بندی‌ها باید پاک‌سازی شوند تا تغییرات بلافاصله اعمال گردند.

3. **مدل نظرات (`Comment`):**
   - هنگامی که کامنت جدیدی تایید (`approved`) یا حذف می‌شود، کش مربوط به کامنت‌های آن مقاله خاص باید ابطال شود: `blog_cache:posts:comments:<article_slug>:*`

---

## ۵. معماری و سناریوی پیشنهادی برای پیاده‌سازی عملی (Django Implementation)

برای پیاده‌سازی این سیاست‌ها در پروژه فعلی، ابزارهای زیر به شدت توصیه می‌شود:

### الف) پیاده‌سازی ابطال کش خودکار با سیگنال‌ها (کد نمونه برای توسعه آینده)

می‌توان فایلی تحت عنوان `posts/signals.py` به شکل زیر ویرایش یا اضافه نمود تا عمل پاک‌سازی کش‌ها پس از تغییر مقالات به صورت کاملاً اتوماتیک انجام گیرد:

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from posts.models import Article

def invalidate_article_cache(article):
    # ۱. پاک کردن کش جزئیات مقاله برای تمام زبان‌ها
    for lang in ['fa', 'en']:
        for slug in article.translations.values_list('slug', flat=True):
            cache.delete(f"blog_cache:posts:article:detail:{slug}:{lang}")
            cache.delete(f"blog_cache:posts:article:by_slug:{slug}:{lang}")

    # ۲. پاک کردن کش‌های لیست مقالات (به دلیل تغییر تعداد یا وضعیت مقاله‌ها)
    # با استفاده از الگوها در django-redis می‌توان تمام کلیدهای با الگوی خاص را پاک کرد:
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern("blog_cache:posts:article:list:*")
        cache.delete_pattern(f"blog_cache:posts:article:related:{article.id}:*")
        cache.delete_pattern(f"blog_cache:posts:article:same_category:{article.id}:*")
    else:
        # در صورت نبود قابلیت الگوی حذف، پاک‌سازی کلیدهای اصلی
        cache.delete("blog_cache:posts:article:list:main")

@receiver(post_save, sender=Article)
def handle_article_save(sender, instance, **kwargs):
    invalidate_article_cache(instance)

@receiver(post_delete, sender=Article)
def handle_article_delete(sender, instance, **kwargs):
    invalidate_article_cache(instance)
```

### ب) استفاده از پکیج هوشمند `drf-extensions` یا کش سفارشی لایه View
برای پیاده‌سازی کش با راندمان بالا روی ViewSetهای DRF، بهترین رویکرد نوشتن یک Mixin اختصاصی کش‌کننده یا دکوراتور برای متدهای `list` و `retrieve` است. به عنوان مثال:

```python
import hashlib
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

class CachedViewSetMixin:
    """
    میکسین اختصاصی جهت کش در سطح متدهایViewSetهای DRF با مدیریت زبان و هدرها
    """
    cache_timeout = 60 * 15  # ۱۵ دقیقه به عنوان پیش‌فرض

    def get_cache_key(self, request, view_action, *args, **kwargs):
        # ساخت کلید کش منحصر به فرد بر اساس زبان، آدرس و پارامترهای کوئری
        lang = request.query_params.get("lang", "en")
        path = request.get_full_path()
        path_hash = hashlib.md5(path.encode('utf-8')).hexdigest()
        user_auth = "auth" if request.user.is_authenticated else "anon"
        return f"blog_cache:{self.basename}:{view_action}:{lang}:{user_auth}:{path_hash}"

    def list(self, request, *args, **kwargs):
        # بررسی وجود نسخه کش‌شده
        cache_key = self.get_cache_key(request, "list")
        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)

        # در صورت عدم وجود، دریافت از دیتابیس و ذخیره در کش
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, self.cache_timeout)
        return response
```

---

## ۶. نتایج و منافع استفاده از سیاست پیشنهادی کش (Impact Analysis)

با پیاده‌سازی این سیاست کش، بهبودهای زیر در کارایی برنامه تضمین می‌شود:

۱. **کاهش چشمگیر بار روی دیتابیس (SQL Queries Reduction):**
   بیش از **۸۰ درصد ترافیک وبلاگ‌ها** روی مشاهده مقالات پربازدید و لیست مقالات صفحه اول متمرکز است. کش کردن این اندپوینت‌ها نیاز به کوئری‌های گران‌قیمت `JOIN` روی سه‌جدول مقالات، ترجمه‌ها و دسته‌بندی‌ها را تقریباً به صفر می‌رساند.

۲. **کاهش شدید Latency و بهبود امتیاز Core Web Vitals:**
   زمان پاسخ‌دهی (Time to First Byte - TTFB) سرور برای مقالات پربازدید از ۲۰۰-۴۰۰ میلی‌ثانیه به کمتر از **۲۰-۵۰ میلی‌ثانیه** (زمان خواندن مستقیم از Redis) کاهش می‌یابد که این موضوع تأثیر مستقیمی بر بهبود رتبه سئو (SEO) سایت دارد.

۳. **پایداری سیستم در زمان ترافیک‌های ناگهانی (Scalability):**
   هنگام انتشار خبرهای ترند یا اشتراک‌گذاری لینک مقالات در شبکه‌های اجتماعی، وب‌سایت با کرش مواجه نمی‌شود؛ چرا که پاسخ تمام بازدیدکنندگان جدید بلافاصله از حافظه رم (RAM) سرور Redis داده می‌شود و نیازی به پردازش مجدد در سرور جنگو و دیتابیس نیست.
