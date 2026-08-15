# راهنمای جامع آپلود همزمان رسانه و ایجاد مقاله (Inline Media Upload Guide)

## ۱. مقدمه و پاسخ مستقیم (Overview & Capabilities)

**آیا امکان آپلود همزمان رسانه هنگام ایجاد مقاله وجود دارد؟**
**بله!** در این سیستم، هنگام ارسال درخواست ایجاد مقاله (`POST /api/articles/`) یا به‌روزرسانی آن (`PUT / PATCH /api/articles/{slug}/`)، می‌توانید تمام فایل‌های رسانه‌ای (تصاویر، ویدیوها، گالری‌ها و کاور مقاله) را **در همان یک درخواست (Single Multipart Request)** به همراه بدنه مقاله ارسال کنید.

بک‌اند سیستم به‌صورت خودکار فایل‌های آپلود شده را پردازش کرده، برای آن‌ها در کتابخانه رسانه (`medias.Media`) رکورد ساخته، شناسه رسانه (`media_id` یا `media_ids`) را تولید کرده و آن را به بلاک‌های مربوطه (`image` , `gallery` , `video`) و یا کاور مقاله (`cover_image`) متصل می‌کند.

---

## ۲. معماری پردازش درون‌خطی رسانه (Inline Media Processing Architecture)

سیستم از دو مكانیزم اصلی برای پردازش همزمان فایل‌ها بهره می‌برد:

1. **`process_inline_blocks_media` (در لایه Serializer):**
   پیش از اعتبارسنجی طرح‌واره (JSON Schema Validation) بلاک‌های محتوا (`content_blocks`)، سریالایزر فایل‌های ارسال شده در `request.FILES` را شناسایی کرده و فایل‌ها را بر اساس نام یا موقعیت به بلاک‌های `image` , `gallery` و `video` نسبت می‌دهد. فایل‌ها در حافظه ذخیره‌سازی ذخیره شده و رکوردهای `Media` ساخته می‌شوند و شناسه عددی آن‌ها (`media_id`) به دیتای بلاک تزریق می‌شود.

2. **`HybridMediaField` (برای `cover_image_id` و `og_image_id`):**
   فیلدهای کاور مقاله و تصویر شبکه‌های اجتماعی هبرید هستند؛ یعنی هم می‌توان شناسه عددی یک رسانه موجود (مثلاً `14`) را فرستاد و هم می‌توان فایل باینری تصویر را در همون فیلد Multipart آپلود نمود.

---

## ۳. روش‌های نگاشت فایل‌ها به بلاک‌ها (Mapping Strategies)

هنگام ساخت درخواست با `Content-Type: multipart/form-data`، می‌توانید فایل‌های خود را به ۳ روش به بلاک‌ها نگاشت کنید:

### روش ۱: نگاشت بر اساس نام فایل (Named File Reference)
در JSON بلاک، کلید `file` را برابر با نام دقیق فایل آپلود شده قرار دهید.

* **نمونه بلاک تصویر (`image`):**
  ```json
  {
    "id": "blk_img_1",
    "type": "image",
    "version": 1,
    "order": 1,
    "file": "chart_2026.png",
    "data": {
      "caption": "نمودار تحلیلی سال ۲۰۲۶",
      "alt": "نمودار رشد"
    }
  }
  ```
* **فایل همراه Multipart:**
  یک فایل با اسم `chart_2026.png` در درخواست فرم ارسال می‌شود.

---

### روش ۲: نگاشت گالری تصاویـر (`gallery`)
در بلاک گالری، می‌توانید لیستی از نام فایل‌ها را در کلید `files` مشخص کنید.

* **نمونه بلاک گالری (`gallery`):**
  ```json
  {
    "id": "blk_gal_1",
    "type": "gallery",
    "version": 1,
    "order": 2,
    "files": ["photo1.jpg", "photo2.jpg", "photo3.jpg"],
    "data": {
      "layout": "grid"
    }
  }
  ```
* **فایل‌های همراه Multipart:**
  سه فایل با نام‌های `photo1.jpg`, `photo2.jpg` و `photo3.jpg` در فرم ارسال می‌شوند.
* **نتیجه بک‌اند:**
  بک‌اند فایل‌ها را آپلود کرده و کلید `media_ids` را به‌صورت آرایه‌ای از شناسه رسانه‌ها تزریق می‌کند:
  ```json
  "data": {
    "layout": "grid",
    "media_ids": [101, 102, 103]
  }
  ```

---

### روش ۳: نگاشت ترتیبی / پوزیشنی (`image_file[]`)
اگر در بلاک تصویر یا ویدیو، فیلد `file` یا `media_id` تنظیم نشده باشد، سیستم به صورت ترتیبی فایل‌های موجود در کلید عمومی `image_file[]` یا `file`های درخواست را به بلاک‌ها اختصاص می‌دهد.

---

## ۴. بلاک ویدیو و شرایط ویژه آن (`video` block)

برای ویدیو دو سناریو وجود دارد:

1. **ویدیوی محلی (Local Upload):**
   * **ساختار JSON بلاک:**
     ```json
     {
       "id": "blk_vid_1",
       "type": "video",
       "version": 1,
       "order": 3,
       "file": "intro_video.mp4",
       "data": {
         "provider": "local",
         "controls": true,
         "autoplay": false
       }
     }
     ```
   * **فایل Multipart:** فایل با پسوند ویدیو (`.mp4`, `.mov`, `.avi`, `.mkv`) و MIME معتبر ویدیویی.
   * **نتیجه بک‌اند:** فایل در ذخیره‌ساز متمرکز ذخیره شده و `media_id` ویدیو در دیتای بلاک ثبت می‌شود.

2. **ویدیوی خارجی (External Video - YouTube / Vimeo):**
   * در این حالت نیازی به آپلود فایل نیست و فقط `external_url` و `provider` فرستاده می‌شود:
     ```json
     {
       "id": "blk_vid_ext",
       "type": "video",
       "version": 1,
       "order": 4,
       "data": {
         "provider": "youtube",
         "external_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
       }
     }
     ```

---

## ۵. آپلود کاور مقاله (`cover_image_id` / `og_image_id`)

فیلد `cover_image_id` در سطح اصلی مقاله قرار دارد و از `HybridMediaField` پشتیبانی می‌کند:
* می‌توانید یک شناسه عددی مانند `"cover_image_id": 42` بفرستید.
* **یا** می‌توانید فایل تصویر کاور را با کلید `cover_image_id` در فرم Multipart آپلود کنید. بک‌اند تصویر را آپلود کرده و به عنوان کاور مقاله ست می‌کند.

---

## ۶. اعتبارسنجی‌ها و الزامات امنیتی (Security & Validation)

1. **احراز هویت:** کاربر ارسال‌کننده باید لاگین بوده یا API Key معتبر داشته باشد (`IsAuthenticated`).
2. **اعتبارسنجی ساختار فایل (MIME & Magic Bytes):** پسوند فایل، ساختار باینری و امضای Magic بررسی می‌شود. فایل‌های اسکریپتی (`.php`, `.js`, HTML) و فایل‌های اجرایی مطلقا رد می‌شوند.
3. **جلوگیری از آپلود تکراری (SHA-256 Deduplication):** برای صرفه‌جویی در حافظه، هش SHA-256 فایل محاسبه می‌شود. اگر فایلی با همان محتوا قبلاً آپلود شده باشد، رکورد همان `Media` بازاستفاده می‌شود.
4. **تولید خودکار نسخه‌ها (Media Variants):** پس از آپلود موفق تصاویر، نسخه‌های بهینه‌شده (`thumbnail`, `small`, `medium`, `large` و فرمت `WebP`) به صورت خودکار ایجاد می‌شوند.

---

## ۷. نمونه کامل درخواست cURL

```bash
curl -X POST http://localhost:8000/api/articles/ \
  -H "X-API-Key: your_static_api_key" \
  -F "language_code=fa" \
  -F "title=مقاله جدید به همراه تصاویر درون‌خطی" \
  -F "excerpt=توضیحات مختصر مقاله" \
  -F "status=draft" \
  -F "cover_image_id=@/path/to/cover.jpg" \
  -F 'content_blocks=[
    {
      "id": "blk_1",
      "type": "paragraph",
      "version": 1,
      "order": 1,
      "data": {
        "content": [{"type": "text", "value": "متن پاراگراف اول..."}]
      }
    },
    {
      "id": "blk_2",
      "type": "image",
      "version": 1,
      "order": 2,
      "file": "chart.jpg",
      "data": {
        "caption": "نمودار سالانه",
        "alt": "تصویر نمودار"
      }
    },
    {
      "id": "blk_3",
      "type": "gallery",
      "version": 1,
      "order": 3,
      "files": ["g1.jpg", "g2.jpg"],
      "data": {
        "layout": "grid"
      }
    },
    {
      "id": "blk_4",
      "type": "video",
      "version": 1,
      "order": 4,
      "file": "intro.mp4",
      "data": {
        "provider": "local",
        "controls": true
      }
    }
  ]' \
  -F "chart.jpg=@/path/to/chart.jpg" \
  -F "g1.jpg=@/path/to/g1.jpg" \
  -F "g2.jpg=@/path/to/g2.jpg" \
  -F "intro.mp4=@/path/to/intro.mp4"
```

---

## English Summary

The CMS fully supports single-request article creation with simultaneous inline media file uploads (`image`, `gallery`, `video` blocks, as well as `cover_image_id` and `og_image_id`).
- Form Data Content-Type: `multipart/form-data`.
- In `content_blocks` JSON array:
  - For single images/videos: set `"file": "filename.ext"`.
  - For galleries: set `"files": ["pic1.jpg", "pic2.jpg"]`.
- Attach binary files in the same request with matching field names.
- The backend (`process_inline_blocks_media` and `HybridMediaField`) transparently validates files, creates `Media` objects, inserts generated `media_id` / `media_ids` into the JSON structure, and runs schema validation and database persistence.
