# راهنمای جامع و عملی استفاده از APIهای ساخت مقاله به همراه عکس و گالری

این مستند شامل آموزش گام‌به‌گام و کامل نحوه لاگین، احراز هویت، و ساخت ۲ مقاله کامل با تصاویر کاور، تصاویر درون‌متنی و گالری تصاویـر با استفاده از APIهای سیستم مدیریت محتوا (CMS) می‌باشد.

---

## فهرست مطالب
1. [روش‌های لاگین و احراز هویت (Authentication)](#۱-روشهای-لاگین-و-احراز-هویت-authentication)
2. [دو روش اصلی برای ساخت مقاله با تصاویر (Workflows)](#۲-دو-روش-اصلی-برای-ساخت-مقاله-با-تصاویر-workflows)
3. [ساخت مقاله اول (با آپلود همزمان کاور، عکس درون‌متنی و گالری)](#۳-ساخت-مقاله-اول-با-آپلود-همزمان-کاور-عکس-درونمتنی-و-گالری)
4. [ساخت مقاله دوم (با تصاویر موجود و آپلود جدید)](#۴-ساخت-مقاله-دوم-با-تصاویر-موجود-و-آپلود-جدید)
5. [نمونه کدهای آماده به زبان‌های cURL، Python و JavaScript](#۵-نمونه-کدهای-آماده-به-زبانهای-curl-python-و-javascript)
6. [نحوه دریافت و نمایش مقاله ساخته شده](#۶-نحوه-دریافت-و-نمایش-مقاله-ساخته-شده)

---

## ۱. روش‌های لاگین و احراز هویت (Authentication)

برای ارسال درخواست ایجاد مقاله، باید هویت کاربر/نویسنده تأیید شود. دو روش پشتیبانی می‌شود:

### روش ۱: لاگین با توکن JWT (روش استاندارد کاربران و نویسندگان)
ابتدا نام کاربری و رمز عبور را به اندپوینت لاگین ارسال می‌کنید:

* **اندپوینت لاگین:** `POST /api/token/` یا `POST /api/auth/admin-login/`
* **بدنه درخواست (JSON):**
  ```json
  {
    "username": "author_user",
    "password": "your_password"
  }
  ```
* **پاسخ دریافتی:**
  ```json
  {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
* **نحوه استفاده در درخواست‌های بعدی:**
  در تمام درخواست‌های ساخت مقاله یا آپلود رسانه، هدر زیر را قرار دهید:
  ```http
  Authorization: Bearer <access_token>
  ```

---

### روش ۲: کلید API ثابت (Static API Key - ویژه تست، توسعه و سیستم‌های داخلی)
در محیط‌های تست یا ارتباطات سرویس به سرویس، نیازی به لاگین و توکن JWT نیست:
* **هدر الزامی:**
  ```http
  X-API-Key: your_configured_static_api_key
  ```
* **هدر اختیاری (برای شبیه‌سازی کاربر مشخص):**
  ```http
  X-Test-User: author_username
  ```

---

## ۲. دو روش اصلی برای ساخت مقاله با تصاویر (Workflows)

### روش ۱: آپلود یکپارچه درون‌خطی (Single Request Inline Upload) — *پیشنهادی و سریع‌ترین روش*
در این روش، شما **تنها با یک درخواست HTTP** از نوع `multipart/form-data`، اطلاعات مقاله و تمام فایل‌های باینری تصویر (کاور، تصویر درون متن، تصاویر گالری) را همزمان ارسال می‌کنید.
* **مزیت:** نیازی به ثبت جداگانه رسانه‌ها نیست؛ سیستم به‌صورت خودکار تصاویر را ذخیره کرده، شناسه‌های رسانه (`media_id`) را ایجاد نموده و در ساختار JSON مقاله قرار می‌دهد.

### روش ۲: فرآیند دومرحله‌ای (Two-Step / Media-First Workflow)
1. ابتدا تصاویر را تک‌تک یا گروهی به اندپوینت `POST /api/medias/` آپلود کرده و `media_id`های عددی (مثلاً `42`, `43`, `44`) دریافت می‌کنید.
2. سپس درخواست ساخت مقاله را با فرمت `application/json` به `POST /api/articles/` فرستاده و از این شناسه در فیلدهای `cover_image_id` یا `media_id` بلوک‌ها استفاده می‌کنید.

---

## ۳. ساخت مقاله اول (با آپلود همزمان کاور، عکس درون‌متنی و گالری)

### اطلاعات کلی درخواست مقاله ۱:
* **متد و آدرس:** `POST /api/articles/`
* **نوع محتوا (Content-Type):** `multipart/form-data`

### فیلدهای فرم (Form-Data Fields):

| نام فیلد (Field Name) | نوع | توضیحات |
| :--- | :--- | :--- |
| `language_code` | Text | کد زبان مقاله (مثلاً `fa`) |
| `title` | Text | عنوان مقاله |
| `excerpt` | Text | چکیده یا خلاصه کوتاه مقاله |
| `status` | Text | وضعیت مقاله (`draft` یا `published`) |
| `cover_image_id` | File | فایل باینری عکس کاور اصلی مقاله |
| `content_blocks` | Text (JSON String) | رشته JSON حاوی بلوک‌های محتوای مقاله |
| `file_intro.jpg` | File | فایل باینری تصویر درون‌متنی |
| `gal1.jpg` | File | فایل باینری تصویر اول گالری |
| `gal2.jpg` | File | فایل باینری تصویر دوم گالری |

### ساختار رشته JSON در فیلد `content_blocks`:

```json
[
  {
    "id": "blk_heading_1",
    "type": "heading",
    "version": 1,
    "order": 1,
    "data": {
      "level": 2,
      "text": "مقدمه‌ای بر هوش مصنوعی در سال ۲۰۲۶"
    }
  },
  {
    "id": "blk_para_1",
    "type": "paragraph",
    "version": 1,
    "order": 2,
    "data": {
      "content": [
        {
          "type": "text",
          "value": "هوش مصنوعی با سرعت بالایی در حال تغییر صنایع مختلف است..."
        }
      ]
    }
  },
  {
    "id": "blk_img_1",
    "type": "image",
    "version": 1,
    "order": 3,
    "file": "file_intro.jpg",
    "data": {
      "caption": "تصویر تحلیلی هوش مصنوعی",
      "alt": "نمودار هوش مصنوعی"
    }
  },
  {
    "id": "blk_gal_1",
    "type": "gallery",
    "version": 1,
    "order": 4,
    "files": ["gal1.jpg", "gal2.jpg"],
    "data": {
      "layout": "grid",
      "caption": "گالری تصاویر رویدادهای هوش مصنوعی"
    }
  }
]
```

> **نکته کلیدی:** در بلوک تصویر تک‌تایی از کلید `"file": "نام_فایل"` و در بلوک گالری از آرایه `"files": ["اسم_فایل۱", "اسم_فایل۲"]` استفاده کنید. نام‌ها باید دقیقاً با نام فیلدهای ارسال‌شده در `multipart/form-data` مطابقت داشته باشند.

---

## ۴. ساخت مقاله دوم (با تصاویر موجود و آپلود جدید)

در مقاله دوم، فرض کنید می‌خواهیم از یک تصویر که قبلاً در سیستم ثبت شده (با شناسه `media_id: 10`) استفاده کنیم و همزمان یک تصویر جدید هم آپلود نماییم.

### اطلاعات کلی درخواست مقاله ۲:
* **متد و آدرس:** `POST /api/articles/`
* **نوع محتوا:** `multipart/form-data`

### فیلدهای فرم (Form-Data Fields):

| نام فیلد | نوع | مقدار |
| :--- | :--- | :--- |
| `language_code` | Text | `fa` |
| `title` | Text | راهنمای جامع معماری نرم‌افزار تمیز (Clean Architecture) |
| `excerpt` | Text | چگونه نرم‌افزارهای مقیاس‌پذیر و قابل نگهداری بسازیم؟ |
| `status` | Text | `published` |
| `cover_image_id` | Text | `10` *(استفاده از شناسه رسانه موجود برای کاور)* |
| `content_blocks` | Text (JSON String) | *مطابق JSON زیر* |
| `clean_arch_diagram.png` | File | فایل باینری نمودار معماری |

### ساختار رشته JSON در فیلد `content_blocks` برای مقاله دوم:

```json
[
  {
    "id": "blk_h2_1",
    "type": "heading",
    "version": 1,
    "order": 1,
    "data": {
      "level": 2,
      "text": "اصول لایه‌بندی در Clean Architecture"
    }
  },
  {
    "id": "blk_p_1",
    "type": "paragraph",
    "version": 1,
    "order": 2,
    "data": {
      "content": [
        {
          "type": "text",
          "value": "جداسازی منطق کسب‌وکار از جزئیات فریم‌ورک‌ها اهمیت زیادی دارد..."
        }
      ]
    }
  },
  {
    "id": "blk_img_new",
    "type": "image",
    "version": 1,
    "order": 3,
    "file": "clean_arch_diagram.png",
    "data": {
      "caption": "نمودار لایه‌های Clean Architecture",
      "alt": "نمودار لایه‌بندی"
    }
  },
  {
    "id": "blk_img_existing",
    "type": "image",
    "version": 1,
    "order": 4,
    "data": {
      "media_id": 10,
      "caption": "تصویر مرجع معماری (رسانه از قبل موجود)",
      "alt": "عکس مرجع"
    }
  }
]
```

---

## ۵. نمونه کدهای آماده به زبان‌های cURL، Python و JavaScript

### نمونه ۱: cURL (ارسال مستقیم از ترمینال)

```bash
curl -X POST http://localhost:8000/api/articles/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "language_code=fa" \
  -F "title=مقاله نمونه اول با cURL" \
  -F "excerpt=توضیحات مختصر مقاله اول" \
  -F "status=published" \
  -F "cover_image_id=@/path/to/cover.jpg" \
  -F 'content_blocks=[
    {
      "id": "b1",
      "type": "paragraph",
      "version": 1,
      "order": 1,
      "data": {
        "content": [{"type": "text", "value": "متن اصلی مقاله..."}]
      }
    },
    {
      "id": "b2",
      "type": "image",
      "version": 1,
      "order": 2,
      "file": "file_intro.jpg",
      "data": { "caption": "تصویر اول" }
    },
    {
      "id": "b3",
      "type": "gallery",
      "version": 1,
      "order": 3,
      "files": ["gal1.jpg", "gal2.jpg"],
      "data": { "layout": "grid" }
    }
  ]' \
  -F "file_intro.jpg=@/path/to/intro.jpg" \
  -F "gal1.jpg=@/path/to/gallery1.jpg" \
  -F "gal2.jpg=@/path/to/gallery2.jpg"
```

---

### نمونه ۲: پایتون (Python - کتابخانه `requests`)

```python
import json
import requests

API_URL = "http://localhost:8000/api/articles/"
TOKEN = "YOUR_ACCESS_TOKEN"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

content_blocks = [
    {
        "id": "b1",
        "type": "heading",
        "version": 1,
        "order": 1,
        "data": {"level": 2, "text": "عنوان مقاله پایتون"}
    },
    {
        "id": "b2",
        "type": "paragraph",
        "version": 1,
        "order": 2,
        "data": {
            "content": [{"type": "text", "value": "این مقاله توسط اسکریپت پایتون ایجاد شده است."}]
        }
    },
    {
        "id": "b3",
        "type": "image",
        "version": 1,
        "order": 3,
        "file": "file_intro.jpg",
        "data": {"caption": "توضیح تصویر پایتون"}
    }
]

# فایل‌های باینری جهت ارسال
files = {
    'cover_image_id': ('cover.jpg', open('cover.jpg', 'rb'), 'image/jpeg'),
    'file_intro.jpg': ('intro.jpg', open('intro.jpg', 'rb'), 'image/jpeg'),
}

data = {
    'language_code': 'fa',
    'title': 'مقاله ساخته شده با پایتون',
    'excerpt': 'چکیده مقاله پایتون',
    'status': 'published',
    'content_blocks': json.dumps(content_blocks, ensure_ascii=False)
}

response = requests.post(API_URL, headers=headers, data=data, files=files)
print("Status Code:", response.status_code)
print("Response JSON:", response.json())
```

---

### نمونه ۳: جاوااسکریپت (JavaScript - مرورگر یا Node.js)

```javascript
async function createArticle() {
  const formData = new FormData();

  formData.append('language_code', 'fa');
  formData.append('title', 'مقاله ساخته شده با جاوااسکریپت');
  formData.append('excerpt', 'توضیحات مقاله JS');
  formData.append('status', 'published');

  // افزودن فایل کاور
  const coverFileInput = document.querySelector('#coverInput');
  if (coverFileInput.files[0]) {
    formData.append('cover_image_id', coverFileInput.files[0]);
  }

  // افزودن فایل تصویر درون متن
  const introFileInput = document.querySelector('#introInput');
  if (introFileInput.files[0]) {
    formData.append('file_intro.jpg', introFileInput.files[0]);
  }

  const contentBlocks = [
    {
      id: "b1",
      type: "paragraph",
      version: 1,
      order: 1,
      data: {
        content: [{ type: "text", value: "متن مقاله ارسال شده از کلاینت جاوااسکریپت." }]
      }
    },
    {
      id: "b2",
      type: "image",
      version: 1,
      order: 2,
      file: "file_intro.jpg",
      data: { caption: "تصویر آپلود شده با JS" }
    }
  ];

  formData.append('content_blocks', JSON.stringify(contentBlocks));

  const response = await fetch('http://localhost:8000/api/articles/', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer YOUR_ACCESS_TOKEN'
      // توجه: در FormData نباید Content-Type را دستی تنظیم کنید؛ مرورگر خودش boundary را اضافه می‌کند.
    },
    body: formData
  });

  const result = await response.json();
  console.log('Article Created:', result);
}
```

---

## ۶. نحوه دریافت و نمایش مقاله ساخته شده

پس از ثبت مقاله، جهت دریافت مقاله ساختاریافته برای نمایش در فرانت‌اند (وب یا موبایل)، می‌توانید از اندپوینت‌های زیر استفاده کنید:

* **لیست مقالات:** `GET /api/articles/`
* **جزئیات مقاله با اسلاگ (Slug):** `GET /api/articles/{slug}/`

### نمونه پاسخ خروجی مقاله‌ی غنی‌شده (JSON Contract Response):

```json
{
  "status": "success",
  "data": {
    "id": 101,
    "language_code": "fa",
    "slug": "mghalh-sakhtah-shdh-ba-payton",
    "title": "مقاله ساخته شده با پایتون",
    "excerpt": "چکیده مقاله پایتون",
    "status": "published",
    "published_at": "1404/08/07 14:20:00",
    "cover_image": {
      "id": 85,
      "url": "https://cdn.example.com/media/cover.jpg",
      "variants": {
        "thumbnail": "https://cdn.example.com/variants/85/thumbnail.webp",
        "medium": "https://cdn.example.com/variants/85/medium.webp"
      }
    },
    "blocks": [
      {
        "id": "b1",
        "type": "heading",
        "order": 1,
        "data": { "level": 2, "text": "عنوان مقاله پایتون" }
      },
      {
        "id": "b3",
        "type": "image",
        "order": 3,
        "data": {
          "media_id": 86,
          "caption": "توضیح تصویر پایتون",
          "media": {
            "id": 86,
            "url": "https://cdn.example.com/media/intro.jpg",
            "variants": {
              "thumbnail": "https://cdn.example.com/variants/86/thumbnail.webp",
              "medium": "https://cdn.example.com/variants/86/medium.webp"
            }
          }
        }
      }
    ]
  },
  "messagesList": []
}
```

پاسخ فوق تمام مشخصات تصویر (شامل آدرس اصلی، نسخه `webp` و سایزهای مختلف) را به صورت خودکار بسط داده و آماده استفاده در React / Next.js / Vue یا اپلیکیشن‌های موبایل می‌باشد.
