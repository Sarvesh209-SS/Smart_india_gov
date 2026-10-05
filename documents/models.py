import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.translation import gettext, gettext_lazy as _


private_storage = FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT, base_url=None)


def random_path(instance, filename):
    return f"{instance.owner_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class DocumentType(models.Model):
    name = models.CharField(max_length=80, unique=True)
    validity_months = models.PositiveIntegerField(null=True, blank=True)

    @property
    def display_name(self):
        return gettext(self.name)

    def __str__(self): return self.name


class Document(models.Model):
    class StorageBackend(models.TextChoices):
        LOCAL = "LOCAL", "Private local storage"
        FIREBASE = "FIREBASE", "Firebase Storage"

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending Verification")
        VERIFIED = "VERIFIED", _("Verified")
        REJECTED = "REJECTED", _("Rejected")
        EXPIRED = "EXPIRED", _("Expired")
        REUPLOAD = "REUPLOAD", _("Requires Re-upload")

    class VerificationSource(models.TextChoices):
        USER_UPLOAD = "USER_UPLOAD", _("Uploaded by user")
        ADMIN_REVIEW = "ADMIN_REVIEW", _("Verified by admin")
        OFFICIAL_API = "OFFICIAL_API", _("Verified through authorized API")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    file = models.FileField(storage=private_storage, upload_to=random_path, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=100, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    storage_backend = models.CharField(max_length=10, choices=StorageBackend.choices, default=StorageBackend.LOCAL)
    storage_key = models.CharField(max_length=500, blank=True)
    file_url = models.CharField(max_length=500, blank=True)
    replaces = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replacement_documents",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    verification_source = models.CharField(
        max_length=20,
        choices=VerificationSource.choices,
        default=VerificationSource.USER_UPLOAD,
    )
    rejection_reason = models.TextField(blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    def delete(self, *a, **kw):
        from .storage import delete_document_file

        delete_document_file(self)
        super().delete(*a, **kw)
class DocumentAccessLog(models.Model):
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True)
    document_reference = models.CharField(max_length=32, blank=True, db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20)
    at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.document_id and not self.document_reference:
            self.document_reference = str(self.document_id)
        super().save(*args, **kwargs)
