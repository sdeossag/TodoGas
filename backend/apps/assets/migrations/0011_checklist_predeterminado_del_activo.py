import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0010_activo_de_ubicacion'),
        ('checklists', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='default_checklist_template',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='default_for_assets',
                to='checklists.checklisttemplate',
            ),
        ),
    ]
