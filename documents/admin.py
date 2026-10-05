from django.contrib import admin

from accounts.permissions import ADMIN_ROLES, can_review_documents
from .models import Document, DocumentAccessLog, DocumentType


@admin.action(description="Mark selected documents verified")
def mark_verified(_modeladmin, request, queryset):
    del _modeladmin
    for document in queryset:
        document.status = Document.Status.VERIFIED
        document.verification_source = Document.VerificationSource.ADMIN_REVIEW
        document.rejection_reason = ""
        document.save(update_fields=["status", "verification_source", "rejection_reason"])
        DocumentAccessLog.objects.create(document=document, actor=request.user, action="VERIFY")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "doc_type", "status", "uploaded_at", "expiry_date")
    list_filter = ("status", "doc_type", "uploaded_at")
    search_fields = ("owner__email", "doc_type__name")
    readonly_fields = ("owner", "file", "uploaded_at", "status", "verification_source", "rejection_reason")
    actions = (mark_verified,)

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
        return request.user.is_authenticated and request.user.is_staff and request.user.role in ADMIN_ROLES

    def has_delete_permission(self, request, _obj=None):
        del _obj
        return request.user.is_authenticated and request.user.is_staff and request.user.role in ADMIN_ROLES


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "validity_months")
    search_fields = ("name",)

    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.is_staff and request.user.role in ADMIN_ROLES


@admin.register(DocumentAccessLog)
class DocumentAccessLogAdmin(admin.ModelAdmin):
    list_display = ("document_reference", "document", "actor", "action", "at")
    readonly_fields = ("document_reference", "document", "actor", "action", "at")

    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.is_staff and request.user.role in ADMIN_ROLES

    def has_add_permission(self, _request):
        del _request
        return False

    def has_change_permission(self, _request, _obj=None):
        del _request, _obj
        return False

    def has_delete_permission(self, request, _obj=None):
        del _obj
        return request.user.is_authenticated and request.user.is_superuser
