from django.core.files.storage import default_storage
from common.utils.images import convert_image_to_avif
from common.utils.files import get_sanitized_filename
from PIL import Image
from .models import Media

def create_media_from_file(uploaded_file, uploaded_by, alt_text='', title=''):
    original_content_type = uploaded_file.content_type
    is_image = 'image' in original_content_type

    if is_image:
        processed_file = convert_image_to_avif(uploaded_file)
        mime = 'image/avif'
    else:
        processed_file = uploaded_file
        mime = original_content_type

    sanitized_name = get_sanitized_filename(processed_file.name)
    storage_key = default_storage.save(sanitized_name, processed_file)
    file_url = default_storage.url(storage_key)

    if not title:
        title = sanitized_name

    media_data = {
        'storage_key': storage_key,
        'url': file_url,
        'size_bytes': processed_file.size,
        'mime': mime,
        'title': title,
        'alt_text': alt_text,
        'uploaded_by': uploaded_by,
    }

    if is_image:
        media_data['type'] = 'image'
        try:
            processed_file.seek(0)
            with Image.open(processed_file) as img:
                media_data['width'] = img.width
                media_data['height'] = img.height
        except Exception:
            media_data['width'] = None
            media_data['height'] = None
    elif 'video' in original_content_type:
        media_data['type'] = 'video'
    else:
        media_data['type'] = 'file'

    return Media.objects.create(**media_data)
