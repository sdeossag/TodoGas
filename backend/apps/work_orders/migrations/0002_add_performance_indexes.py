from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("work_orders", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="workorder",
            index=models.Index(
                fields=["status", "scheduled_date"],
                name="idx_wo_status_scheduled",
            ),
        ),
        migrations.AddIndex(
            model_name="workorder",
            index=models.Index(
                fields=["maintenance_plan", "status"],
                name="idx_wo_plan_status",
            ),
        ),
        migrations.AddIndex(
            model_name="workorder",
            index=models.Index(
                fields=["assigned_to", "status"],
                name="idx_wo_assignee_status",
            ),
        ),
    ]
