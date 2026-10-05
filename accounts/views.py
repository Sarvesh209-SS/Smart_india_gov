import re

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from accounts.models import AuditEvent, User
from profiles.models import UserProfile
from scholarships.models import Scholarship, ScholarshipApplication


@login_required
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": request.user.get_full_name()},
    )
    today = timezone.localdate()
    scholarships = Scholarship.objects.filter(is_published=True).filter(
        Q(opens_on__isnull=True) | Q(opens_on__lte=today),
    ).filter(Q(closes_on__isnull=True) | Q(closes_on__gte=today))
    applications = ScholarshipApplication.objects.filter(
        user=request.user,
    ).select_related("scholarship")
    return render(request, "dashboard.html", {
        "profile": profile,
        "scholarships": scholarships,
        "applications": applications,
    })


def _normalize_optional_indian_mobile(value):
    digits = re.sub(r"[\s()-]", "", value or "")
    if not digits:
        return None
    if digits.startswith("+91"):
        local_number = digits[3:]
    elif digits.startswith("91") and len(digits) == 12:
        local_number = digits[2:]
    else:
        local_number = digits
    if not re.fullmatch(r"[6-9]\d{9}", local_number):
        raise ValueError(_("Enter a valid 10-digit Indian mobile number."))
    return f"+91{local_number}"


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""
        try:
            mobile = _normalize_optional_indian_mobile(request.POST.get("mobile", ""))
        except ValueError as error:
            messages.error(request, str(error))
            return render(request, "accounts/register.html", status=400)

        if not email or not password:
            messages.error(request, _("Email and password are required."))
            return render(request, "accounts/register.html", status=400)
        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, _("An account with this email already exists. Please log in."))
            return render(request, "accounts/register.html", status=409)
        if mobile and User.objects.filter(mobile=mobile).exists():
            messages.error(request, _("This mobile number is already registered."))
            return render(request, "accounts/register.html", status=409)

        candidate = User(email=User.objects.normalize_email(email), mobile=mobile)
        try:
            candidate.full_clean(exclude=["password", "last_login", "date_joined", "groups", "user_permissions"])
            validate_password(password, user=candidate)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            return render(request, "accounts/register.html", status=400)

        user = User.objects.create_user(
            email=candidate.email,
            password=password,
            mobile=mobile,
            role="USER",
            preferred_language=request.LANGUAGE_CODE,
        )
        AuditEvent.objects.create(user=user, event="REGISTER")
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session["auth_version"] = user.auth_version
        request.session["django_language"] = user.preferred_language
        messages.success(request, _("Account created successfully."))
        return redirect("dashboard")

    return render(request, "accounts/register.html")
