import os
import subprocess

from celery import shared_task

from common.utils.images import convert_image_to_avif


def optimize_image(image_field):
    """
    EN:
    Optimizes an image by converting it to AVIF format and compressing it.
    AVIF offers superior compression compared to JPEG/PNG.
    This function uses the robust convert_image_to_avif utility.

    FA:
    بهینه‌سازی تصویر با تبدیل آن به فرمت AVIF و فشرده‌سازی آن.
    فرمت AVIF فشرده‌سازی برتری نسبت به JPEG/PNG ارائه می‌دهد.
    این تابع از ابزار قدرتمند convert_image_to_avif استفاده می‌کند.

    Args:
        image_field: The image file to optimize.

    Returns:
        dict: A dictionary containing the 'buffer' and 'filename' of the optimized image.
    """
    try:
        # EN: Use the robust conversion utility to ensure transparency and ICC profiles are handled.
        # FA: استفاده از ابزار تبدیل قدرتمند برای اطمینان از مدیریت شفافیت و پروفایل‌های ICC.
        avif_content = convert_image_to_avif(image_field, quality=85)

        return {"buffer": avif_content, "filename": avif_content.name}

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
