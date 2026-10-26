from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("evidence", "0006_fotos_ocultas_del_acta"),
    ]

    operations = [
        migrations.AddField(
            model_name="photo",
            name="stage",
            field=models.CharField(
                blank=True,
                choices=[("BEFORE", "Antes"), ("AFTER", "Después"), ("", "Sin etiqueta")],
                default="",
                max_length=6,
            ),
        ),
    ]
