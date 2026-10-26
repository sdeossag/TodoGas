# Permisos adicionales por usuario (apps.users.permisos). Solo crea la tabla:
# no toca ningun dato y se deshace borrandola.

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alcance_por_nodo'),
    ]

    operations = [
        migrations.CreateModel(
            name='PermisoExtra',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('codigo', models.CharField(max_length=50)),
                ('otorgado_en', models.DateTimeField(default=django.utils.timezone.now)),
                ('otorgado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='permisos_otorgados', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='permisos_extra', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'users_permisoextra',
                'ordering': ['codigo'],
                'constraints': [models.UniqueConstraint(fields=('user', 'codigo'), name='uniq_permiso_extra_usuario_codigo')],
            },
        ),
    ]
