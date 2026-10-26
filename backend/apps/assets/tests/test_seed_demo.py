"""
seed_demo prepara la base de la demo con el cliente. Se niega a correr fuera de
una base «demo» y, donde corre, arma lo esencial con los servicios del dominio.
"""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


def test_se_niega_fuera_de_una_base_demo():
    # DB_NAME de las pruebas no lleva «demo»: ni siquiera toca la base.
    with pytest.raises(CommandError, match="no parece una base de demo"):
        call_command("seed_demo")


@pytest.mark.django_db
def test_en_una_base_de_prueba_crea_lo_esencial():
    from apps.assets.models import Asset, Contract, Hospital
    from apps.checklists.models import ChecklistField
    from apps.evidence.models import Photo, Signature
    from apps.maintenance.models import PlanTask, Task
    from apps.users.models import User
    from apps.work_orders.models import Finding, WorkOrder

    # «test» está en el nombre de la base de pruebas; --sin-actas evita WeasyPrint.
    call_command("seed_demo", marcador="test", sin_actas=True, verbosity=0)

    assert Hospital.objects.count() == 2
    assert Asset.objects.count() >= 12
    assert set(User.objects.values_list("role", flat=True)) == {"ADMIN", "SUP", "TEC", "CLI"}
    cli = User.objects.get(role="CLI")
    assert cli.hospital.name == "Clínica Demo Norte"

    assert not ChecklistField.objects.filter(field_type__in=["PHOTO", "SIGNATURE"]).exists()
    assert ChecklistField.objects.filter(field_type="GPS").exists()
    assert PlanTask.objects.filter(trigger="WHEN", meter_comparator="LT").exists()

    assert WorkOrder.objects.filter(status="COMPLETED").count() >= 6
    assert Photo.objects.filter(stage="BEFORE").exists() and Photo.objects.filter(stage="AFTER").exists()
    assert Signature.objects.filter(signature_type="TECHNICIAN").exists()

    en_vivo = WorkOrder.objects.get(status="PENDING", hospital__name="Clínica Demo Norte")
    assert en_vivo.location.name.startswith("Piso 1")
    assert en_vivo.tasks.count() == 2 and en_vivo.assigned_to.role == "TEC"

    pendientes = Finding.objects.filter(status="PENDING")
    assert pendientes.count() == 2 and pendientes.filter(severity="CRITICAL", out_of_service=True).exists()
    assert Contract.objects.filter(kind="MAINTENANCE").exists() and Contract.objects.filter(kind="WARRANTY").exists()
    assert Task.objects.filter(status="PENDING", scheduled_date__lt=en_vivo.scheduled_date).exists()

    # Con datos de demo no vuelve a correr: explica cómo empezar de cero.
    with pytest.raises(CommandError, match="empezar de cero"):
        call_command("seed_demo", marcador="test", sin_actas=True, verbosity=0)
