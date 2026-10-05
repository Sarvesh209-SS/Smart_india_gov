from django.db import models
from documents.models import DocumentType
from scholarships.models import Scholarship
class ScholarshipEligibilityRule(models.Model):
    """All fields optional: blank/null = no restriction. Editable in Django admin."""
    scholarship = models.OneToOneField(Scholarship, on_delete=models.CASCADE, related_name="rule")
    min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_income = models.PositiveIntegerField(null=True, blank=True)
    education_levels = models.CharField(max_length=200, blank=True, help_text="Comma-separated")
    categories = models.CharField(max_length=200, blank=True, help_text="Comma-separated")
    states = models.CharField(max_length=300, blank=True, help_text="Comma-separated")
    requires_first_gen = models.BooleanField(default=False)
    required_documents = models.ManyToManyField(DocumentType, blank=True)
