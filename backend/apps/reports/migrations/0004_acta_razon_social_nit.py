from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_acta_configurable'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportsettings',
            name='company_name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='reportsettings',
            name='company_tax_id',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
    ]
