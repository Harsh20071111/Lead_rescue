from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


NEW_ADMIN_EMAIL = "kamleshpanchal21121983@gmail.com"
NEW_ADMIN_PASSWORD = "Harsh2007"
DEMOTE_EMAILS = [
    "harshpanchal200011@gmail.com",
    "admin@example.com",
]


class Command(BaseCommand):
    help = "Enforce single superuser: demote old ones, create/update the new admin."

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

        try:
            user = User.objects.get(email=NEW_ADMIN_EMAIL)
            user.set_password(NEW_ADMIN_PASSWORD)
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.save(update_fields=["password", "is_superuser", "is_staff", "is_active"])
            self.stdout.write(self.style.SUCCESS(f"Updated {NEW_ADMIN_EMAIL} → superuser"))
        except User.DoesNotExist:
            user = User.objects.create_superuser(
                email=NEW_ADMIN_EMAIL,
                username=NEW_ADMIN_EMAIL,
                password=NEW_ADMIN_PASSWORD,
            )
            self.stdout.write(self.style.SUCCESS(f"Created {NEW_ADMIN_EMAIL} → superuser"))
