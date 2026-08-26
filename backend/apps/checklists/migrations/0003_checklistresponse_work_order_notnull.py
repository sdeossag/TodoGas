import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checklists', '0002_initial'),
        ('work_orders', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='checklistresponse',
            name='work_order',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='checklist_response',
                to='work_orders.workorder',
            ),
        ),
    ]
