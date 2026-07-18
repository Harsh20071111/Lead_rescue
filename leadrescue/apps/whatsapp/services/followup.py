from apps.whatsapp.services.client import send_template


def send_followup_whatsapp(lead, template_name="lead_follow_up"):
    return send_template(lead.agency, lead.phone, template_name, [lead.name])

