# Generated for LeadSathi Phase 4 WhatsApp integration.

import apps.whatsapp.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agencies", "0002_alter_agency_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="agency",
            name="whatsapp_phone_number_id",
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="agency",
            name="whatsapp_business_account_id",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="agency",
            name="whatsapp_access_token",
            field=apps.whatsapp.fields.EncryptedTextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="agency",
            name="whatsapp_display_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="agency",
            name="whatsapp_status",
            field=models.CharField(
                choices=[
                    ("not_connected", "Not connected"),
                    ("connected", "Connected"),
                    ("error", "Error"),
                ],
                default="not_connected",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="agency",
            name="whatsapp_connected_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

