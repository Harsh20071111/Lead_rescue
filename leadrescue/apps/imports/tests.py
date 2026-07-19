import io
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile
from apps.imports.models import ImportJob
from apps.leads.models import Lead
from apps.imports.services.column_matcher import match_columns

User = get_user_model()

class ImportJobTestCase(TestCase):
    def setUp(self):
        self.agency = Agency.objects.create(name="Test Agency")
        self.user = User.objects.create_user(username="test@example.com", email="test@example.com", password="password")
        self.agent = AgentProfile.objects.create(user=self.user, agency=self.agency, role="owner")
        self.client.force_login(self.user)

    def test_upload_form_enctype(self):
        """1. Verify the upload form has enctype='multipart/form-data' (Part A fix)."""
        response = self.client.get(reverse("imports:import_upload"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_high_confidence_auto_map_skips_mapping_screen(self):
        """2. High-confidence auto-map correctly skips the manual mapping screen."""
        csv_content = b"Client Name,Ph No,Budget\nJane Doe,9876543210,75 lakh\n"
        csv_file = SimpleUploadedFile("upload_leads.csv", csv_content, content_type="text/csv")

        response = self.client.post(
            reverse("imports:import_upload"),
            {"target_model": ImportJob.TargetModel.LEAD, "file": csv_file},
        )
        # Should redirect directly to progress screen, skipping mapping
        job = ImportJob.objects.latest("created_at")
        self.assertRedirects(response, reverse("imports:import_progress", args=[job.id]))
        # Ensure mapping was saved automatically
        self.assertEqual(job.column_mapping.get("name"), "Client Name")
        self.assertEqual(job.column_mapping.get("phone"), "Ph No")

    def test_ambiguous_header_falls_back_to_manual_mapping(self):
        """3. Ambiguous/unrecognizable header falls back to manual mapping, with known fields pre-filled."""
        # 'Col4' will not match any required field confidently (e.g. phone is missing)
        csv_content = b"Client Name,Col4,Budget\nJane Doe,9876543210,75 lakh\n"
        csv_file = SimpleUploadedFile("upload_leads2.csv", csv_content, content_type="text/csv")

        response = self.client.post(
            reverse("imports:import_upload"),
            {"target_model": ImportJob.TargetModel.LEAD, "file": csv_file},
        )
        job = ImportJob.objects.latest("created_at")
        # Should redirect to mapping screen because 'phone' is missing
        self.assertRedirects(response, reverse("imports:import_mapping", args=[job.id]))
        
        # Check that the mapping screen contains the pre-filled 'Client Name' for 'name'
        response = self.client.get(reverse("imports:import_mapping", args=[job.id]))
        self.assertContains(response, 'Client Name')
        # Check transparency UI
        self.assertContains(response, 'Auto-Mapped Columns')

    def test_multiple_columns_fuzzy_matching_resolve_correctly(self):
        """4. Two columns that both fuzzy-match 'phone' resolve to only one being assigned."""
        headers = ["Phone1", "Ph No", "Client Name"]
        target_fields = ['name', 'phone']
        mapped, confidences = match_columns(headers, target_fields)
        
        self.assertIn('phone', mapped)
        self.assertEqual(mapped['phone'], 'Ph No') # 'Ph No' is an exact match synonym, so it should beat 'Phone1'
        self.assertEqual(mapped['name'], 'Client Name')
        self.assertEqual(len(mapped), 2) # Ensures no duplicate assignments for phone

    def test_end_to_end_zero_click_flow(self):
        """5. End-to-end test verifying Leads are created correctly in the database through the zero-click flow."""
        csv_content = b"Full Name,Mobile No,Budget,City,Source\nJohn Wick,5550123,2 Cr,New York,Website\n"
        csv_file = SimpleUploadedFile("real_leads.csv", csv_content, content_type="text/csv")

        # The upload triggers inline CELERY task if eager is on, but we might need to rely on the views.py logic
        # Our `_queue_import_job` falls back to inline if Celery is down, or if CELERY_TASK_ALWAYS_EAGER is True.
        # Let's override settings to make celery eager for this test.
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            response = self.client.post(
                reverse("imports:import_upload"),
                {"target_model": ImportJob.TargetModel.LEAD, "file": csv_file},
            )

        job = ImportJob.objects.latest("created_at")
        self.assertRedirects(response, reverse("imports:import_progress", args=[job.id]))
        
        # Check the import actually ran
        job.refresh_from_db()
        self.assertEqual(job.status, ImportJob.Status.COMPLETED)
        self.assertEqual(job.successful_rows, 1)

        # Check lead was created correctly
        lead = Lead.objects.filter(agency=self.agency, phone="5550123").first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.name, "John Wick")
        self.assertEqual(lead.preferred_location, "New York")
        # Source 'Website' should map to something (perhaps default or IMPORT) depending on our logic
