from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evidence", "0008_firma_guardada_del_usuario"),
    ]

    operations = [
        migrations.AlterField(
            model_name="signature",
            name="signature_type",
            field=models.CharField(
                choices=[
                    ("TECHNICIAN", "Firma del técnico"),
                    ("CLIENT", "Firma del cliente"),
                    ("VALIDATION", "Firma de validación"),
                ],
                max_length=12,
            ),
        ),
    ]
