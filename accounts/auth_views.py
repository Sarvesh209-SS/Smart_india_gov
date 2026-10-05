from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods


def set_language(request):
    if request.method != "POST":
        return redirect("home")
    language = request.POST.get("language")
    available = {choice[0] for choice in settings.LANGUAGES}
    if language not in available:
        language = settings.LANGUAGE_CODE
    if request.user.is_authenticated and request.user.preferred_language != language:
        request.user.preferred_language = language
        request.user.save(update_fields=["preferred_language"])

    translation.activate(language)
    next_url = request.POST.get("next", "")
    response = redirect(
        next_url if url_has_allowed_host_and_scheme(next_url, {request.get_host()}) else reverse("home")
    )
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        language,
        max_age=settings.LANGUAGE_COOKIE_AGE,
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=True,
        samesite="Lax",
    )
    return response


@login_required
def security_dashboard(request):
    active_sessions = sum(
        session.get_decoded().get("_auth_user_id") == str(request.user.pk)
        for session in Session.objects.filter(expire_date__gt=timezone.now())
    )
    return render(request, "accounts/security.html", {
        "active_sessions": active_sessions,
        "email_verified": request.user.email_verified,
        "masked_mobile": request.user.masked_mobile,
    })


@require_http_methods(["POST"])
def logout_all_devices(request):
    if not request.user.is_authenticated:
        return redirect("login")
    request.user.auth_version += 1
    request.user.save(update_fields=["auth_version"])
    logout(request)
    messages.success(request, _("You have been signed out from all devices."))
    return redirect("login")
