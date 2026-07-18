# Generated for LeadSathi Phase 4 WhatsApp integration.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("agencies", "0003_agency_whatsapp_fields"),
        ("leads", "0003_lead_budget_max_lead_budget_min_lead_preferred_bhk_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="WhatsAppConversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_phone", models.CharField(db_index=True, max_length=32)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("started", "Started"),
                            ("asked_name", "Asked name"),
                            ("asked_budget", "Asked budget"),
                            ("asked_bhk", "Asked BHK"),
                            ("asked_location", "Asked location"),
                            ("completed", "Completed"),
                            ("handed_off", "Handed off"),
                        ],
                        default="started",
                        max_length=32,
                    ),
                ),
                ("collected_data", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "agency",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="whatsapp_conversations",
                        to="agencies.agency",
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="whatsapp_conversations",
                        to="leads.lead",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="WhatsAppMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "direction",
                    models.CharField(
                        choices=[("inbound", "Inbound"), ("outbound", "Outbound")],
                        max_length=12,
                    ),
                ),
                ("message_id", models.CharField(max_length=255, unique=True)),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="whatsapp.whatsappconversation",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="whatsappconversation",
            index=models.Index(
                fields=["agency", "customer_phone", "is_active"],
                name="wa_conv_route_idx",
            ),
        ),
    ]

