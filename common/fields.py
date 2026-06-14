from django.db.models import FileField, ImageField
from django.db.models.fields.files import FieldFile, ImageFieldFile


class OptimizedImageFieldFile(ImageFieldFile):
    """
    EN: Custom FieldFile for OptimizedImageField. Optimization disabled.
    FA: یک FieldFile سفارشی برای OptimizedImageField. بهینه‌سازی غیرفعال شده است.
    """

    def save(self, name, content, save=True):
        """
        EN: Saves the original content directly.
        FA: محتوای اصلی را مستقیماً ذخیره می‌کند.
        """
        super().save(name, content, save)


class OptimizedImageField(ImageField):
    """
    EN: A Django ImageField. Optimization disabled.
    FA: یک ImageField جنگو. بهینه‌سازی غیرفعال شده است.
    """

    attr_class = OptimizedImageFieldFile


class OptimizedVideoFieldFile(FieldFile):
    """
    EN: Custom FieldFile for OptimizedVideoField. Optimization disabled.
    FA: یک FieldFile سفارشی برای OptimizedVideoField. بهینه‌سازی غیرفعال شده است.
    """

    def save(self, name, content, save=True):
        """
        EN: Saves the original content directly.
        FA: محتوای اصلی را مستقیماً ذخیره می‌کند.
        """
        super().save(name, content, save)


class OptimizedVideoField(FileField):
    """
    EN: A Django FileField. Optimization disabled.
    FA: یک FileField جنگو. بهینه‌سازی غیرفعال شده است.
    """

    attr_class = OptimizedVideoFieldFile


class OptimizedFileFieldFile(FieldFile):
    """
    EN: Custom FieldFile for OptimizedFileField. Optimization disabled.
    FA: یک FieldFile سفارشی برای OptimizedFileField. بهینه‌سازی غیرفعال شده است.
    """

    def save(self, name, content, save=True):
        """
        EN: Saves the original content directly.
        FA: محتوای اصلی را مستقیماً ذخیره می‌کند.
        """
        super().save(name, content, save)


class OptimizedFileField(FileField):
    """
    EN: A Django FileField. Optimization disabled.
    FA: یک FileField جنگو. بهینه‌سازی غیرفعال شده است.
    """

    attr_class = OptimizedFileFieldFile
