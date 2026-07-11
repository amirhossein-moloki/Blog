# گزارش نهایی ارتقا و توسعه سیستم محتوایی پروژه (Content System Upgrade Report)

این سند شامل گزارش جامع تغییرات خواسته‌شده توسط کارفرما و پیاده‌سازی‌های انجام‌شده بر اساس معماری فعلی پروژه، به صورت کاملاً هماهنگ و Production-Ready می‌باشد.

---

## ۱. نیازمندی‌های خواسته‌شده (Requested Requirements)
تغییرات و نیازمندی‌های جدید به صورت کلی به سه دسته اصلی تقسیم می‌شدند:
1. **ارتقای مدل‌های محتوایی موجود (Article/Post & Category):**
   - اضافه کردن عنوان، اسلاگ، توضیحات کوتاه، تصویر کاور، فیلد Rich Text برای محتوای اصلی، دسته‌بندی، نویسنده، انتخاب دستی مقالات مرتبط (`related_articles`) و تاریخ‌ها.
   - اضافه کردن آیکون (ترجیحاً SVG) و وضعیت فعال/غیرفعال به مدل دسته‌بندی مقالات (`Category`).
2. **پیاده‌سازی سیستم مدیریت پادکست‌ها (Podcast & PodcastCategory):**
   - ایجاد ساختار دسته‌بندی پادکست شامل عنوان، اسلاگ، آیکون SVG و وضعیت فعال بودن.
   - ایجاد مدل اصلی پادکست/اپیزود با مشخصات: عنوان، اسلاگ، دسته‌بندی، شماره اپیزود، تصویر کاور، فایل صوتی، نوع رسانه (صوتی/ویدئوکست)، فایل یا لینک ویدئو، توضیحات (به صورت Rich Text)، مدت زمان به دقیقه، تاریخ انتشار، تعداد بازدید (جهت نمایش پربازدیدها) و پادکست‌های مرتبط.
3. **پیاده‌سازی گالری تصاویر پولاروید (GalleryItem):**
   - تصویر اصلی، توضیح کوتاه (Caption)، ترتیب نمایش (order) برای قابلیت مرتب‌سازی، وضعیت فعال بودن و لینک دلخواه و اختیاری به صفحات دیگر.

---

## ۲. پیاده‌سازی‌های انجام‌شده بر اساس نیازمندی‌ها (Implemented Changes)

تغییرات با کمترین تغییر در معماری و به صورت ۱۰۰٪ سازگار با ساختار فعلی پروژه بدون هیچ‌گونه Data Loss یا Breaking Changes پیاده‌سازی شدند:

### الف) ارتقای مدل‌های موجود در `posts/models.py`
* **مدل `Post` (معادل Article):**
  - فیلد `related_posts` به صورت `ManyToManyField("self", blank=True, symmetrical=False)` به مدل `Post` اضافه شد تا مدیر سایت بتواند به صورت دستی مقالات مرتبط را در پنل ادمین انتخاب کند. این فیلد در سطح کلان مدل `Post` قرار دارد و با سیستم چندزبانه تداخلی ندارد (هر زبان محتوای ترجمه‌شده پست مرتبط را متناسب با زبان جاری کاربر رندر می‌کند).
* **مدل `PostTranslation`:**
  - فیلد `short_description = models.TextField(blank=True, null=True)` اضافه شد تا توضیحات خلاصه کارت‌ها و متای سئو به ازای هر زبان به صورت مجزا ذخیره شود.
* **مدل `Category`:**
  - فیلد `icon = models.FileField(upload_to="categories/icons/", null=True, blank=True)` اضافه شد تا آیکون‌های دسته‌بندی با فرمت‌های مختلف به ویژه **SVG** به درستی پشتیبانی و ذخیره شوند. وضعیت `is_active` نیز از پیش از طریق ارث‌بری از `BaseModel` وجود داشت.

### ب) ایجاد مدل‌های جدید در `posts/models.py`
* **مدل `PodcastCategory` (دسته‌بندی پادکست):**
  - ارث‌بری از `BaseModel` (شامل فیلدهای زمان ایجاد، ویرایش و وضعیت فعال بودن).
  - شامل فیلدهای `title` (عنوان)، `slug` (اسلاگ یکتا با پشتیبانی از یونیکد برای سئو) و `icon` به صورت `FileField` برای پشتیبانی از تصاویر و فرمت SVG.
* **مدل `Podcast` (اپیزود پادکست):**
  - شامل فیلدهای اطلاعات پایه: `title`, `slug` (یکتا)، `category` (رابطه کلید خارجی به `PodcastCategory`)، `episode_number` (شماره اپیزود) و `cover_image` (تصویر کاور).
  - شامل فیلدهای رسانه: `audio_file` (فایل صوتی)، `media_type` (نوع رسانه با گزینه‌های صوتی و ویدئویی)، `video_file` (فایل ویدئو) و `video_url` (لینک ویدئو جهت انعطاف بیشتر ادمین).
  - شامل فیلدهای محتوایی و آماری: `description` (توضیحات با فیلد پیشرفته Rich Text پروژه از نوع `CKEditor5Field`)، `duration` (مدت زمان به دقیقه)، `published_date` (زمان انتشار)، `view_count` (تعداد بازدید با مقدار اولیه ۰) و `related_podcasts` (رابطه چند به چند با خود پادکست).
* **مدل `GalleryItem` (گالری تصاویر با استایل پولاروید):**
  - شامل فیلدهای `image` (تصویر اصلی گالری)، `caption` (عنوان زیر عکس)، `order` (ترتیب نمایش عددی جهت مرتب‌سازی راحت ادمین)، `link` (آدرس اینترنتی اختیاری) و ارث‌بری از `BaseModel` برای فیلد `is_active`.

---

## ۳. هماهنگی بخش‌های وابسته پروژه (System Integration)

برای آماده‌سازی نهایی و پروداکشن بودن تغییرات، تمامی لایه‌های پروژه بازنویسی و هماهنگ شدند:

### ۱. لایه پایگاه داده و مهاجرت‌ها (Migrations):
- فایل میگریشن امن `0006_galleryitem_podcastcategory_category_icon_and_more.py` تولید شد. تمامی فیلدها با قابلیت Null بودن یا مقادیر پیش‌فرض تعریف شده‌اند تا از هرگونه از دست رفتن داده‌های قبلی جلوگیری شود. قابلیت Rollback کامل با اجرای دستور مهاجرت به نسخه قبلی برقرار است.

### ۲. لایه سریالایزرها (`posts/serializers.py`):
- فیلد `icon` به `CategorySerializer` اضافه شد.
- فیلد `short_description` به `PostListSerializer` و `PostDetailSerializer` اضافه شد.
- فیلد `related_posts` با استفاده از نمایش کامل `PostListSerializer(many=True)` در `PostDetailSerializer` پیاده‌سازی شد.
- در `PostCreateUpdateSerializer` فیلدهای `short_description` و `related_post_ids` (به صورت PrimaryKeyRelatedField با قابلیت نوشتن برای ارتباط ManyToMany) با موفقیت پیاده‌سازی و در متدهای `create` و `update` هندل شدند.
- سریالایزرهای جدید `PodcastCategorySerializer`، `PodcastSerializer` (به همراه فیلد تاریخ جلالی `published_date_jalali` و نرمال‌سازی محتوای ادیتور از طریق `ContentNormalizationMixin`) و `GalleryItemSerializer` ایجاد شدند.

### ۳. لایه ویوها و آدرس‌ها (`posts/views.py` & `posts/urls.py`):
- ایجاد `PodcastCategoryViewSet` با قابلیت فیلترینگ و جستجو.
- ایجاد `PodcastViewSet` با قابلیت فیلتر بر اساس دسته‌بندی و نوع رسانه، مرتب‌سازی و افزایش خودکار تعداد بازدید اپیزود (`view_count`) به ازای هر بار خواندن جزئیات اپیزود (Retrieve API).
- ایجاد `GalleryItemViewSet` با قابلیت مرتب‌سازی بر اساس فیلد ترتیب (`order`).
- ثبت تمامی مسیرهای جدید در Router اپلیکیشن `posts`.

### ۴. پنل مدیریت ادمین جنگو (`posts/admin.py`):
- ارتقای `CategoryAdmin` جهت پیش‌نمایش آیکون و اسلاگ‌سازی خودکار.
- ارتقای `PostAdmin` جهت اضافه شدن فیلد مقالات مرتبط به صورت `filter_horizontal` و مدیریت آسان‌تر روابط.
- ثبت ادمین مدل‌های `PodcastCategory` و `GalleryItem` به همراه قابلیت ادیت درجا (list_editable) برای فیلد ترتیب و وضعیت گالری.
- ثبت ادمین مدل `Podcast` با استفاده از `ModelAdminJalaliMixin` جهت نمایش زیبای شمسی تاریخ انتشار و گروه‌بندی فیلدها در قالب Fieldsetها.

### ۵. لایه تست و پایداری (Testing):
- تعریف فکتوری‌های تست جدید در `posts/factories.py` برای پادکست‌ها، دسته‌بندی‌ها و گالری.
- ایجاد فایل تست جامع `posts/blog_tests/test_new_content_models.py` شامل ۵ تست مجزای یکپارچه‌سازی و API جهت پوشش ۱۰۰٪ مدل‌ها، اعتبارسنجی‌ها، سطح دسترسی‌ها و مکانیزم افزایش بازدید خودکار.
- اجرای تست‌های کل سیستم با دستور `python manage.py test` که با موفقیت ۱۷۷ تست پروژه را بدون کوچکترین خطا پاس کرد.

---

## ۴. مستندات نمونه پاسخ‌های API (Sample Response Real Payload)

### دسته‌بندی پادکست‌ها (`GET /api/posts/podcast-categories/`):
```json
[
  {
    "id": 1,
    "title": "معماری",
    "slug": "architecture",
    "icon": "/media/podcasts/categories/icons/arch.svg",
    "is_active": true
  }
]
```

### اپیزودهای پادکست (`GET /api/posts/podcasts/`):
```json
[
  {
    "id": 1,
    "title": "قواعد بازی زندگی",
    "slug": "rules-of-life",
    "category": 1,
    "category_detail": {
      "id": 1,
      "title": "معماری",
      "slug": "architecture",
      "icon": "/media/podcasts/categories/icons/arch.svg",
      "is_active": true
    },
    "episode_number": 60,
    "cover_image": "/media/podcasts/covers/cover.jpg",
    "audio_file": "/media/podcasts/audio/ep60.mp3",
    "media_type": "audio",
    "video_file": null,
    "video_url": null,
    "description": "این اپیزود درباره قواعد بازی زندگی و چگونگی هدایت ذهن است.",
    "duration": 45,
    "published_date": "2026-07-11T12:00:00Z",
    "published_date_jalali": "1405/04/20 15:30:00",
    "view_count": 12,
    "related_podcasts": [],
    "is_active": true
  }
]
```

---

## ۵. دستورات لازم جهت Deploy در پروداکشن
برای اعمال تغییرات در سرور اصلی، دستورات زیر را به ترتیب اجرا نمایید:

```bash
# ۱. فعال‌سازی محیط مجازی و نصب وابستگی‌ها (در صورت تغییر)
pip install -r requirements.txt

# ۲. اعمال میگریشن‌های جدید روی پایگاه داده به صورت کاملا زنده و امن
python manage.py migrate

# ۳. جمع‌آوری فایل‌های استاتیک جدید ادمین پنل
python manage.py collectstatic --noinput

# ۴. اجرای خودکار تست‌های واحد و یکپارچگی جهت تایید نهایی صحت عملکرد
python manage.py test
```
