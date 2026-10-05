from django.db import migrations


def promote_superusers(apps, schema_editor):
    user = apps.get_model("accounts", "User")
    users = user.objects.using(schema_editor.connection.alias)
    users.filter(is_superuser=True).update(role="SUPER_ADMIN")
    users.filter(is_verified=True, mobile__isnull=False).exclude(mobile="").update(mobile_verified=True)


def preserve_roles(_apps, _schema_editor):
    del _apps, _schema_editor


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_auditevent_subject")]

    operations = [migrations.RunPython(promote_superusers, preserve_roles)]
