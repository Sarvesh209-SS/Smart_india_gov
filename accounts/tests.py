from django.contrib.auth import authenticate
from django.test import TestCase
from django.urls import reverse

from .models import User


class EmailPasswordRegistrationTests(TestCase):
    def test_registration_creates_and_logs_in_account_without_otp(self):
        response = self.client.post(reverse("register"), {
            "email": "student@example.com",
            "password": "Valid-passphrase-42!",
        })

        user = User.objects.get(email="student@example.com")
        self.assertRedirects(response, reverse("dashboard"))
        self.assertIsNone(user.mobile)
        self.assertEqual(user.role, "USER")
        self.assertEqual(self.client.session.get("_auth_user_id"), str(user.pk))

    def test_registration_accepts_optional_indian_mobile(self):
        response = self.client.post(reverse("register"), {
            "email": "student@example.com",
            "mobile": "98765 43210",
            "password": "Valid-passphrase-42!",
        })

        user = User.objects.get(email="student@example.com")
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(user.mobile, "+919876543210")

    def test_invalid_optional_mobile_is_rejected(self):
        response = self.client.post(reverse("register"), {
            "email": "student@example.com",
            "mobile": "1234567890",
            "password": "Valid-passphrase-42!",
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="student@example.com").exists())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_duplicate_email_and_mobile_are_rejected(self):
        User.objects.create_user(
            email="existing@example.com",
            password="Valid-passphrase-42!",
            mobile="+919876543210",
        )
        email_response = self.client.post(reverse("register"), {
            "email": "existing@example.com",
            "password": "Valid-passphrase-42!",
        })
        mobile_response = self.client.post(reverse("register"), {
            "email": "new@example.com",
            "mobile": "9876543210",
            "password": "Valid-passphrase-42!",
        })

        self.assertEqual(email_response.status_code, 409)
        self.assertEqual(mobile_response.status_code, 409)
        self.assertEqual(User.objects.count(), 1)

    def test_email_password_login_works_without_mobile_verification(self):
        user = User.objects.create_user(
            email="student@example.com",
            password="Valid-passphrase-42!",
        )

        response = self.client.post(reverse("login"), {
            "username": user.email,
            "password": "Valid-passphrase-42!",
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("home"))
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
        self.assertEqual(self.client.session.get("_auth_user_id"), str(user.pk))
        self.assertIsNotNone(authenticate(username=user.email, password="Valid-passphrase-42!"))

    def test_logout_all_invalidates_other_sessions(self):
        user = User.objects.create_user(
            email="student@example.com",
            password="Valid-passphrase-42!",
        )
        self.client.force_login(user)
        other_client = self.client_class()
        other_client.force_login(user)

        response = self.client.post(reverse("logout-all"))
        other_response = other_client.get(reverse("dashboard"))

        user.refresh_from_db()
        self.assertRedirects(response, reverse("login"))
        self.assertEqual(user.auth_version, 2)
        self.assertRedirects(other_response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_mobile_otp_routes_are_removed(self):
        for path in ("/accounts/mobile-login/", "/accounts/verify/00000000-0000-4000-8000-000000000000/"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_registration_page_contains_no_otp_step_or_action(self):
        response = self.client.get(reverse("register"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create account")
        self.assertNotContains(response, "Send OTP")
        self.assertNotContains(response, "OTP verification")
