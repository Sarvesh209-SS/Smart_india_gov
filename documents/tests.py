from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from .models import Document, DocumentAccessLog, DocumentType
from .validators import validate_upload


class DocumentUploadFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="docs@example.com",
            password="test-password-123",
            mobile="+919876543210",
        )
        self.document_type = DocumentType.objects.create(name="Identity proof")
        self.client.force_login(self.user)

    def tearDown(self):
        for document in Document.objects.filter(owner=self.user):
            document.delete()

    def test_valid_pdf_is_uploaded_as_pending_private_document(self):
        upload = SimpleUploadedFile("identity.pdf", b"%PDF-1.7\nexample", content_type="application/pdf")

        response = self.client.post(reverse("document-upload"), {
            "doc_type": self.document_type.pk,
            "file": upload,
        })

        self.assertRedirects(response, reverse("document-upload"))
        document = Document.objects.get(owner=self.user)
        self.assertEqual(document.status, Document.Status.PENDING)
        self.assertEqual(document.verification_source, Document.VerificationSource.USER_UPLOAD)
        self.assertEqual(document.doc_type, self.document_type)
        self.assertTrue(document.file.storage.exists(document.file.name))

    def test_extension_without_matching_file_signature_is_rejected(self):
        upload = SimpleUploadedFile("identity.pdf", b"not a real PDF", content_type="application/pdf")

        response = self.client.post(reverse("document-upload"), {
            "doc_type": self.document_type.pk,
            "file": upload,
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Document.objects.filter(owner=self.user).exists())

    def test_document_download_is_not_shared_between_users(self):
        other_user = User.objects.create_user(
            email="other@example.com",
            password="test-password-123",
            mobile="+919876543211",
        )
        document = Document.objects.create(
            owner=self.user,
            doc_type=self.document_type,
            file=SimpleUploadedFile("identity.pdf", b"%PDF-1.7\nprivate sample"),
            original_filename="identity.pdf",
            file_type="application/pdf",
            file_size=24,
        )
        self.client.force_login(other_user)

        response = self.client.get(reverse("doc-download", args=[document.pk]))

        self.assertEqual(response.status_code, 404)

    def test_complete_upload_display_download_delete_flow(self):
        upload = SimpleUploadedFile("identity.pdf", b"%PDF-1.7\nprivate sample", content_type="application/pdf")
        response = self.client.post(reverse("document-upload"), {
            "doc_type": self.document_type.pk,
            "file": upload,
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 201)
        metadata = response.json()
        document = Document.objects.get(pk=metadata["id"], owner=self.user)
        self.assertEqual(metadata["name"], "identity.pdf")
        self.assertEqual(document.file_type, "application/pdf")
        self.assertEqual(document.file_size, len(b"%PDF-1.7\nprivate sample"))
        self.assertEqual(document.file_url, reverse("doc-download", args=[document.pk]))

        listing = self.client.get(reverse("document-upload"))
        self.assertContains(listing, "identity.pdf")
        self.assertContains(listing, "application/pdf")

        download = self.client.get(document.file_url)
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b"".join(download.streaming_content), b"%PDF-1.7\nprivate sample")

        deleted = self.client.post(
            reverse("document-delete", args=[document.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(Document.objects.filter(pk=document.pk).exists())
        delete_log = DocumentAccessLog.objects.get(actor=self.user, action="DELETE")
        self.assertEqual(delete_log.document_reference, str(metadata["id"]))
        self.assertIsNone(delete_log.document_id)

    def test_supported_extensions_require_matching_signatures(self):
        docx_bytes = BytesIO()
        with ZipFile(docx_bytes, "w", ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
        samples = (
            ("sample.pdf", b"%PDF-1.7 content", "application/pdf"),
            ("sample.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1data", "application/msword"),
            ("sample.docx", docx_bytes.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("sample.txt", b"Text document", "text/plain"),
            ("sample.jpg", b"\xff\xd8\xff\xe0image", "image/jpeg"),
            ("sample.jpeg", b"\xff\xd8\xff\xe0image", "image/jpeg"),
            ("sample.png", b"\x89PNG\r\n\x1a\ndata", "image/png"),
        )
        for filename, content, expected_type in samples:
            with self.subTest(filename=filename):
                upload = SimpleUploadedFile(filename, content)
                self.assertEqual(validate_upload(upload), expected_type)

    def test_upload_size_limit_is_enforced(self):
        upload = SimpleUploadedFile("too-large.pdf", b"%PDF-" + b"x" * settings.MAX_UPLOAD_BYTES)

        response = self.client.post(reverse("document-upload"), {
            "doc_type": self.document_type.pk,
            "file": upload,
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(response.status_code, 400)
        self.assertIn("maximum size", response.json()["error"])

    @override_settings(FIREBASE_STORAGE_BUCKET="example.appspot.com", FIREBASE_SERVICE_ACCOUNT_KEY="")
    def test_partial_firebase_configuration_returns_actionable_error(self):
        upload = SimpleUploadedFile("identity.pdf", b"%PDF-1.7\nprivate sample")

        response = self.client.post(reverse("document-upload"), {
            "doc_type": self.document_type.pk,
            "file": upload,
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(response.status_code, 503)
        self.assertIn("Contact support", response.json()["error"])
        self.assertNotIn("FIREBASE_SERVICE_ACCOUNT_KEY", response.json()["error"])
        self.assertFalse(Document.objects.filter(owner=self.user).exists())

    def test_another_user_cannot_delete_document(self):
        other_user = User.objects.create_user(
            email="other@example.com",
            password="test-password-123",
            mobile="+919876543211",
        )
        document = Document.objects.create(
            owner=other_user,
            doc_type=self.document_type,
            file=SimpleUploadedFile("other.pdf", b"%PDF-1.7\nprivate sample"),
            original_filename="other.pdf",
            file_type="application/pdf",
            file_size=25,
        )

        response = self.client.post(reverse("document-delete", args=[document.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Document.objects.filter(pk=document.pk, owner=other_user).exists())
        document.delete()

    def test_regular_user_cannot_access_document_review_queue(self):
        response = self.client.get(reverse("document-review-queue"))

        self.assertEqual(response.status_code, 403)

    def test_authorized_reviewer_can_verify_pending_document(self):
        reviewer = User.objects.create_user(
            email="reviewer@example.com",
            password="test-password-123",
            mobile="+919876543212",
            is_staff=True,
            role="REVIEWER",
        )
        document = Document.objects.create(
            owner=self.user,
            doc_type=self.document_type,
            original_filename="identity.pdf",
            file_type="application/pdf",
            file_size=10,
        )
        self.client.force_login(reviewer)

        dashboard = self.client.get(reverse("dashboard"))
        queue = self.client.get(reverse("document-review-queue"))
        response = self.client.post(reverse("document-review-decision", args=[document.pk]), {"action": "verify"})

        document.refresh_from_db()
        self.assertEqual(queue.status_code, 200)
        self.assertContains(dashboard, "Verification queue")
        self.assertContains(queue, "Identity proof")
        self.assertRedirects(response, reverse("document-review-queue"))
        self.assertEqual(document.status, Document.Status.VERIFIED)
        self.assertEqual(document.verification_source, Document.VerificationSource.ADMIN_REVIEW)
        self.assertTrue(DocumentAccessLog.objects.filter(document=document, actor=reviewer, action="VERIFY").exists())

    def test_reviewer_rejection_requires_and_saves_a_reason(self):
        reviewer = User.objects.create_user(
            email="reviewer@example.com",
            password="test-password-123",
            mobile="+919876543212",
            is_staff=True,
            role="REVIEWER",
        )
        document = Document.objects.create(
            owner=self.user,
            doc_type=self.document_type,
            original_filename="identity.pdf",
            file_type="application/pdf",
            file_size=10,
        )
        self.client.force_login(reviewer)

        response = self.client.post(reverse("document-review-decision", args=[document.pk]), {
            "action": "reject",
            "rejection_reason": "The image is not readable.",
        })

        document.refresh_from_db()
        self.assertRedirects(response, reverse("document-review-queue"))
        self.assertEqual(document.status, Document.Status.REJECTED)
        self.assertEqual(document.rejection_reason, "The image is not readable.")
        self.assertTrue(DocumentAccessLog.objects.filter(document=document, actor=reviewer, action="REJECT").exists())

    def test_rejected_document_can_be_replaced_without_losing_review_record(self):
        previous = Document.objects.create(
            owner=self.user,
            doc_type=self.document_type,
            file=SimpleUploadedFile("old.pdf", b"%PDF-1.7\nold"),
            original_filename="old.pdf",
            file_type="application/pdf",
            file_size=12,
            status=Document.Status.REJECTED,
            rejection_reason="The image is not readable.",
        )
        replacement = SimpleUploadedFile("new.pdf", b"%PDF-1.7\nnew clear copy")

        response = self.client.post(reverse("document-upload"), {
            "replace_id": previous.pk,
            "file": replacement,
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        previous.refresh_from_db()
        new_document = Document.objects.get(replaces=previous)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(previous.status, Document.Status.REJECTED)
        self.assertEqual(previous.rejection_reason, "The image is not readable.")
        self.assertEqual(new_document.status, Document.Status.PENDING)
        self.assertEqual(new_document.doc_type, previous.doc_type)

    def test_portfolio_renders_requested_certificate_sections_for_new_user(self):
        response = self.client.get(reverse("document-portfolio"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aadhaar card")
        self.assertContains(response, "Community certificate")
        self.assertContains(response, "Nativity certificate")
        self.assertContains(response, "Graduation certificate")
        page = response.content.decode()
        self.assertLess(page.index("Aadhaar card"), page.index("Community certificate"))
        self.assertLess(page.index("Community certificate"), page.index("Income certificate"))

    def test_all_student_certificate_categories_accept_uploads(self):
        names = (
            "Aadhaar card", "PAN card", "Community certificate", "Income certificate",
            "Nativity certificate", "Birth certificate", "Bank passbook", "10th certificate",
            "12th certificate", "Graduation certificate",
        )
        for index, name in enumerate(names):
            with self.subTest(document_type=name):
                document_type = DocumentType.objects.get(name=name)
                upload = SimpleUploadedFile(f"student-{index}.pdf", b"%PDF-1.7\ncertificate")
                response = self.client.post(reverse("document-upload"), {
                    "doc_type": document_type.pk,
                    "file": upload,
                }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
                self.assertEqual(response.status_code, 201)
                self.assertTrue(Document.objects.filter(owner=self.user, doc_type=document_type).exists())

            Document.objects.filter(owner=self.user).update(status=Document.Status.VERIFIED)
            portfolio = self.client.get(reverse("document-portfolio"))
            self.assertContains(portfolio, "100%")

    def test_document_locker_uses_saved_tamil_language(self):
        self.user.preferred_language = "ta"
        self.user.save(update_fields=["preferred_language"])

        response = self.client.get(reverse("document-upload"), HTTP_ACCEPT_LANGUAGE="hi")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["request"].LANGUAGE_CODE, "ta")
        self.assertContains(response, "எனது ஆவணங்கள்")

    def test_portfolio_localizes_certificate_names_to_tamil(self):
        self.user.preferred_language = "ta"
        self.user.save(update_fields=["preferred_language"])

        response = self.client.get(reverse("document-portfolio"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ஆதார் அட்டை")
