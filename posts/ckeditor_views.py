from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from common.utils.files import get_sanitized_filename
from common.utils.images import convert_image_to_avif
from medias.models import Media


@login_required
@csrf_exempt
def ckeditor_upload_view(request):
    """
    EN:
    Custom upload view for CKEditor 5.
    Handles image uploads, converts them to AVIF, and creates a corresponding Media object.
    Restricts access to staff or authors.

    FA:
    نمای آپلود سفارشی برای CKEditor 5.
    آپلود تصاویر را مدیریت کرده، آن‌ها را به AVIF تبدیل می‌کند و شیء Media متناظر را ایجاد می‌کند.
    دسترسی را به کارکنان یا نویسندگان محدود می‌کند.
    """
    # EN: Permission check: User must be staff or an author
    # FA: بررسی دسترسی: کاربر باید جزو کارکنان یا نویسندگان باشد
    is_author = hasattr(request.user, "author_profile")
    if not (request.user.is_staff or is_author):
        return HttpResponseForbidden("You do not have permission to upload files.")

    if request.method == "POST" and request.FILES.get("upload"):
        uploaded_file = request.FILES["upload"]

        # EN: Check if the uploaded file is an image
        # FA: بررسی اینکه فایل آپلود شده تصویر باشد
        if "image" not in uploaded_file.content_type:
            return JsonResponse(
                {"error": "The uploaded file is not an image."}, status=400
            )

        # EN: Convert the image to AVIF for storage optimization
        # FA: تبدیل تصویر به AVIF برای بهینه‌سازی ذخیره‌سازی
        try:
            avif_file = convert_image_to_avif(uploaded_file, quality=60, speed=4)
        except Exception as e:
            return JsonResponse({"error": f"Error processing image: {e}"}, status=500)

        # EN: Save the converted file using default storage
        # FA: ذخیره فایل تبدیل شده با استفاده از فضای ذخیره‌سازی پیش‌فرض
        sanitized_name = get_sanitized_filename(avif_file.name)
        storage_key = default_storage.save(sanitized_name, avif_file)
        file_url = default_storage.url(storage_key)

        # EN: Create a Media object for the new AVIF image
        # FA: ایجاد یک شیء Media برای تصویر AVIF جدید
        Media.objects.create(
            storage_key=storage_key,
            url=file_url,
            mime="image/avif",  # EN: Explicitly set the MIME type for AVIF
            # FA: تنظیم صریح نوع MIME برای AVIF
            size_bytes=avif_file.size,
            title=sanitized_name,
            uploaded_by=request.user,
            type="image",
        )

        return JsonResponse({"url": file_url})

    return JsonResponse({"error": "Invalid request."}, status=400)
