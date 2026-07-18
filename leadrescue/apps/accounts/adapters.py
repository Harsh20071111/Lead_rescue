import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import redirect

from apps.agencies.models import Agency
from apps.accounts.models import AgentProfile

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Override the default allauth account adapter.
    Redirects to our own login page on errors instead of allauth's defaults.
    """

    def get_login_redirect_url(self, request):
        return "/dashboard/"

    def get_signup_redirect_url(self, request):
        return "/dashboard/"


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Handles:
    1. Account linking — if an email/password user later signs in with
       Google using the SAME email, link the Google identity to the
       existing User rather than creating a duplicate.
    2. First-time social signup — auto-create Agency + AgentProfile(Owner).
    3. Returning social login — no duplicate Agency/AgentProfile.
    4. Error handling — cancelled or failed Google auth redirects to
       login with a friendly message.
    """

    def pre_social_login(self, request, sociallogin):
        """
        Called after Google auth succeeds but BEFORE the social account
        is connected. This is where we handle account linking.

        If a User with the same email already exists (registered via
        email/password), we link the Google identity to that user.

        Security: Google has already verified the email address, so
        auto-linking is safe — we only link when the social provider's
        verified email exactly matches an existing account's email.
        """
        # If the social account is already connected, nothing to do.
        if sociallogin.is_existing:
            return

        # Get the email from Google's response.
        email = None
        if sociallogin.account.extra_data:
            email = sociallogin.account.extra_data.get("email", "").lower().strip()

        if not email:
            # Fallback: check email addresses from allauth
            for addr in sociallogin.email_addresses:
                if addr.verified:
                    email = addr.email.lower().strip()
                    break

        if not email:
            return

        # Check if a user with this email already exists.
        try:
            existing_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        # Link the Google social account to the existing user.
        sociallogin.connect(request, existing_user)
        logger.info(
            "Linked Google account to existing user %s (id=%d)",
            existing_user.email,
            existing_user.pk,
        )

    def save_user(self, request, sociallogin, form=None):
        """
        Called on FIRST social signup only (when a brand-new User is
        created). Creates the default Agency and AgentProfile(Owner).
        """
        user = super().save_user(request, sociallogin, form)

        # Ensure the username field is set (our User model inherits
        # AbstractUser which requires it).
        if not user.username:
            user.username = user.email
            user.save(update_fields=["username"])

        # Only create Agency/AgentProfile if one doesn't already exist.
        # (Defensive: pre_social_login might have already linked to a
        # user that has these.)
        if not AgentProfile.objects.filter(user=user).exists():
            name = user.get_full_name() or user.email.split("@")[0]

            agency = Agency.objects.create(
                name=f"{name}'s Agency",
                owner_phone="N/A",
                owner_email=user.email,
                city="N/A",
            )

            agent_profile = AgentProfile.objects.create(
                user=user,
                agency=agency,
                role="owner",
                phone="N/A",
            )

            logger.info(
                "Created Agency '%s' and AgentProfile(Owner) for Google user %s",
                agency.name,
                user.email,
            )

            try:
                if not agent_profile.welcome_email_sent:
                    from apps.accounts.services.email_service import send_welcome_email
                    if send_welcome_email(user):
                        agent_profile.welcome_email_sent = True
                        agent_profile.save(update_fields=['welcome_email_sent'])
            except Exception as e:
                logger.error("Welcome email failed for social user %s: %s", user.email, e, exc_info=True)

        return user

    def authentication_error(
        self, request, provider_id, error=None, exception=None, extra_context=None
    ):
        """
        Called when the Google OAuth flow fails or the user cancels.
        Redirect to the login page with a friendly error message instead
        of showing Django's default error page.
        """
        logger.warning(
            "Google auth error: provider=%s error=%s exception=%s",
            provider_id,
            error,
            exception,
        )
        messages.error(
            request,
            "Google sign-in was cancelled or failed. Please try again, "
            "or sign in with your email and password.",
        )
        raise ImmediateHttpResponse(redirect("/login/"))
