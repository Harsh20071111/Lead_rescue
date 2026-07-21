from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Reset superuser password to a known value for production access."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="harshpanchal200011@gmail.com")
        parser.add_argument("--password", default="Harsh2007")

    def handle(self, *args, **options):
        User = get_user_model()
        email = options["email"]
        password = options["password"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User {email} not found."))
            return

        user.set_password(password)
        user.save(update_fields=["password"])
        self.stdout.write(self.style.SUCCESS(f"Password reset for {email}"))
