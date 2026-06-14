from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from common.utils.files import get_sanitized_filename
from medias.models import Media


@login_required
@csrf_exempt
def ckeditor_upload_view(request):
    """
    EN:
    Custom upload view for CKEditor 5.
    Handles image uploads and creates a corresponding Media object.
    Optimization (AVIF conversion) has been removed.

    FA:
    نمای آپلود سفارشی برای CKEditor 5.
    آپلود تصاویر را مدیریت کرده و شیء Media متناظر را ایجاد می‌کند.
    بهینه‌سازی (تبدیل به AVIF) حذف شده است.
    """
    is_author = hasattr(request.user, "author_profile")
    if not (request.user.is_staff or is_author):
        return HttpResponseForbidden("You do not have permission to upload files.")

    if request.method == "POST" and request.FILES.get("upload"):
        uploaded_file = request.FILES["upload"]

        if "image" not in uploaded_file.content_type:
            return JsonResponse(
                {"error": "The uploaded file is not an image."}, status=400
            )

        sanitized_name = get_sanitized_filename(uploaded_file.name)
        storage_key = default_storage.save(sanitized_name, uploaded_file)
        file_url = default_storage.url(storage_key)

        Media.objects.create(
            storage_key=storage_key,
            url=file_url,
            mime=uploaded_file.content_type,
            size_bytes=uploaded_file.size,
            title=sanitized_name,
            uploaded_by=request.user,
            type="image",
        )

        return JsonResponse({"url": file_url})

    return JsonResponse({"error": "Invalid request."}, status=400)
