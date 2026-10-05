from django.conf import settings
from django.db import models
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=120)
    date_of_birth = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=60, blank=True, db_index=True)
    district = models.CharField(max_length=60, blank=True, db_index=True)
    education_level = models.CharField(max_length=40, blank=True, db_index=True)
    course = models.CharField(max_length=100, blank=True)
    institution = models.CharField(max_length=150, blank=True)
    category = models.CharField(max_length=20, blank=True)  # voluntary
    annual_family_income = models.PositiveIntegerField(null=True, blank=True)
    first_generation_graduate = models.BooleanField(null=True)
    def __str__(self): return self.full_name
