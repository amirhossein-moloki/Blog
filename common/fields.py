from django.core.files.base import ContentFile
from django.db.models import FileField, ImageField
from django.db.models.fields.files import FieldFile, ImageFieldFile

from common.optimization import optimize_image, optimize_video


class OptimizedImageFieldFile(ImageFieldFile):
    """
    EN: Custom FieldFile for OptimizedImageField that handles image optimization on save.
    FA: یک FieldFile سفارشی برای OptimizedImageField که بهینه‌سازی تصویر را هنگام ذخیره‌سازی مدیریت می‌کند.
    """

    def save(self, name, content, save=True):
        """
        EN: Optimizes the image before saving it to the storage.
        FA: قبل از ذخیره تصویر در فضای ذخیره‌سازی، آن را بهینه‌سازی می‌کند.
        """
        # EN: Optimize the image before saving
        # FA: بهینه‌سازی تصویر قبل از ذخیره‌سازی
        optimization_result = optimize_image(content)
        if optimization_result:
            buffer = optimization_result["buffer"]
            filename = optimization_result["filename"]
            # EN: Save the optimized content
            # FA: ذخیره محتوای بهینه‌سازی شده
            super().save(filename, ContentFile(buffer.read()), save)
        else:
            # EN: Save the original content if optimization fails
            # FA: ذخیره محتوای اصلی در صورت شکست بهینه‌سازی
            super().save(name, content, save)


class OptimizedImageField(ImageField):
    """
    EN: A Django ImageField that automatically optimizes uploaded images.
    FA: یک ImageField جنگو که به طور خودکار تصاویر آپلود شده را بهینه‌سازی می‌کند.
    """

    attr_class = OptimizedImageFieldFile


class OptimizedVideoFieldFile(FieldFile):
    """
    EN: Custom FieldFile for OptimizedVideoField that triggers video optimization.
    FA: یک FieldFile سفارشی برای OptimizedVideoField که فرآیند بهینه‌سازی ویدیو را اجرا می‌کند.
    """

    def save(self, name, content, save=True):
        """
        EN: Saves the video and triggers an asynchronous optimization task.
        FA: ویدیو را ذخیره کرده و یک تسک نامتقارن برای بهینه‌سازی آن اجرا می‌کند.
        """
        # EN: Call the parent save method first
        # FA: ابتدا متد ذخیره کلاس والد فراخوانی می‌شود
        super().save(name, content, save)
        # EN: Then, trigger the video optimization task
        # FA: سپس، تسک بهینه‌سازی ویدیو اجرا می‌شود
        optimize_video.delay(self.path)


class OptimizedVideoField(FileField):
    """
    EN: A Django FileField that automatically triggers video optimization.
    FA: یک FileField جنگو که به طور خودکار بهینه‌سازی ویدیو را اجرا می‌کند.
    """

    attr_class = OptimizedVideoFieldFile


class OptimizedFileFieldFile(FieldFile):
    """
    EN: Custom FieldFile for OptimizedFileField that handles both images and videos.
    FA: یک FieldFile سفارشی برای OptimizedFileField که هم تصاویر و هم ویدیوها را مدیریت می‌کند.
    """

    def save(self, name, content, save=True):
        """
        EN: Identifies file type and applies appropriate optimization.
        FA: نوع فایل را شناسایی کرده و بهینه‌سازی مناسب را اعمال می‌کند.
        """
        # EN: Check the file extension
        # FA: بررسی پسوند فایل
        ext = name.split(".")[-1].lower()
        if ext in ["jpg", "jpeg", "png", "webp"]:
            optimization_result = optimize_image(content)
            if optimization_result:
                buffer = optimization_result["buffer"]
                filename = optimization_result["filename"]
                super().save(filename, ContentFile(buffer.read()), save)
            else:
                super().save(name, content, save)
        else:
            super().save(name, content, save)
            if ext in ["mp4", "mov", "avi", "mkv"]:
                # EN: Trigger asynchronous video optimization for common video formats.
                # FA: اجرای تسک نامتقارن بهینه‌سازی ویدیو برای فرمت‌های رایج ویدیو.
                optimize_video.delay(self.path)


class OptimizedFileField(FileField):
    """
    EN: A Django FileField that optimizes images and triggers video optimization.
    FA: یک FileField جنگو که تصاویر را بهینه‌سازی کرده و بهینه‌سازی ویدیو را اجرا می‌کند.
    """

    attr_class = OptimizedFileFieldFile
