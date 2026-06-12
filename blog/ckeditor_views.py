from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import Http404, JsonResponse
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.forms import UploadFileForm
from django_ckeditor_5.views import (
    NoImageException,
    handle_uploaded_file,
    image_verify,
)


def _error_response(message, status=400):
    return JsonResponse({"error": {"message": message}}, status=status)


def ckeditor5_upload(request):
    if request.method != "POST":
        raise Http404(_("Page not found."))

    if not request.user.is_staff:
        return _error_response(
            _(
                "You do not have permission to upload. Please log in with an account that has appropriate access."
            ),
            status=403,
        )

    form = UploadFileForm(request.POST, request.FILES)
    allow_all_file_types = getattr(settings, "CKEDITOR_5_ALLOW_ALL_FILE_TYPES", False)

    try:
        upload_file = request.FILES["upload"]
    except KeyError:
        return _error_response(_("No file has been sent for upload."))

    if not allow_all_file_types:
        try:
            image_verify(upload_file)
            upload_file.seek(0)
        except NoImageException:
            return _error_response(
                _(
                    "The selected file is not a valid image. Please upload one of the supported formats."
                ),
            )

    if form.is_valid():
        try:
            url = handle_uploaded_file(upload_file)
        except ValidationError as exc:
            return _error_response(" ".join(exc.messages))
        except Exception:
            return _error_response(
                _("File upload failed. Please try again."), status=500
            )

        return JsonResponse({"url": url})

    error_messages = []
    for field_errors in form.errors.get_json_data().values():
        for err in field_errors:
            message = err.get("message")
            if message:
                error_messages.append(message)

    detail = " ".join(error_messages).strip()
    if not detail:
        detail = _("The submitted file is not valid. Please check its format and size.")

    return _error_response(detail)
