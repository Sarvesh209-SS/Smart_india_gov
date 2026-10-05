from django.db import migrations


DOCUMENT_TYPES = (
    "Aadhaar card",
    "Community certificate",
    "Income certificate",
    "Nativity certificate",
    "Birth certificate",
    "PAN card",
    "Bank passbook",
    "10th certificate",
    "12th certificate",
    "Graduation certificate",
    "Other",
)


def seed_document_types(apps, schema_editor):
    document_type = apps.get_model("documents", "DocumentType")
    database = schema_editor.connection.alias
    for name in DOCUMENT_TYPES:
        document_type.objects.using(database).get_or_create(name=name)


def keep_document_types(_apps, _schema_editor):
    del _apps, _schema_editor


class Migration(migrations.Migration):
    dependencies = [("documents", "0002_document_file_size_document_file_type_and_more")]

    operations = [migrations.RunPython(seed_document_types, keep_document_types)]
