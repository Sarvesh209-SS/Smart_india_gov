from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import AuditEvent


@receiver(user_logged_in)
def record_login(sender, request, user, **kwargs):
    del sender, kwargs
    request.session["auth_version"] = user.auth_version
    request.session["django_language"] = user.preferred_language
    AuditEvent.objects.create(user=user, event="LOGIN")


@receiver(user_logged_out)
def record_logout(sender, request, user, **kwargs):
    del sender, request, kwargs
    if user is not None and user.is_authenticated:
        AuditEvent.objects.create(user=user, event="LOGOUT")
