from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


ROLE_CHOICES = [
    ("USER", _("Student")),
    ("REVIEWER", _("Document reviewer")),
    ("ADMIN", _("Admin")),
    ("SUPER_ADMIN", _("Super Admin")),
]


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **kw):
        user = self.model(email=self.normalize_email(email), **kw)
        user.set_password(password); user.save(); return user
    def create_superuser(self, email, password=None, **kw):
        kw.update(is_staff=True, is_superuser=True, role="SUPER_ADMIN")
        return self.create_user(email, password, **kw)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=16, default="USER", choices=ROLE_CHOICES)
    preferred_language = models.CharField(
        max_length=5,
        default="en",
        choices=[("en", _("English")), ("ta", _("Tamil")), ("hi", _("Hindi"))],
    )
    auth_version = models.PositiveIntegerField(default=1)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    @property
    def masked_mobile(self):
        if not self.mobile:
            return ""
        return f"+91 ******{self.mobile[-4:]}"


class AuditEvent(models.Model):
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subject_audit_events",
    )
    event = models.CharField(max_length=40, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
