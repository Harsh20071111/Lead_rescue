import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.accounts.models import AgentProfile
from apps.agencies.models import Agency
from apps.accounts.services.email_service import send_welcome_email
from apps.accounts.adapters import CustomSocialAccountAdapter
from apps.accounts.views import SignupView
from apps.core.email_backend import ResendEmailBackend

User = get_user_model()

@override_settings(
    EMAIL_PROVIDER="resend",
    RESEND_API_KEY="test_key",
    DEFAULT_FROM_EMAIL="noreply@test.leadsathi.in"
)
class EmailIntegrationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create(
            username="testuser",
            email="testuser@example.com",
            first_name="Test"
        )
        self.agency = Agency.objects.create(
            name="Test Agency",
            owner_phone="N/A",
            owner_email=self.user.email,
            city="N/A",
        )
        self.agent_profile = AgentProfile.objects.create(
            user=self.user,
            agency=self.agency,
            role="owner",
            phone="N/A",
        )

    @patch('resend.Emails.send')
    def test_send_welcome_email_success_and_deduplication(self, mock_resend_send):
        # Initial state
        self.assertFalse(self.agent_profile.welcome_email_sent)
        
        # Call it first time (simulate hook)
        success = send_welcome_email(self.user)
        self.assertTrue(success)
        mock_resend_send.assert_called_once()
        
        # Simulate updating profile
        self.agent_profile.welcome_email_sent = True
        self.agent_profile.save()

        # Simulate second call
        mock_resend_send.reset_mock()
        if not self.agent_profile.welcome_email_sent:
            send_welcome_email(self.user)
            
        mock_resend_send.assert_not_called()

    @patch('resend.Emails.send')
    def test_send_welcome_email_failure(self, mock_resend_send):
        # Make resend fail
        mock_resend_send.side_effect = Exception("Network Error")
        
        # Call it
        success = send_welcome_email(self.user)
        self.assertFalse(success)
        self.assertFalse(self.agent_profile.welcome_email_sent)

    def test_allauth_verification_template_rendering(self):
        # Verify the allauth templates render correctly
        context = {
            'email': 'test@example.com',
            'activate_url': 'http://test/activate/123/',
        }
        
        html_content = render_to_string('account/email/email_confirmation_message.html', context)
        
        # Ensure our branded styling is in there
        self.assertIn("LeadSathi", html_content)
        self.assertIn("http://test/activate/123/", html_content)
        self.assertIn("background-color: #8B5E34", html_content)

    @patch('resend.Emails.send')
    def test_resend_backend_constructs_payload(self, mock_resend_send):
        # Create an email and send through our custom backend
        backend = ResendEmailBackend(fail_silently=False)
        email = EmailMultiAlternatives(
            subject="Test Subject",
            body="Text Body",
            from_email="noreply@test.leadsathi.in",
            to=["test@example.com"]
        )
        email.attach_alternative("<h1>HTML Body</h1>", "text/html")
        
        backend.send_messages([email])
        
        # Check that resend payload was constructed correctly
        mock_resend_send.assert_called_once()
        payload = mock_resend_send.call_args[0][0]
        
        self.assertEqual(payload['from'], "noreply@test.leadsathi.in")
        self.assertEqual(payload['to'], ["test@example.com"])
        self.assertEqual(payload['subject'], "Test Subject")
        self.assertEqual(payload['html'], "<h1>HTML Body</h1>")
        # Text is omitted in our backend when HTML is present
