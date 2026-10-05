from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
class Scholarship(models.Model):
    name = models.CharField(max_length=200)
    provider = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    official_url = models.URLField()  # admin must enter a verified official link
    opens_on = models.DateField(null=True, blank=True)
    closes_on = models.DateField(null=True, blank=True, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    is_demo = models.BooleanField(default=False)  # label DEMO DATA in the UI
    def __str__(self): return self.name


class ScholarshipApplication(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", _("Submitted")
        UNDER_REVIEW = "UNDER_REVIEW", _("Under review")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scholarship_applications")
    scholarship = models.ForeignKey(Scholarship, on_delete=models.PROTECT, related_name="applications")
    documents = models.ManyToManyField("documents.Document", blank=True, related_name="scholarship_applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    applicant_note = models.TextField(blank=True)
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_scholarship_applications")
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "scholarship"], name="unique_user_scholarship_application")]
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.user.email} - {self.scholarship.name}"
