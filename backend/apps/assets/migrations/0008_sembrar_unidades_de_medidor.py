"""
Las seis unidades de medidor que el cliente tiene en Fracttal (revision del
2026-09-19). HORAS es la unica que acumula: sobre ella se programa "cada N
horas". inHg es vacio; PSI, presion de gas.
"""

from django.db import migrations

UNIDADES = [
    ("AMPERIOS", "A", False),
    ("HORAS", "H", True),
    ("PRESION", "inHg", False),
    ("PRESION", "PSI", False),
    ("TEMPERATURA", "°C", False),
    ("VOLTAJE", "V", False),
]


def sembrar(apps, schema_editor):
    MeterUnit = apps.get_model("assets", "MeterUnit")
    for orden, (name, symbol, is_counter) in enumerate(UNIDADES):
        MeterUnit.objects.update_or_create(
            name=name, symbol=symbol, defaults={"is_counter": is_counter, "sort_order": orden},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0007_medidores_y_lecturas"),
    ]

    operations = [
        migrations.RunPython(sembrar, migrations.RunPython.noop),
    ]
