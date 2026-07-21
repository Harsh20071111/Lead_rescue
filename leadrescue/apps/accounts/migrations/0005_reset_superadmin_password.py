"""
One-time data migration: reset superuser password for production access.
Safe to remove after first successful deploy.
"""
from django.contrib.auth.hashers import make_password
from django.db import migrations


def reset_superadmin_password(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    try:
        user = User.objects.get(email="harshpanchal200011@gmail.com")
        user.password = make_password("Harsh2007")
        user.save(update_fields=["password"])
        print(f"[migration] Password reset for {user.email}")
    except User.DoesNotExist:
        print("[migration] Target superuser not found, skipping password reset.")


def reverse(apps, schema_editor):
    """No-op — we don't roll back passwords."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_agentinvite"),
    ]

    operations = [
        migrations.RunPython(reset_superadmin_password, reverse),
    ]
