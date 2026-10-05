from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from documents.models import Document
from eligibility.engine import ELIGIBLE, evaluate
from eligibility.models import ScholarshipEligibilityRule
from profiles.models import UserProfile
from .models import Scholarship, ScholarshipApplication


@login_required
@require_http_methods(["GET", "POST"])
def scholarship_detail(request, pk):
    scholarship = get_object_or_404(Scholarship, pk=pk, is_published=True)
    profile = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": request.user.get_full_name()},
    )[0]
    try:
        result = evaluate(profile, scholarship)
    except ScholarshipEligibilityRule.DoesNotExist:
        result = None

    application = ScholarshipApplication.objects.filter(
        user=request.user, scholarship=scholarship,
    ).first()

    if request.method == "POST":
        if result is None:
            messages.error(request, _("This scholarship does not have eligibility criteria yet."))
        elif result.status != ELIGIBLE:
            messages.error(request, _("Complete the eligibility requirements before applying."))
        elif scholarship.opens_on and scholarship.opens_on > timezone.localdate():
            messages.error(request, _("Applications for this scholarship are not open yet."))
        elif scholarship.closes_on and scholarship.closes_on < timezone.localdate():
            messages.error(request, _("The application deadline has passed."))
        elif application:
            messages.info(request, _("You have already applied for this scholarship."))
        else:
            application = ScholarshipApplication.objects.create(
                user=request.user,
                scholarship=scholarship,
                applicant_note=request.POST.get("applicant_note", "").strip(),
            )
            application.documents.set(Document.objects.filter(owner=request.user))
            messages.success(request, _("Your scholarship application has been submitted."))
            return redirect("dashboard")

    return render(request, "scholarships/detail.html", {
        "scholarship": scholarship,
        "eligibility": result,
        "application": application,
    })
