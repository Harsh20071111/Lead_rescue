import io
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile
from apps.imports.models import ImportJob
from apps.leads.models import Lead
from apps.imports.tasks import process_import_job

User = get_user_model()

class ImportJobTestCase(TestCase):
    def setUp(self):
        self.agency = Agency.objects.create(name="Test Agency")
        self.user = User.objects.create_user(username="test@example.com", email="test@example.com", password="password")
        self.agent = AgentProfile.objects.create(user=self.user, agency=self.agency, role="owner")
        
    def test_lead_import_csv(self):
        csv_content = b"client_name,client_phone,budget,bhk,location\nJohn Doe,1234567890,50 lakh,2 bhk,Downtown\n"
        csv_file = SimpleUploadedFile("test_leads.csv", csv_content, content_type="text/csv")
        
        job = ImportJob.objects.create(
            agency=self.agency,
            initiated_by=self.agent,
            target_model=ImportJob.TargetModel.LEAD,
            file=csv_file,
            status=ImportJob.Status.MAPPING,
            column_mapping={
                "name": "client_name",
                "phone": "client_phone",
                "budget": "budget",
                "bhk": "bhk",
                "location": "location"
            }
        )
        
        # Run Celery task synchronously for testing
        process_import_job(job.id)
        
        job.refresh_from_db()
        self.assertEqual(job.status, ImportJob.Status.COMPLETED)
        self.assertEqual(job.successful_rows, 1)
        self.assertEqual(job.failed_rows, 0)
        
        # Verify lead creation
        lead = Lead.objects.filter(agency=self.agency, phone="1234567890").first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.name, "John Doe")
        self.assertEqual(lead.source, Lead.LeadSource.IMPORT)
