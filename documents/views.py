import logging

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods

from accounts.permissions import can_review_documents
from .models import Document, DocumentAccessLog, DocumentType
from .storage import (
    DocumentStorageError,
    StorageConfigurationError,
    delete_document_file,
    open_document_file,
    save_document_file,
)
from .validators import validate_upload

logger = logging.getLogger(__name__)
PORTFOLIO_CATEGORY_ORDER = (
    "Aadhaar card",
    "Community certificate",
    "Income certificate",
    "Nativity certificate",
    "Birth certificate",
    "PAN card",
    "Bank passbook",
    "10th certificate",
    "12th certificate",
    "Graduation certificate",
    "Other",
    "General document",
)
REQUIRED_PORTFOLIO_CATEGORIES = PORTFOLIO_CATEGORY_ORDER[:10]


def _ordered_document_types():
    document_types = list(DocumentType.objects.all())
    order = {name: position for position, name in enumerate(PORTFOLIO_CATEGORY_ORDER)}
    document_types.sort(key=lambda doc_type: (order.get(doc_type.name, len(order)), doc_type.name.lower()))
    return document_types


def _upload_context(request):
    return {
        "document_types": _ordered_document_types(),
        "documents": Document.objects.filter(owner=request.user).select_related("doc_type"),
        "max_upload_bytes": settings.MAX_UPLOAD_BYTES,
        "upload_translations": {
            "invalidType": _("Unsupported file type. Choose PDF, DOC, DOCX, TXT, JPG, JPEG, or PNG."),
            "tooLarge": _("File too large. Maximum size is %(size)s."),
            "uploading": _("Uploading document…"),
            "uploadComplete": _("Upload complete."),
            "uploadFailed": _("Upload failed. Please try again."),
            "networkError": _("Network error. Check your connection and retry."),
            "deleteConfirm": _("Delete this document? This cannot be undone."),
            "deleteFailed": _("Delete failed. Please try again."),
            "deleteNetworkError": _("Network error while deleting. Retry."),
            "deleted": _("Document deleted."),
            "emptyList": _("No documents uploaded yet."),
        },
    }


def _upload_error(request, message, status=400):
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"error": message}, status=status)
    messages.error(request, message)
    return render(request, "documents/upload.html", _upload_context(request), status=status)


@login_required
@require_http_methods(["GET", "POST"])
def upload_document(request):
    if request.method == "POST":
        try:
            uploaded_file = request.FILES.get("file")
            if uploaded_file is None:
                return _upload_error(request, _("Choose a file to upload."))

            replace_id = request.POST.get("replace_id")
            replaces = None
            if replace_id:
                replaces = Document.objects.get(
                    pk=replace_id,
                    owner=request.user,
                    status__in=[Document.Status.REJECTED, Document.Status.REUPLOAD],
                )
                doc_type = replaces.doc_type
            else:
                doc_type_id = request.POST.get("doc_type")
                if doc_type_id:
                    doc_type = DocumentType.objects.get(pk=doc_type_id)
                else:
                    doc_type = DocumentType.objects.get_or_create(name="General document")[0]

            file_type = validate_upload(uploaded_file)
            document = Document(
                owner=request.user,
                doc_type=doc_type,
                original_filename=uploaded_file.name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1][:255],
                file_type=file_type,
                file_size=uploaded_file.size,
                replaces=replaces,
            )
            file_saved = False
            try:
                save_document_file(document, uploaded_file)
                file_saved = True
                with transaction.atomic():
                    document.save()
                    document.file_url = reverse("doc-download", args=[document.pk])
                    document.save(update_fields=["file_url"])
            except Exception:
                if file_saved:
                    try:
                        delete_document_file(document)
                    except Exception:
                        logger.exception("Failed to clean up an incomplete document upload")
                raise

            action = "REPLACE" if replaces else "UPLOAD"
            DocumentAccessLog.objects.create(document=document, actor=request.user, action=action)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "id": document.pk,
                    "name": document.original_filename,
                    "doc_type": document.doc_type.display_name,
                    "file_type": document.file_type,
                    "file_size": document.file_size,
                    "status": document.get_status_display(),
                    "verification_source": document.get_verification_source_display(),
                    "uploaded_at": document.uploaded_at.isoformat(),
                    "file_url": document.file_url,
                }, status=201)
            messages.success(request, _("Document uploaded successfully."))
            return redirect("document-upload")
        except (Document.DoesNotExist, DocumentType.DoesNotExist, ValueError, TypeError):
            return _upload_error(request, _("Choose a valid document type."))
        except ValidationError as error:
            return _upload_error(request, "; ".join(error.messages))
        except StorageConfigurationError as error:
            logger.error("Document storage is not configured: %s", error)
            return _upload_error(request, _("Secure document storage is not configured. Contact support."), status=503)
        except (DocumentStorageError, DatabaseError, OSError):
            logger.exception("Document upload failed")
            return _upload_error(request, _("Upload failed. Check your connection and try again."), status=502)
        except Exception:
            logger.exception("Unexpected document upload failure")
            return _upload_error(request, _("Upload failed unexpectedly. Please try again."), status=500)

    return render(request, "documents/upload.html", _upload_context(request))


@login_required
@require_GET
def document_portfolio(request):
    from profiles.models import UserProfile

    profile = UserProfile.objects.filter(user=request.user).first()
    documents = Document.objects.filter(owner=request.user).select_related("doc_type")
    categories = [{"type": doc_type, "documents": documents.filter(doc_type=doc_type)} for doc_type in _ordered_document_types()]
    verified_count = documents.filter(
        status=Document.Status.VERIFIED,
        doc_type__name__in=REQUIRED_PORTFOLIO_CATEGORIES,
    ).values("doc_type_id").distinct().count()
    return render(request, "documents/portfolio.html", {
        "profile": profile,
        "categories": categories,
        "document_count": documents.count(),
        "completion_percentage": round(verified_count / len(REQUIRED_PORTFOLIO_CATEGORIES) * 100),
    })


@login_required
@require_http_methods(["POST"])
def delete_document(request, pk):
    document = Document.objects.filter(owner=request.user, pk=pk).first()
    if document is None:
        raise Http404

    DocumentAccessLog.objects.create(document=document, actor=request.user, action="DELETE")
    try:
        document.delete()
    except (DocumentStorageError, StorageConfigurationError, OSError):
        logger.exception("Document delete failed")
        return _upload_error(request, _("Could not delete the document. Please try again."), status=502)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"deleted": True})
    messages.success(request, _("Document deleted."))
    return redirect("document-upload")
@login_required
@require_GET
def download_document(request, pk):
    doc = Document.objects.filter(pk=pk).first()
    allowed = doc and (doc.owner_id == request.user.id or can_review_documents(request.user))
    if not allowed:
        raise Http404  # 404, not 403: don't reveal that the ID exists
    try:
        document_file = open_document_file(doc)
    except (DocumentStorageError, StorageConfigurationError, OSError):
        logger.exception("Document download failed")
        raise Http404
    DocumentAccessLog.objects.create(document=doc, actor=request.user, action="DOWNLOAD")
    can_view_inline = doc.file_type in {"application/pdf", "image/jpeg", "image/png", "text/plain"}
    resp = FileResponse(
        document_file,
        as_attachment=not (request.GET.get("view") == "1" and can_view_inline),
        filename=doc.original_filename,
        content_type=doc.file_type or "application/octet-stream",
    )
    resp["Cache-Control"] = "private, no-store"
    resp["X-Content-Type-Options"] = "nosniff"
    return resp
