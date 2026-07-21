from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


DEMOTE_EMAILS = [
    "harshpanchal200011@gmail.com",
    "admin@example.com",
    "kamleshpanchal21121983@gmail.com",
]


class Command(BaseCommand):
    help = "Demote old superusers. Pass --email and --password to create a new one."

    def add_arguments(self, parser):
        parser.add_argument("--email", default=None)
        parser.add_argument("--password", default=None)

    def handle(self, *args, **options):
        User = get_user_model()

        for email in DEMOTE_EMAILS:
            try:
                user = User.objects.get(email=email)
                if user.is_superuser or user.is_staff:
                    user.is_superuser = False
                    user.is_staff = False
                    user.save(update_fields=["is_superuser", "is_staff"])
                    self.stdout.write(f"Demoted {email}")
            except User.DoesNotExist:
                pass

        email = options.get("email")
        password = options.get("password")
        if not email or not password:
            self.stdout.write("No --email/--password provided, demotions only.")
            return

        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.save(update_fields=["password", "is_superuser", "is_staff", "is_active"])
            self.stdout.write(self.style.SUCCESS(f"Updated {email} → superuser"))
        except User.DoesNotExist:
            user = User.objects.create_superuser(
                email=email,
                username=email,
                password=password,
            )
            self.stdout.write(self.style.SUCCESS(f"Created {email} → superuser"))
