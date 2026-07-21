from django.db import migrations


def migrate_free_to_starter(apps, schema_editor):
    Agency = apps.get_model("agencies", "Agency")
    Agency.objects.filter(plan_tier="free").update(plan_tier="starter")


def migrate_starter_to_free(apps, schema_editor):
    Agency = apps.get_model("agencies", "Agency")
    Agency.objects.filter(plan_tier="starter").update(plan_tier="free")


class Migration(migrations.Migration):

    dependencies = [
        ("agencies", "0005_rename_pro_to_growth"),
    ]

    operations = [
        migrations.RunPython(migrate_free_to_starter, reverse_code=migrate_starter_to_free),
    ]
