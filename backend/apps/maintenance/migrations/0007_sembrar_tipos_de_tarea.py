"""
Los tipos de tarea que usa el cliente en Fracttal (Plan de Tareas -> Tipo de
Tarea, revisado el 2026-09-18). Los cinco de siempre conservan su codigo; los
demas lo toman del nombre. "AREA DE URGENCIAS.EJE EH-ENTRE 1-4" no entra: es
una ubicacion cargada por error como tipo.

`counts_as` es el punto de partida; el administrador lo cambia en el catalogo.
"""

from django.db import migrations

# (codigo, nombre, cuenta como, del sistema)
TIPOS = [
    ("PREVENTIVE", "Preventivo", "PREVENTIVE", True),
    ("CORRECTIVE", "Correctivo", "CORRECTIVE", True),
    ("VERIFICATION", "Verificación", "OTHER", True),
    ("INSTALLATION", "Instalación", "OTHER", True),
    ("DELIVERY", "Entrega", "OTHER", True),
    ("ACOMPANAMIENTO", "Acompañamiento", "OTHER", False),
    ("ACTA_DE_PROYECTOS", "Acta de proyectos", "OTHER", False),
    ("AJUSTE", "Ajuste", "CORRECTIVE", False),
    ("BARRIDO", "Barrido", "OTHER", False),
    ("CALIBRACION", "Calibración", "PREVENTIVE", False),
    ("CAMBIO_DE_FILTROS", "Cambio de filtros", "PREVENTIVE", False),
    ("CAMBIO_DE_SENSORES", "Cambio de sensores", "PREVENTIVE", False),
    ("CAPACITACION", "Capacitación", "OTHER", False),
    ("DIAGNOSTICO", "Diagnóstico", "CORRECTIVE", False),
    ("ENTREGA_PROYECTO", "Entrega de proyecto", "OTHER", False),
    ("FIDELIZACION", "Fidelización", "OTHER", False),
    ("GARANTIA", "Garantía", "CORRECTIVE", False),
    ("LAVADO_DE_TUBERIA", "Lista de chequeo para lavado de tubería de gases medicinales", "PREVENTIVE", False),
    ("PRUEBA_DE_REDES", "Prueba de redes de gases medicinales", "PREVENTIVE", False),
    ("RETIRO", "Retiro", "OTHER", False),
]


def sembrar(apps, schema_editor):
    Catalogo = apps.get_model("maintenance", "TaskTypeCatalog")
    for orden, (code, name, counts_as, is_system) in enumerate(TIPOS):
        Catalogo.objects.update_or_create(
            code=code,
            defaults={"name": name, "counts_as": counts_as, "is_system": is_system, "sort_order": orden},
        )
    # Cualquier codigo ya guardado que no este arriba queda en el catalogo (inactivo)
    # para que ninguna tarea ni OT se quede sin nombre.
    usados = set()
    for app, modelo in (("maintenance", "PlanTask"), ("maintenance", "Task"), ("work_orders", "WorkOrder")):
        usados |= set(apps.get_model(app, modelo).objects.values_list("task_type", flat=True).distinct())
    conocidos = set(Catalogo.objects.values_list("code", flat=True))
    for code in sorted(usados - conocidos - {""}):
        Catalogo.objects.create(code=code, name=code, is_active=False, sort_order=100)


class Migration(migrations.Migration):

    dependencies = [
        ("maintenance", "0006_catalogo_tipos_de_tarea"),
        ("work_orders", "0007_tipo_de_tarea_del_catalogo"),
    ]

    operations = [
        migrations.RunPython(sembrar, migrations.RunPython.noop),
    ]
