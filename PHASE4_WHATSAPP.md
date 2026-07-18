# LeadSathi Phase 4 - Multi-Tenant WhatsApp Bot

## File Tree

- `leadrescue/apps/agencies/models.py` - per-agency WhatsApp credential fields.
- `leadrescue/apps/agencies/migrations/0003_agency_whatsapp_fields.py` - agency credential migration.
- `leadrescue/apps/whatsapp/` - WhatsApp app, models, webhook, tasks, forms, services, tests.
- `leadrescue/templates/whatsapp/settings.html` - owner-only manual connection page.
- `leadrescue/apps/leads/views.py` and `leadrescue/templates/leads/lead_detail.html` - manual WhatsApp follow-up action.
- `leadrescue/config/settings.py`, `leadrescue/config/urls.py`, `leadrescue/config/celery.py` - app registration, URLs, Celery config.
- `.env.example`, `render.yaml`, `Procfile`, `requirements.txt` - local and deployment configuration.

## Required Installs

```bash
pip install "celery>=5.4,<6" "redis>=5,<7" "django-celery-beat>=2.6,<3" "cryptography>=42"
```

The encrypted token field uses `cryptography.Fernet` through `apps.whatsapp.fields.EncryptedTextField`.

## Environment

App-level Meta settings only:

```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=${REDIS_URL}
WHATSAPP_APP_ID=
WHATSAPP_APP_SECRET=
WHATSAPP_WEBHOOK_VERIFY_TOKEN=
FIELD_ENCRYPTION_KEY=
```

Agency-level WhatsApp credentials are entered at `/settings/whatsapp/` and stored encrypted in the database.

## Local Verification

```bash
cd leadrescue
DATABASE_URL=sqlite:///test_whatsapp.sqlite3 ../.venv/bin/python manage.py test apps.whatsapp
../.venv/bin/python manage.py makemigrations --check --dry-run
```

Covered cases:

- Full webhook conversation through all states creates a WhatsApp lead with mapped budget, BHK, and location.
- Two agencies with different `phone_number_id` values route to separate conversations and leads.
- Duplicate WhatsApp `message_id` values are not reprocessed.
- Invalid webhook signatures return `403`.
- Agencies not in `CONNECTED` status are not matched by the webhook.
- Round-robin assignment uses the least recently assigned active agent.
- Bad settings-page tokens do not save the pasted credentials.

## End-to-End With Ngrok

1. Run Redis locally: `redis-server`.
2. Run Django: `cd leadrescue && ../.venv/bin/python manage.py runserver 8000`.
3. Run Celery: `cd leadrescue && ../.venv/bin/celery -A config worker --loglevel=info`.
4. Expose Django: `ngrok http 8000`.
5. In Meta, set webhook callback URL to `https://<ngrok-host>/webhooks/whatsapp/`.
6. Use the `.env` `WHATSAPP_WEBHOOK_VERIFY_TOKEN` for webhook verification.
7. Log in as an owner and enter the test number's Phone Number ID, WABA ID, and access token at `/settings/whatsapp/`.
8. Send messages to the connected test number and confirm the lead appears under that same agency.

## Render Deployment

Deploy three services:

- Web service: existing Django/Gunicorn service.
- Worker service: `cd leadrescue && celery -A config worker --loglevel=info`.
- Redis service: used by `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND`.

Set `WHATSAPP_APP_ID`, `WHATSAPP_APP_SECRET`, `WHATSAPP_WEBHOOK_VERIFY_TOKEN`, and a stable `FIELD_ENCRYPTION_KEY` as Render environment variables. Do not store agency phone number IDs, WABA IDs, or agency access tokens in Render env vars.
