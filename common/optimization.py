import os
import subprocess
from io import BytesIO

from celery import shared_task
from PIL import Image


def optimize_image(image_field):
    """
    EN:
    Optimizes an image by converting it to AVIF format and compressing it.
    AVIF offers superior compression compared to JPEG/PNG.

    FA:
    بهینه‌سازی تصویر با تبدیل آن به فرمت AVIF و فشرده‌سازی آن.
    فرمت AVIF فشرده‌سازی برتری نسبت به JPEG/PNG ارائه می‌دهد.

    Args:
        image_field: The image file to optimize.

    Returns:
        dict: A dictionary containing the 'buffer' and 'filename' of the optimized image.
    """
    try:
        img = Image.open(image_field)

        # EN: Convert RGBA to RGB if necessary for AVIF compatibility
        # FA: تبدیل RGBA به RGB در صورت نیاز برای سازگاری با AVIF
        if img.mode == "RGBA":
            img = img.convert("RGB")

        # EN: Create a buffer to save the optimized image
        # FA: ایجاد یک بافر برای ذخیره تصویر بهینه‌سازی شده
        buffer = BytesIO()
        img.save(buffer, format="AVIF", quality=85, optimize=True)
        buffer.seek(0)

        # EN: Get the original filename without extension
        # FA: دریافت نام اصلی فایل بدون پسوند
        filename = os.path.splitext(image_field.name)[0]
        new_filename = f"{filename}.avif"

        return {"buffer": buffer, "filename": new_filename}

    except Exception as e:
        # EN: Handle exceptions (e.g., corrupted images)
        # FA: مدیریت خطاها (مثلاً تصاویر خراب)
        print(f"Error optimizing image: {e}")
        return None


@shared_task
def optimize_video(video_path):
    """
    EN:
    Optimizes a video by compressing it using FFmpeg.
    This task reduces video file size using libx264 codec.

    FA:
    بهینه‌سازی ویدیو با فشرده‌سازی آن با استفاده از FFmpeg.
    این تسک حجم فایل ویدیو را با استفاده از کدک libx264 کاهش می‌دهد.

    Args:
        video_path (str): The absolute path to the video file.
    """
    try:
        # EN: Get the original filename without extension
        # FA: دریافت نام اصلی فایل بدون پسوند
        filename, ext = os.path.splitext(video_path)
        new_filename = f"{filename}_optimized.mp4"

        # EN: Run ffmpeg to compress the video. CRF 28 is a good balance between quality and size.
        # FA: اجرای ffmpeg برای فشرده‌سازی ویدیو. CRF 28 توازن خوبی بین کیفیت و حجم است.
        command = [
            "ffmpeg",
            "-i",
            video_path,
            "-vcodec",
            "libx264",
            "-crf",
            "28",
            new_filename,
        ]
        subprocess.run(command, check=True)

        # EN: Replace the original file with the optimized one
        # FA: جایگزینی فایل اصلی با فایل بهینه‌سازی شده
        os.replace(new_filename, video_path)

    except Exception as e:
        # EN: Handle exceptions (e.g., ffmpeg not installed)
        # FA: مدیریت خطاها (مثلاً نصب نبودن ffmpeg)
        print(f"Error optimizing video: {e}")
