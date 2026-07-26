"""
EN: BDR Maintenance Middleware. Intercepts incoming requests when the system is under maintenance restoration.
FA: میان‌افزار تعمیرات و بازیابی سیستم. قطع دسترسی کاربران به سیستم در طول فرآیند بازیابی داده‌ها.
"""

from django.http import JsonResponse
from common.bdr.maintenance_lock import MaintenanceLockManager


class BDRMaintenanceMiddleware:
    """
    EN: Middleware that returns HTTP 503 Service Unavailable when a maintenance lock is active.
    FA: میان‌افزاری که در صورت فعال بودن قفل تعمیرات سیستم، خطای ۵۰۳ را به کاربران بازمی‌گرداند.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.lock_manager = MaintenanceLockManager()

    def __call__(self, request):
        if self.lock_manager.is_locked():
            return JsonResponse(
                {
                    "status": "maintenance",
                    "message": "System restoration in progress"
                },
                status=503
            )
        return self.get_response(request)
