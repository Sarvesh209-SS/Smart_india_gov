from datetime import date

from django.contrib import admin
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from eligibility.models import ScholarshipEligibilityRule
from documents.models import Document, DocumentType
from eligibility.engine import ELIGIBLE, INCOMPLETE, NOT_ELIGIBLE, evaluate
from profiles.models import UserProfile
from .models import Scholarship, ScholarshipApplication


class ScholarshipApplicationFlowTests(TestCase):
    def setUp(self):
        from accounts.models import User

        self.user = User.objects.create_user(
            email="applicant@example.com",
            password="test-password-123",
            mobile="+919876543210",
        )
        self.profile = UserProfile.objects.create(user=self.user, full_name="Applicant", date_of_birth=date(2000, 1, 1))
        self.scholarship = Scholarship.objects.create(
            name="Learning Grant",
            provider="Education Foundation",
            official_url="https://example.org/grant",
            is_published=True,
        )
        self.rule = ScholarshipEligibilityRule.objects.create(scholarship=self.scholarship)
        self.client.force_login(self.user)

    def test_eligible_user_can_submit_once(self):
        response = self.client.post(reverse("scholarship-detail", args=[self.scholarship.pk]), {
            "applicant_note": "Please consider my application.",
        })

        self.assertRedirects(response, reverse("dashboard"))
        application = ScholarshipApplication.objects.get(user=self.user, scholarship=self.scholarship)
        self.assertEqual(application.status, ScholarshipApplication.Status.SUBMITTED)
        self.assertEqual(application.applicant_note, "Please consider my application.")

        self.client.post(reverse("scholarship-detail", args=[self.scholarship.pk]))
        self.assertEqual(ScholarshipApplication.objects.filter(user=self.user).count(), 1)

    def test_scholarship_page_displays_eligibility_result(self):
        self.user.preferred_language = "ta"
        self.user.save(update_fields=["preferred_language"])
        response = self.client.get(reverse("scholarship-detail", args=[self.scholarship.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "விண்ணப்பிக்கத் தகுதி உள்ளது")

    def test_failed_eligibility_blocks_submission(self):
        self.rule.min_age = 99
        self.rule.save()

        response = self.client.post(reverse("scholarship-detail", args=[self.scholarship.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScholarshipApplication.objects.filter(user=self.user).exists())

    def test_unconfigured_rules_cannot_be_applied_to(self):
        self.rule.delete()

        response = self.client.post(reverse("scholarship-detail", args=[self.scholarship.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScholarshipApplication.objects.filter(user=self.user).exists())

    def test_application_review_is_registered_in_admin(self):
        self.assertTrue(admin.site.is_registered(ScholarshipApplication))

        from accounts.models import User

        reviewer = User.objects.create_superuser(
            email="reviewer@example.com",
            password="review-password-123",
            mobile="+919876543211",
        )
        application = ScholarshipApplication.objects.create(user=self.user, scholarship=self.scholarship)
        self.client.force_login(reviewer)
        response = self.client.get(reverse("admin:scholarships_scholarshipapplication_change", args=[application.pk]))

        self.assertEqual(response.status_code, 200)

    def test_dashboard_creates_a_profile_for_a_new_user(self):
        self.profile.delete()

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

    def test_required_document_must_be_verified(self):
        document_type = DocumentType.objects.create(name="Income proof")
        self.rule.required_documents.add(document_type)
        document = Document.objects.create(
            owner=self.user,
            doc_type=document_type,
            status=Document.Status.PENDING,
        )

        pending_result = evaluate(self.profile, self.scholarship)
        self.assertEqual(pending_result.status, INCOMPLETE)
        self.assertTrue(any("Income proof" in item for item in pending_result.missing))

        document.status = Document.Status.VERIFIED
        document.save(update_fields=["status"])
        verified_result = evaluate(self.profile, self.scholarship)
        self.assertEqual(verified_result.status, ELIGIBLE)

    def test_missing_required_profile_data_is_incomplete(self):
        self.profile.date_of_birth = None
        self.profile.save(update_fields=["date_of_birth"])
        self.rule.min_age = 18
        self.rule.save(update_fields=["min_age"])

        result = evaluate(self.profile, self.scholarship)

        self.assertEqual(result.status, INCOMPLETE)
        self.assertIn("Date of birth", result.missing)

    def test_age_and_income_failures_make_applicant_ineligible(self):
        self.rule.min_age = 30
        self.rule.max_income = 50000
        self.rule.save(update_fields=["min_age", "max_income"])
        self.profile.annual_family_income = 60000
        self.profile.save(update_fields=["annual_family_income"])

        result = evaluate(self.profile, self.scholarship)

        self.assertEqual(result.status, NOT_ELIGIBLE)
        self.assertTrue(result.failed)

    def test_zero_age_limits_are_enforced(self):
        today = timezone.localdate()
        self.profile.date_of_birth = date(today.year - 1, today.month, today.day)
        self.profile.save(update_fields=["date_of_birth"])
        self.rule.min_age = 0
        self.rule.max_age = 0
        self.rule.save(update_fields=["min_age", "max_age"])

        result = evaluate(self.profile, self.scholarship)

        self.assertEqual(result.status, NOT_ELIGIBLE)
        self.assertTrue(any("maximum age of 0" in item for item in result.failed))

    def test_profile_criteria_match_case_and_surrounding_spaces(self):
        self.profile.education_level = "  GRADUATE  "
        self.profile.category = " obc "
        self.profile.state = " karnataka "
        self.profile.save(update_fields=["education_level", "category", "state"])
        self.rule.education_levels = "Undergraduate, Graduate"
        self.rule.categories = "OBC, SC"
        self.rule.states = "Karnataka, Tamil Nadu"
        self.rule.save(update_fields=["education_levels", "categories", "states"])

        result = evaluate(self.profile, self.scholarship)

        self.assertEqual(result.status, ELIGIBLE)
        self.assertIn("Education level", result.met)
        self.assertIn("Category", result.met)
        self.assertIn("State", result.met)
