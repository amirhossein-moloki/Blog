# راهنمای جامع قرارداد داده‌ای Headless CMS: فرآیند ایجاد و خروجی مقاله نمونه (خانه علوی تبریز)

این مستند فنی به بررسی عمیق و تشریح دو بخش کلیدی در معماری سیستم مدیریت محتوای مستقل از نمایش (Presentation-Agnostic Headless CMS) راسته می‌پردازد:
1. **ساختار درخواست ارسالی (Multipart Form-Data Payload)**: چگونگی ایجاد مقاله به همراه آپلود همزمان تصاویر جدید و استفاده از تصاویر موجود در سیستم.
2. **ساختار پاسخ خروجی (Headless JSON Response Contract)**: خروجی استاندارد و غنی‌شده API پس از پردازش، بومی‌سازی، ایمن‌سازی و بسط داینامیک رسانه‌ها.

---

## ۱. مرور کلی بر جریان فرآیند (Workflow Overview)

سیستم ما به صورت یکپارچه از دو فرآیند کاری مستقل پشتیبانی می‌کند:

*   **فرآیند رسانه‌محور (Media-First Workflow)**: ابتدا فایل رسانه آپلود شده، شناسه عددی (`media_id`) دریافت شده و سپس در ساختار JSON بلوک‌ها قرار می‌گیرد.
*   **فرآیند مقاله‌محور (Article-First Workflow)**: نویسنده هنگام نگارش پیش‌نویس مقاله، فایل تصویر را مستقیماً در فیلد بلوک قرار می‌دهد. کلاینت یک درخواست چندبخشی (`multipart/form-data`) ارسال می‌کند که شامل آرایه بلوک‌ها و فایل‌های باینری است. سریالایزر جنگو به طور خودکار فایل‌ها را استخراج، در کتابخانه رسانه ذخیره و شناسه‌های تولید شده را جایگزین فیلدهای موقت می‌کند.

---

## ۲. ساختار درخواست ارسالی (Multipart Form-Data Request)

وقتی کاربر می‌خواهد مقاله نمونه **«خانه علوی (موزه سفال)»** را بسازد و همزمان:
1. **کاور اصلی** مقاله (شناسه ۵۰۱) را از تصاویر موجود انتخاب کند.
2. تصویر بخش مقدمه (`blk_image_intro`) را با آپلود یک **فایل جدید** جایگزین کند.
3. تصویر بخش تاریخچه (`blk_image_history`) را از تصاویر موجود (شناسه ۵۰۳) قرار دهد.
4. گالری معماری (`blk_gallery_arch`) را ترکیبی از دو تصویر موجود (شناسه‌های ۵۰۲ و ۵۰۳) و دو تصویر آپلود شده همزمان قرار دهد.

درخواست چندبخشی (`multipart/form-data`) ارسالی کلاینت به شکل زیر خواهد بود:

### فیلدهای استاندارد فرم (Form-Data Fields)

| نام فیلد (Key) | نوع داده | توضیحات | مقدار نمونه |
| :--- | :--- | :--- | :--- |
| `language_code` | Text | کد زبان مقاله جهت ایجاد ترجمه متناظر | `fa` |
| `title` | Text | عنوان اصلی مقاله | خانه علوی (موزه سفال)؛ نگاهی عمیق به تاریخ خانه‌های قدیمی تبریز |
| `excerpt` | Text | خلاصه یا چکیده مقاله برای لیست‌ها | بررسی تاریخچه، معماری و ارزش فرهنگی خانه علوی تبریز... |
| `status` | Text | وضعیت انتشار مقاله | `published` |
| `cover_image_id` | Text/File | فیلد هیبریدی رسانه (شناسه عددی موجود یا فایل باینری) | `501` |
| `content_blocks` | Text (JSON String) | ساختار درختی بلوک‌های محتوا به صورت رشته متنی JSON | *در جدول زیر به تفصیل تشریح شده است* |

### ساختار بلوک‌های محتوا درون فیلد `content_blocks`

رشته متنی JSON ارسالی در فیلد `content_blocks` حاوی ارجاع‌های ترکیبی (شناسه‌های عددی رسانه و نام فایل‌های آپلود شده) خواهد بود:

```json
[
  {
    "id": "blk_toc_001",
    "type": "accordion",
    "version": 1,
    "order": 1,
    "data": {
      "items": [
        { "title": "مقدمه", "content": "مقدمه و آشنایی با خانه علوی" },
        { "title": "تاریخچه", "content": "پیشینه و قدمت تاریخی بنا" },
        { "title": "معماری", "content": "ویژگی‌های معماری و ساختاری موزه سفال" },
        { "title": "نتیجه‌گیری", "content": "جمع‌بندی و کاربرد فعلی بنا" }
      ]
    }
  },
  {
    "id": "blk_heading_intro",
    "type": "heading",
    "version": 1,
    "order": 2,
    "data": {
      "level": 2,
      "text": "مقدمه",
      "anchor_id": "intro"
    }
  },
  {
    "id": "blk_para_intro",
    "type": "paragraph",
    "version": 1,
    "order": 3,
    "data": {
      "content": [
        {
          "type": "text",
          "value": "شهر تبریز به عنوان یکی از مهم‌ترین شهرهای تاریخی ایران، همواره دارای جایگاه ویژه‌ای در عرصه فرهنگ، هنر و معماری بوده است. وجود بناهای ارزشمند تاریخی در این شهر، گواهی بر پیشینه غنی و هویت فرهنگی آن است."
        }
      ]
    }
  },
  {
    "id": "blk_image_intro",
    "type": "image",
    "version": 1,
    "order": 4,
    "data": {
      "file": "new-intro-yard.jpg",
      "caption": "حیاط مرکزی خانه علوی تبریز",
      "alt": "نمای حیاط تاریخی خانه علوی",
      "loading": "lazy",
      "object_fit": "cover",
      "focal_point": { "x": 0.5, "y": 0.5 }
    }
  },
  {
    "id": "blk_heading_history",
    "type": "heading",
    "version": 1,
    "order": 5,
    "data": {
      "level": 2,
      "text": "تاریخچه",
      "anchor_id": "history"
    }
  },
  {
    "id": "blk_para_history",
    "type": "paragraph",
    "version": 1,
    "order": 6,
    "data": {
      "content": [
        {
          "type": "text",
          "value": "خانه علوی در تبریز، خیابان شمس تبریزی، کوچه صرافالر واقع شده است. این بنا با شماره ثبت ۷۸۰۳ در فهرست آثار ملی ایران ثبت شده و قدمت آن مربوط به دوره قاجاریه و پهلوی می‌باشد."
        }
      ]
    }
  },
  {
    "id": "blk_image_history",
    "type": "image",
    "version": 1,
    "order": 7,
    "data": {
      "media_id": 503,
      "caption": "نمای ایوان ستون‌دار خانه علوی",
      "alt": "ایوان تاریخی خانه علوی تبریز"
    }
  },
  {
    "id": "blk_gallery_arch",
    "type": "gallery",
    "version": 1,
    "order": 8,
    "data": {
      "media_ids": [502, 503],
      "files": ["new-gallery-detail1.png", "new-gallery-detail2.png"],
      "layout": "grid",
      "aspect_ratio": "16:9"
    }
  },
  {
    "id": "blk_heading_result",
    "type": "heading",
    "version": 1,
    "order": 9,
    "data": {
      "level": 2,
      "text": "نتیجه‌گیری",
      "anchor_id": "conclusion"
    }
  },
  {
    "id": "blk_para_result",
    "type": "paragraph",
    "version": 1,
    "order": 10,
    "data": {
      "content": [
        {
          "type": "text",
          "value": "خانه علوی تبریز یکی از نمونه‌های ارزشمند معماری مسکونی اواخر دوره قاجار و اوایل دوره پهلوی است که با حفظ عناصر معماری سنتی، امروزه به عنوان موزه سفال و مرکز آموزش سفالگری مورد استفاده قرار می‌گیرد."
        }
      ]
    }
  },
  {
    "id": "blk_faq_arch",
    "type": "faq",
    "version": 1,
    "order": 11,
    "data": {
      "questions": [
        {
          "q": "آیا خانه علوی تبریز ثبت ملی شده است؟",
          "a": "بله، این بنا با شماره ثبت ۷۸۰۳ در فهرست آثار ملی ایران به ثبت رسیده است."
        },
        {
          "q": "موزه سفال تبریز در کجا واقع شده است؟",
          "a": "این موزه در خیابان شمس تبریزی، کوچه صرافالر واقع شده است."
        }
      ]
    }
  }
]
```

### فیلدهای مربوط به فایل‌های پیوست (Uploaded Files)

برای اینکه فرآیند «مقاله اول» کار کند، کاربر فایل‌های باینری زیر را همزمان در بدنه درخواست ارسال می‌کند. هدر هر فایل باید شامل نوع MIME درست باشد:

1.  **فایل ۱ (فیلد `new-intro-yard.jpg`)**:
    *   **Filename**: `new-intro-yard.jpg`
    *   **Content-Type**: `image/jpeg`
    *   **هدف**: اختصاص به عنوان تصویر بلوک `blk_image_intro` (از طریق تطابق با کلید `"file"` در بلوک).
2.  **فایل ۲ (فیلد `new-gallery-detail1.png`)**:
    *   **Filename**: `new-gallery-detail1.png`
    *   **Content-Type**: `image/png`
    *   **هدف**: قرارگیری در آرایه گالری بلوک `blk_gallery_arch`.
3.  **فایل ۳ (فیلد `new-gallery-detail2.png`)**:
    *   **Filename**: `new-gallery-detail2.png`
    *   **Content-Type**: `image/png`
    *   **هدف**: قرارگیری در آرایه گالری بلوک `blk_gallery_arch`.

---

## ۳. ساختار پاسخ خروجی (Headless JSON Response)

پس از ثبت موفق درخواست در بک‌اند، عملیات زیر به صورت متوالی رخ می‌دهد:
1.  **پردازش و ذخیره فایل‌ها**: تصاویر آپلود شده اعتبار سنجی چندمرحله‌ای (امضای باینری یا Magic Signature و اسکن بدافزار) شده، در سیستم رسانه ذخیره می‌شوند و شناسه‌های جدید (مثلاً ۵۰۴، ۵۰۵ و ۵۰۶) به آن‌ها تعلق می‌گیرد.
2.  **سازماندهی ترتیب بلوک‌ها**: بلوک‌ها بر اساس ترتیبی یکپارچه مجدداً اندیس‌گذاری شده و فیلدهای موقت `file`/`files` حذف و با `media_id` واقعی جایگزین می‌شوند.
3.  **بسط داینامیک رسانه‌ها (Batch Expansion)**: کلاینت هنگام واکشی مقاله، جزئیات کامل رسانه (شامل آدرس انواع نسخه‌های ریسپانسیو و پیش‌نمایش تاری یا BlurHash) را دریافت می‌کند.
4.  **تجمیع سئو در سطح سند**: داده‌های ساختاریافته موتور جستجو (مانند FAQ schema و Breadcrumbs) به صورت خودکار از درون بلوک‌ها استخراج شده و در آرایه جامع `structured_data` در سطح اول سند رندر می‌شوند.

پاسخ دریافت شده توسط کلاینت از آدرس `GET /api/v1/articles/khaneh-alavi-tabriz-museum-sofal/` به شرح زیر است:

```json
{
  "status": "success",
  "data": {
    "id": 250,
    "language_code": "fa",
    "slug": "khaneh-alavi-tabriz-museum-sofal",
    "title": "خانه علوی (موزه سفال)؛ نگاهی عمیق به تاریخ خانه‌های قدیمی تبریز",
    "excerpt": "بررسی تاریخچه، معماری و ارزش فرهنگی خانه علوی تبریز به عنوان یکی از بناهای ارزشمند تاریخی این شهر.",
    "short_description": "بررسی تاریخچه، معماری و ارزش فرهنگی خانه علوی تبریز به عنوان یکی از بناهای ارزشمند تاریخی این شهر.",
    "reading_time_sec": 120,
    "status": "published",
    "is_hot": false,
    "published_at": "1405/05/08 15:30:00",
    "article_schema_version": 2,
    "author": {
      "display_name": "تیم محتوای راسته",
      "avatar": {
        "id": 99,
        "url": "https://cdn.example.com/media/author-rasteh.jpg",
        "mime": "image/jpeg"
      }
    },
    "cover_image": {
      "id": 501,
      "storage_key": "khaneh-alavi-cover.jpg",
      "url": "https://cdn.example.com/media/khaneh-alavi-cover.jpg",
      "type": "image",
      "mime": "image/jpeg",
      "width": 1920,
      "height": 1080,
      "size_bytes": 450120,
      "alt_text": "نمای کاور خانه تاریخی علوی تبریز",
      "title": "Kaver Khaneh Alavi",
      "status": "Ready",
      "dominant_color": "#8c7255",
      "blur_hash": "LHD]Bf_3%Mxu~q%M_3of_3WBMyay",
      "storage_provider": "local",
      "metadata": {
        "width": 1920,
        "height": 1080,
        "mime": "image/jpeg",
        "size": 450120
      },
      "variants": {
        "thumbnail": "https://cdn.example.com/variants/501/thumbnail.webp",
        "small": "https://cdn.example.com/variants/501/small.webp",
        "medium": "https://cdn.example.com/variants/501/medium.webp",
        "large": "https://cdn.example.com/variants/501/large.webp"
      }
    },
    "structured_data": [
      {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
          {
            "@type": "Question",
            "name": "آیا خانه علوی تبریز ثبت ملی شده است؟",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "بله، این بنا با شماره ثبت ۷۸۰۳ در فهرست آثار ملی ایران به ثبت رسیده است."
            }
          },
          {
            "@type": "Question",
            "name": "موزه سفال تبریز در کجا واقع شده است؟",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "این موزه در خیابان شمس تبریزی، کوچه صرافالر واقع شده است."
            }
          }
        ]
      }
    ],
    "blocks": [
      {
        "id": "blk_toc_001",
        "type": "accordion",
        "version": 1,
        "order": 1,
        "settings": {
          "align": "left",
          "spacing": "md",
          "theme": "default",
          "visibility": "visible",
          "animation": "none",
          "width": "contained",
          "container": "default",
          "responsive": {},
          "custom_class": null
        },
        "meta": {
          "locked": false,
          "hidden": false,
          "created_by": null,
          "updated_by": null,
          "draft": false,
          "deleted": false,
          "internal_notes": ""
        },
        "data": {
          "items": [
            { "title": "مقدمه", "content": "مقدمه و آشنایی با خانه علوی" },
            { "title": "تاریخچه", "content": "پیشینه و قدمت تاریخی بنا" },
            { "title": "معماری", "content": "ویژگی‌های معماری و ساختاری موزه سفال" },
            { "title": "نتیجه‌گیری", "content": "جمع‌بندی و کاربرد فعلی بنا" }
          ]
        }
      },
      {
        "id": "blk_heading_intro",
        "type": "heading",
        "version": 1,
        "order": 2,
        "settings": {
          "align": "left",
          "spacing": "md",
          "theme": "default",
          "visibility": "visible",
          "animation": "none",
          "width": "contained",
          "container": "default",
          "responsive": {},
          "custom_class": null
        },
        "meta": {
          "locked": false,
          "hidden": false,
          "created_by": null,
          "updated_by": null,
          "draft": false,
          "deleted": false,
          "internal_notes": ""
        },
        "data": {
          "level": 2,
          "text": "مقدمه",
          "anchor_id": "intro"
        }
      },
      {
        "id": "blk_para_intro",
        "type": "paragraph",
        "version": 1,
        "order": 3,
        "settings": {
          "align": "left",
          "spacing": "md",
          "theme": "default",
          "visibility": "visible",
          "animation": "none",
          "width": "contained",
          "container": "default",
          "responsive": {},
          "custom_class": null
        },
        "meta": {
          "locked": false,
          "hidden": false,
          "created_by": null,
          "updated_by": null,
          "draft": false,
          "deleted": false,
          "internal_notes": ""
        },
        "data": {
          "content": [
            {
              "type": "text",
              "value": "شهر تبریز به عنوان یکی از مهم‌ترین شهرهای تاریخی ایران، همواره دارای جایگاه ویژه‌ای در عرصه فرهنگ، هنر و معماری بوده است. وجود بناهای ارزشمند تاریخی در این شهر، گواهی بر پیشینه غنی و هویت فرهنگی آن است."
            }
          ]
        }
      },
      {
        "id": "blk_image_intro",
        "type": "image",
        "version": 1,
        "order": 4,
        "settings": {
          "align": "left",
          "spacing": "md",
          "theme": "default",
          "visibility": "visible",
          "animation": "none",
          "width": "contained",
          "container": "default",
          "responsive": {},
          "custom_class": null
        },
        "meta": {
          "locked": false,
          "hidden": false,
          "created_by": null,
          "updated_by": null,
          "draft": false,
          "deleted": false,
          "internal_notes": ""
        },
        "data": {
          "media_id": 504,
          "caption": "حیاط مرکزی خانه علوی تبریز",
          "alt": "نمای حیاط تاریخی خانه علوی",
          "loading": "lazy",
          "object_fit": "cover",
          "focal_point": { "x": 0.5, "y": 0.5 },
          "media": {
            "id": 504,
            "storage_key": "new-intro-yard.jpg",
            "url": "https://cdn.example.com/media/new-intro-yard.jpg",
            "type": "image",
            "mime": "image/jpeg",
            "width": 1200,
            "height": 800,
            "size_bytes": 182400,
            "alt_text": "نمای حیاط تاریخی خانه علوی",
            "title": "new-intro-yard.jpg",
            "uploaded_by": 1,
            "status": "Ready",
            "dominant_color": "#7a6e5b",
            "blur_hash": "LEHLt#_3%Mxu~q_3_3of_3WBMyay",
            "storage_provider": "local",
            "metadata": {
              "width": 1200,
              "height": 800,
              "mime": "image/jpeg",
              "size": 182400
            },
            "variants": {
              "thumbnail": "https://cdn.example.com/variants/504/thumbnail.webp",
              "small": "https://cdn.example.com/variants/504/small.webp",
              "medium": "https://cdn.example.com/variants/504/medium.webp"
            }
          }
        }
      },
      {
        "id": "blk_heading_history",
        "type": "heading",
        "version": 1,
        "order": 5,
        "settings": {
          "align": "left",
          "spacing": "md",
          "theme": "default",
          "visibility": "visible",
          "animation": "none",
          "width": "contained",
          "container": "default",
          "responsive": {},
          "custom_class": null
        },
        "meta": {
          "locked": false,
          "hidden": false,
          "created_by": null,
          "updated_by": null,
          "draft": false,
          "deleted": false,
          "internal_notes": ""
        },
        "data": {
          "level": 2,
          "text": "تاریخچه",
          "anchor_id": "history"
        }
      },
      {
        "id": "blk_para_history",
        "type": "paragraph",
        "version": 1,
        "order": 6,
        "settings": {
          "align": "left",
          "spacing": "md",
          "theme": "default",
          "visibility": "visible",
          "animation": "none",
          "width": "contained",
          "container": "default",
          "responsive": {},
          "custom_class": null
        },
        "meta": {
          "locked": false,
          "hidden": false,
          "created_by": null,
          "updated_by": null,
          "draft": false,
          "deleted": false,
          "internal_notes": ""
        },
        "data": {
          "content": [
            {
              "type": "text",
              "value": "خانه علوی در تبریز، خیابان شمس تبریزی، کوچه صرافالر واقع شده است. این بنا با شماره ثبت ۷۸۰۳ در فهرست آثار ملی ایران ثبت شده و قدمت آن مربوط به دوره قاجاریه و پهلوی می‌باشد."
            }
          ]
        }
      },
      {
        "id": "blk_image_history",
        "type": "image",
        "version": 1,
        "order": 7,
        "settings": {
          "align": "left",
          "spacing": "md",
          "theme": "default",
          "visibility": "visible",
          "animation": "none",
          "width": "contained",
          "container": "default",
          "responsive": {},
          "custom_class": null
        },
        "meta": {
          "locked": false,
          "hidden": false,
          "created_by": null,
          "updated_by": null,
          "draft": false,
          "deleted": false,
          "internal_notes": ""
        },
        "data": {
          "media_id": 503,
          "caption": "نمای ایوان ستون‌دار خانه علوی",
          "alt": "ایوان تاریخی خانه علوی تبریز",
          "media": {
            "id": 503,
            "storage_key": "khaneh-alavi-porch.jpg",
            "url": "https://cdn.example.com/media/khaneh-alavi-porch.jpg",
            "type": "image",
            "mime": "image/jpeg",
            "width": 1600,
            "height": 900,
            "size_bytes": 312040,
            "alt_text": "ایوان تاریخی خانه علوی تبریز",
            "title": "Khaneh Alavi Porch",
            "uploaded_by": 1,
            "status": "Ready",
            "dominant_color": "#aa8866",
            "blur_hash": "LGD*gf_3%Mxu~q%M_3of_3WBMyay",
            "storage_provider": "local",
            "metadata": {
              "width": 1600,
              "height": 900,
              "mime": "image/jpeg",
              "size": 312040
            },
            "variants": {
              "thumbnail": "https://cdn.example.com/variants/503/thumbnail.webp",
              "small": "https://cdn.example.com/variants/503/small.webp",
              "medium": "https://cdn.example.com/variants/503/medium.webp",
              "large": "https://cdn.example.com/variants/503/large.webp"
            }
          }
        }
      },
      {
        "id": "blk_gallery_arch",
        "type": "gallery",
        "version": 1,
        "order": 8,
        "settings": {
          "align": "left",
          "spacing": "md",
          "theme": "default",
          "visibility": "visible",
          "animation": "none",
          "width": "contained",
          "container": "default",
          "responsive": {},
          "custom_class": null
        },
        "meta": {
          "locked": false,
          "hidden": false,
          "created_by": null,
          "updated_by": null,
          "draft": false,
          "deleted": false,
          "internal_notes": ""
        },
        "data": {
          "media_ids": [502, 503, 505, 506],
          "layout": "grid",
          "aspect_ratio": "16:9",
          "medias": [
            {
              "id": 502,
              "storage_key": "yard.jpg",
              "url": "https://cdn.example.com/media/yard.jpg",
              "type": "image",
              "mime": "image/jpeg",
              "width": 1200,
              "height": 800,
              "size_bytes": 190400,
              "variants": {
                "thumbnail": "https://cdn.example.com/variants/502/thumbnail.webp",
                "medium": "https://cdn.example.com/variants/502/medium.webp"
              }
            },
            {
              "id": 503,
              "storage_key": "khaneh-alavi-porch.jpg",
              "url": "https://cdn.example.com/media/khaneh-alavi-porch.jpg",
              "type": "image",
              "mime": "image/jpeg",
              "width": 1600,
              "height": 900,
              "size_bytes": 312040,
              "variants": {
                "thumbnail": "https://cdn.example.com/variants/503/thumbnail.webp",
                "medium": "https://cdn.example.com/variants/503/medium.webp"
              }
            },
            {
              "id": 505,
              "storage_key": "new-gallery-detail1.png",
              "url": "https://cdn.example.com/media/new-gallery-detail1.png",
              "type": "image",
              "mime": "image/png",
              "width": 1024,
              "height": 576,
              "size_bytes": 142050,
              "variants": {
                "thumbnail": "https://cdn.example.com/variants/505/thumbnail.webp",
                "medium": "https://cdn.example.com/variants/505/medium.webp"
              }
            },
            {
              "id": 506,
              "storage_key": "new-gallery-detail2.png",
              "url": "https://cdn.example.com/media/new-gallery-detail2.png",
              "type": "image",
              "mime": "image/png",
              "width": 1024,
              "height": 576,
              "size_bytes": 149120,
              "variants": {
                "thumbnail": "https://cdn.example.com/variants/506/thumbnail.webp",
                "medium": "https://cdn.example.com/variants/506/medium.webp"
              }
            }
          ]
        }
      },
      {
        "id": "blk_heading_result",
        "type": "heading",
        "version": 1,
        "order": 9,
        "settings": {
          "align": "left",
          "spacing": "md",
          "theme": "default",
          "visibility": "visible",
          "animation": "none",
          "width": "contained",
          "container": "default",
          "responsive": {},
          "custom_class": null
        },
        "meta": {
          "locked": false,
          "hidden": false,
          "created_by": null,
          "updated_by": null,
          "draft": false,
          "deleted": false,
          "internal_notes": ""
        },
        "data": {
          "level": 2,
          "text": "نتیجه‌گیری",
          "anchor_id": "conclusion"
        }
      },
      {
        "id": "blk_para_result",
        "type": "paragraph",
        "version": 1,
        "order": 10,
        "settings": {
          "align": "left",
          "spacing": "md",
          "theme": "default",
          "visibility": "visible",
          "animation": "none",
          "width": "contained",
          "container": "default",
          "responsive": {},
          "custom_class": null
        },
        "meta": {
          "locked": false,
          "hidden": false,
          "created_by": null,
          "updated_by": null,
          "draft": false,
          "deleted": false,
          "internal_notes": ""
        },
        "data": {
          "content": [
            {
              "type": "text",
              "value": "خانه علوی تبریز یکی از نمونه‌های ارزشمند معماری مسکونی اواخر دوره قاجار و اوایل دوره پهلوی است که با حفظ عناصر معماری سنتی، امروزه به عنوان موزه سفال و مرکز آموزش سفالگری مورد استفاده قرار می‌گیرد."
            }
          ]
        }
      },
      {
        "id": "blk_faq_arch",
        "type": "faq",
        "version": 1,
        "order": 11,
        "settings": {
          "align": "left",
          "spacing": "md",
          "theme": "default",
          "visibility": "visible",
          "animation": "none",
          "width": "contained",
          "container": "default",
          "responsive": {},
          "custom_class": null
        },
        "meta": {
          "locked": false,
          "hidden": false,
          "created_by": null,
          "updated_by": null,
          "draft": false,
          "deleted": false,
          "internal_notes": ""
        },
        "data": {
          "questions": [
            {
              "q": "آیا خانه علوی تبریز ثبت ملی شده است؟",
              "a": "بله، این بنا با شماره ثبت ۷۸۰۳ در فهرست آثار ملی ایران به ثبت رسیده است."
            },
            {
              "q": "موزه سفال تبریز در کجا واقع شده است؟",
              "a": "این موزه در خیابان شمس تبریزی، کوچه صرافالر واقع شده است."
            }
          ]
        }
      }
    ],
    "content_blocks": [
      { "ref": "این آرایه همسان با blocks برای سازگاری کامل با کلاینت‌های قدیمی‌تر بازگردانده می‌شود." }
    ],
    "media_attachments": [
      {
        "media": {
          "id": 501,
          "url": "https://cdn.example.com/media/khaneh-alavi-cover.jpg",
          "type": "image",
          "mime": "image/jpeg"
        },
        "attachment_type": "cover",
        "usage_count": 1,
        "referenced_by": ["article_meta"],
        "lock_status": true
      },
      {
        "media": {
          "id": 504,
          "url": "https://cdn.example.com/media/new-intro-yard.jpg",
          "type": "image",
          "mime": "image/jpeg"
        },
        "attachment_type": "in-content",
        "usage_count": 1,
        "referenced_by": ["blk_image_intro"],
        "lock_status": true
      },
      {
        "media": {
          "id": 503,
          "url": "https://cdn.example.com/media/khaneh-alavi-porch.jpg",
          "type": "image",
          "mime": "image/jpeg"
        },
        "attachment_type": "in-content",
        "usage_count": 2,
        "referenced_by": ["blk_image_history", "blk_gallery_arch"],
        "lock_status": true
      },
      {
        "media": {
          "id": 502,
          "url": "https://cdn.example.com/media/yard.jpg",
          "type": "image",
          "mime": "image/jpeg"
        },
        "attachment_type": "in-content",
        "usage_count": 1,
        "referenced_by": ["blk_gallery_arch"],
        "lock_status": true
      },
      {
        "media": {
          "id": 505,
          "url": "https://cdn.example.com/media/new-gallery-detail1.png",
          "type": "image",
          "mime": "image/png"
        },
        "attachment_type": "in-content",
        "usage_count": 1,
        "referenced_by": ["blk_gallery_arch"],
        "lock_status": true
      },
      {
        "media": {
          "id": 506,
          "url": "https://cdn.example.com/media/new-gallery-detail2.png",
          "type": "image",
          "mime": "image/png"
        },
        "attachment_type": "in-content",
        "usage_count": 1,
        "referenced_by": ["blk_gallery_arch"],
        "lock_status": true
      }
    ]
  },
  "messagesList": []
}
```

---

## ۴. تبیین استانداردهای استقلال از فرانت‌اند در این خروجی (Headless CMS Compliance)

1.  **حذف کامل کدهای خام HTML**: ساختار متنی پاراگراف‌ها کاملاً مستقل از کدهای نمایشی است و بر خلاف وبلاگ‌های سنتی به کدهای استایل یا HTML مجهز نیست. متن به صورت توکن‌گذاری شده تحویل داده می‌شود که در اپلیکیشن‌های اندروید و iOS با ابزارهای بومی و در وب با کامپوننت‌های بهینه‌سازی شده رندر می‌شود.
2.  **عدم ارجاع به نام کامپوننت‌ها (Component Agnosticism)**: فیلد `"component"` یا مقادیر اختصاصی فریمورک‌ها (مثل `"NextImage"`) در هیچ جای بدنه بلوک وجود ندارد. بلوک‌ها صرفاً از طریق کلید مستقل `"type"` مشخص می‌شوند و این وظیفه فرانت‌اند است که تصمیم بگیرد برای هر نوع (مثل `paragraph` یا `gallery`) چه ظاهر یا کامپوننتی را رندر کند.
3.  **یکپارچه‌سازی متاداده و ساختار**: مقادیر استایل‌ها و رفتارهای بصری کلاینت در بخش تنظیمات تعمیم‌یافته بلوک (`settings`) کپسوله‌سازی شده‌اند و مقادیر ممیزی و حفاظتی در آبجکت `meta` قرار گرفته‌اند تا تداخلی با اصل داده‌های معنایی (`data`) ایجاد نکنند.
4.  **تزریق داده‌های ساختاریافته وب به صورت متمرکز**: سئو وب‌سایت در سطح اول خروجی در یک آرایه مجزا به نام `structured_data` رندر شده است تا فریمورک فرانت‌اند (مانند Next.js) بتواند بدون خواندن کل بلوک‌ها، بلافاصله کدهای JSON-LD متناسب با استانداردهای گوگل را در بخش `<head>` تزریق کند.
5.  **مدیریت هوشمند آدرس رسانه‌ها و نسخه‌های ریسپانسیو**: آدرس مستقیم هاردکد شده فایل‌ها هیچگاه در دیتابیس بلوک ذخیره نمی‌شود. بک‌اند همواره در زمان سریالایز، آدرس و نسخه‌های مختلف هر رسانه را بر اساس CDN جاری استخراج کرده و به صورت پویا بسط می‌دهد.
6.  **قفل حفاظتی رسانه‌ها (Relational Reference Lock)**: جدول واسط `media_attachments` در پاسخ نشان می‌دهد که هر تصویر در کدام بلوک‌ها از کدام مقاله‌ها استفاده شده است. وجود این رکوردها مانع از حذف اتفاقی این تصاویر از کتابخانه رسانه می‌شود.
