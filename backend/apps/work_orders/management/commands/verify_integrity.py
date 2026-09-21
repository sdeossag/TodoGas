"""Verifica el acta de todas las OT cerradas contra lo que dice hoy la base.

    python manage.py verify_integrity
    python manage.py verify_integrity --hospital H-01 --detalle

Cada acta guarda el hash de contenido que se calculo al firmarla y la version
del algoritmo. El comando recalcula ese hash con la misma version y los
compara, igual que el endpoint /api/work-orders/{id}/integrity/ pero para
todas a la vez.

Sirve de control despues de una migracion de datos: si todas las actas que
verificaban antes siguen verificando, la migracion no toco nada probatorio.
Termina con error si alguna acta no verifica o usa una version desconocida,
para poder usarlo como compuerta en un despliegue.
"""

from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from apps.work_orders import integrity
from apps.work_orders.models import WorkOrder

ETIQUETAS = {
    integrity.VERIFIED: "Verifican",
    integrity.ALTERED: "NO verifican",
    integrity.UNKNOWN_VERSION: "Version desconocida",
    integrity.NO_HASH: "Sin hash (acta anterior al hash de contenido)",
    integrity.NO_REPORT: "Sin acta generada",
}


class Command(BaseCommand):
    help = "Verifica el hash de integridad de las actas de todas las OT cerradas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hospital", help="Codigo del hospital, para verificar solo sus OT."
        )
        parser.add_argument(
            "--detalle", action="store_true",
            help="Una linea por OT, no solo las que fallan.",
        )

    def handle(self, *args, **options):
        ots = WorkOrder.objects.filter(status=WorkOrder.Status.COMPLETED).order_by(
            "wo_number"
        )
        if options["hospital"]:
            ots = ots.filter(hospital__code=options["hospital"])

        conteo = Counter()
        por_version = Counter()
        fallas = []
        for ot in ots.iterator(chunk_size=200):
            resultado = integrity.verify_work_order(ot)
            conteo[resultado.outcome] += 1
            version = resultado.report.integrity_version if resultado.report else ""
            if resultado.outcome == integrity.VERIFIED:
                por_version[version] += 1
            if resultado.outcome in (integrity.ALTERED, integrity.UNKNOWN_VERSION):
                fallas.append((ot, resultado))
            if options["detalle"]:
                self.stdout.write(
                    f"  {ot.wo_code}  v{version or '-'}  {ETIQUETAS[resultado.outcome]}"
                )

        total = sum(conteo.values())
        self.stdout.write(f"OT cerradas revisadas: {total}")
        for outcome, etiqueta in ETIQUETAS.items():
            linea = f"  {etiqueta}: {conteo[outcome]}"
            if outcome == integrity.VERIFIED and por_version:
                versiones = ", ".join(f"v{v}: {n}" for v, n in sorted(por_version.items()))
                linea += f"  ({versiones})"
            self.stdout.write(linea)

        if not fallas:
            self.stdout.write(self.style.SUCCESS("Todas las actas con hash verifican."))
            return

        self.stdout.write("")
        for ot, resultado in fallas:
            report = resultado.report
            if resultado.outcome == integrity.ALTERED:
                self.stdout.write(self.style.ERROR(
                    f"  {ot.wo_code}  v{report.integrity_version}  "
                    f"guardado {report.content_hash[:16]}  "
                    f"recalculado {resultado.recomputed_hash[:16]}"
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"  {ot.wo_code}  version {report.integrity_version or 'vacia'} "
                    "desconocida"
                ))
        raise CommandError(f"{len(fallas)} acta(s) no verifican.")
