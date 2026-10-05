from django.contrib import admin

from accounts.permissions import can_review_documents
from .models import Scholarship, ScholarshipApplication


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "opens_on", "closes_on", "is_published", "is_demo")
    list_filter = ("is_published", "is_demo", "provider")
    search_fields = ("name", "provider")

    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.is_staff and request.user.role in {"ADMIN", "SUPER_ADMIN"}


@admin.register(ScholarshipApplication)
class ScholarshipApplicationAdmin(admin.ModelAdmin):
    list_display = ("scholarship", "user", "status", "submitted_at", "reviewed_by")
    list_filter = ("status", "submitted_at", "scholarship")
    search_fields = ("user__email", "scholarship__name")
    readonly_fields = ("submitted_at", "updated_at", "reviewed_by")
    filter_horizontal = ("documents",)

    def save_model(self, request, obj, form, change):
        if obj.status != ScholarshipApplication.Status.SUBMITTED:
            obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return can_review_documents(request.user)

    def has_view_permission(self, request, _obj=None):
        del _obj
        return can_review_documents(request.user)

    def has_add_permission(self, _request):
        del _request
        return False

    def has_change_permission(self, request, _obj=None):
        del _obj
        return request.user.is_authenticated and request.user.is_staff and request.user.role in {"ADMIN", "SUPER_ADMIN"}

    def has_delete_permission(self, request, _obj=None):
        del _obj
        return request.user.is_authenticated and request.user.is_superuser and request.user.role == "SUPER_ADMIN"
