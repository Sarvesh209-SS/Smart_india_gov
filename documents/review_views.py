from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .models import Document, DocumentAccessLog


REVIEWER_ROLES = {"REVIEWER", "ADMIN", "SUPER_ADMIN"}


def _require_reviewer(user):
    if not user.is_authenticated or not user.is_staff or user.role not in REVIEWER_ROLES:
        raise PermissionDenied


@login_required
@require_GET
def review_queue(request):
    _require_reviewer(request.user)
    documents = Document.objects.filter(
        status__in=[Document.Status.PENDING, Document.Status.REUPLOAD],
    ).select_related("owner", "doc_type").order_by("uploaded_at")
    return render(request, "documents/review_queue.html", {"documents": documents})


@login_required
@require_POST
def review_document(request, pk):
    _require_reviewer(request.user)
    document = get_object_or_404(
        Document,
        pk=pk,
        status__in=[Document.Status.PENDING, Document.Status.REUPLOAD],
    )
    action = request.POST.get("action")
    if action == "verify":
        document.status = Document.Status.VERIFIED
        document.verification_source = Document.VerificationSource.ADMIN_REVIEW
        document.rejection_reason = ""
        event = "VERIFY"
    elif action == "reject":
        reason = (request.POST.get("rejection_reason") or "").strip()
        if not reason:
            raise PermissionDenied("A rejection reason is required.")
        document.status = Document.Status.REJECTED
        document.rejection_reason = reason[:5000]
        event = "REJECT"
    else:
        raise Http404

    document.save(update_fields=["status", "verification_source", "rejection_reason"])
    DocumentAccessLog.objects.create(document=document, actor=request.user, action=event)
    return redirect("document-review-queue")
