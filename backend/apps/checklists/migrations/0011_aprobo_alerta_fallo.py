from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checklists', '0010_pendientes_del_checklist'),
    ]

    operations = [
        migrations.AlterField(
            model_name='checklistfield',
            name='field_type',
            field=models.CharField(choices=[('TEXT', 'Texto libre'), ('NUMBER', 'Valor numérico'), ('BOOLEAN', 'Sí/No (checkbox)'), ('SELECT', 'Selección única'), ('MULTI_SELECT', 'Selección múltiple'), ('PHOTO', 'Fotografía'), ('SIGNATURE', 'Firma digital'), ('GPS', 'Localización GPS'), ('METER', 'Lectura de medidor'), ('DATE', 'Fecha'), ('DATETIME', 'Fecha y hora'), ('TEXTAREA', 'Texto largo'), ('PASS_ALERT_FAIL', 'Aprobó / Alerta / Falló')], max_length=15),
        ),
    ]
