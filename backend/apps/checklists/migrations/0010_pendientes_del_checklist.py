from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checklists', '0009_respuestas_corregidas'),
    ]

    operations = [
        migrations.AddField(
            model_name='checklistresponse',
            name='pendientes',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
