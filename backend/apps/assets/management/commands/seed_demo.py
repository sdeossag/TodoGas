"""Datos de demostracion para el cliente, en una base aparte.

    DB_NAME=todogas_demo python manage.py seed_demo

Crea dos hospitales con su arbol de ubicaciones, 14 equipos, dos checklists
(mas uno de correctivos), dos protocolos, ocho OT finalizadas con su historia
(checklist respondido, fotos Antes/Despues, firmas, acta), tareas vencidas,
proximas y lejanas, dos hallazgos pendientes, un contrato por vencer, una
garantia y, lista para ejecutar en vivo desde el celular, una OT pendiente en
Urgencias de Clinica Demo Norte.

No escribe estados a mano: crea las OT con apps.maintenance.services y las
mueve con apps.work_orders.transitions, igual que la API. Para que la historia
caiga en los ultimos meses, el reloj de Django (`timezone.now`) se congela en
cada fecha pasada mientras se arma esa OT; al terminar vuelve a la hora real.

Seguridad: solo corre con los settings de desarrollo y sobre una base cuyo
nombre contenga "demo". Si ya hay datos de demo se detiene: para empezar de
cero se borra la base y se vuelve a crear (todos los FK son PROTECT, no hay
borrado en cascada). Ver docs/DEMO.md.

Las contrasenas de abajo son valores de prueba solo para esa base local.
"""

import hashlib
import io
import random
from contextlib import ExitStack
from datetime import datetime, time, timedelta
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from apps.assets.management.commands.completar_ubicaciones_demo import UBICACIONES

# ── Credenciales de prueba (solo para la base de demo) ───────────────────────
DOMINIO = "demo.todogas.local"
USUARIOS = {
    "admin": ("admin@" + DOMINIO, "TgDemo-Admin-2026", "Admin", "Demo", "ADMIN"),
    "sup": ("supervisor@" + DOMINIO, "TgDemo-Super-2026", "Supervisor", "Demo", "SUP"),
    "tec": ("tecnico@" + DOMINIO, "TgDemo-Tecnico-2026", "Técnico", "Demo", "TEC"),
    "cli": ("biomedica@" + DOMINIO, "TgDemo-Biomedica-2026", "Biomédica", "Demo", "CLI"),
}

CODIGO_NORTE = "DEMO-NORTE"
CODIGO_SUR = "DEMO-SUR"
MARCADOR = "demo"

# Las cuatro configuraciones que cada hospital necesita: se crean con el mismo
# codigo de equipo en el que se leen (N-... = Norte, S-... = Sur).
EQUIPOS = [
    # codigo, nombre, hospital, nodo, tipo, fabricante, modelo
    ("N-URG-O2-01", "Toma de oxígeno Urgencias 1", "N", "P1", "Toma de oxígeno", "Ohmeda", "DISS-O2"),
    ("N-URG-O2-02", "Toma de oxígeno Urgencias 2", "N", "P1", "Toma de oxígeno", "Ohmeda", "DISS-O2"),
    ("N-URG-AIR-01", "Toma de aire medicinal Urgencias", "N", "P1", "Toma de aire medicinal", "Ohmeda", "DISS-AIR"),
    ("N-URG-ALM-01", "Alarma de presión Urgencias", "N", "P1", "Alarma de presión", "Amico", "ALM-3"),
    ("N-URG-CV-01", "Caja de válvulas Urgencias", "N", "P1", "Caja de válvulas", "Amico", "VB-6"),
    ("N-HOS-O2-01", "Toma de oxígeno Hospitalización 301", "N", "P3", "Toma de oxígeno", "Ohmeda", "DISS-O2"),
    ("N-HOS-ALM-01", "Alarma de presión Hospitalización", "N", "P3", "Alarma de presión", "Amico", "ALM-3"),
    ("N-SOT-MAN-01", "Manifold de oxígeno", "N", "SOT", "Manifold de oxígeno", "Chart", "MFD-2x6"),
    ("N-SOT-CMP-01", "Compresor de aire medicinal", "N", "SOT", "Compresor de aire medicinal", "Atlas Copco", "GA-11"),
    ("S-URG-O2-01", "Toma de oxígeno Urgencias", "S", "P1", "Toma de oxígeno", "Ohmeda", "DISS-O2"),
    ("S-URG-ALM-01", "Alarma de presión Urgencias", "S", "P1", "Alarma de presión", "Amico", "ALM-3"),
    ("S-HOS-VAC-01", "Toma de vacío Hospitalización 305", "S", "P3", "Toma de vacío", "Ohmeda", "DISS-VAC"),
    ("S-HOS-CV-01", "Caja de válvulas Hospitalización", "S", "P3", "Caja de válvulas", "Amico", "VB-4"),
    ("S-SOT-BMB-01", "Bomba de vacío", "S", "SOT", "Bomba de vacío", "Busch", "R5-0100"),
]

FOTO_URL = "demo"  # carpeta en el almacenamiento


def verificar_entorno(marcador=MARCADOR):
    """Se niega fuera de desarrollo o fuera de una base cuyo nombre lleve `marcador`."""
    modulo = getattr(settings, "SETTINGS_MODULE", "") or ""
    if not modulo.endswith(".development"):
        raise CommandError(
            f"seed_demo solo corre con los settings de desarrollo (hoy: {modulo or 'desconocidos'}). "
            "No se hace nada."
        )
    nombre = connection.settings_dict["NAME"]
    if marcador.lower() not in str(nombre).lower():
        raise CommandError(
            f"La base «{nombre}» no parece una base de demo: su nombre no contiene «{marcador}». "
            "Para no mezclar datos de demostración con datos reales, el comando se niega. "
            "Usa otra base, por ejemplo: DB_NAME=todogas_demo python manage.py seed_demo "
            "(ver docs/DEMO.md)."
        )
    return nombre


def _explicar_reinicio(nombre):
    return (
        f"Ya hay datos de demostración en la base «{nombre}». "
        "El comando no borra ni duplica: todos los FK son PROTECT y no hay borrado en cascada. "
        "Para empezar de cero, borra la base y vuelve a crearla:\n"
        f"  psql -U <usuario> -d postgres -c \"DROP DATABASE {nombre};\"\n"
        f"  psql -U <usuario> -d postgres -c \"CREATE DATABASE {nombre};\"\n"
        f"  DB_NAME={nombre} python manage.py migrate\n"
        f"  DB_NAME={nombre} python manage.py seed_demo\n"
        "(el detalle está en docs/DEMO.md)."
    )


class Command(BaseCommand):
    help = "Carga datos de demostración realistas (solo en desarrollo y en una base «demo»)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--marcador", default=MARCADOR,
            help="Palabra que debe llevar el nombre de la base (por defecto «demo»). "
                 "Existe para poder probar el comando en la base de pruebas.",
        )
        parser.add_argument(
            "--sin-actas", action="store_true",
            help="No genera las actas PDF de las OT finalizadas.",
        )

    # ── entrada ──────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        nombre = verificar_entorno(options["marcador"])
        self._comprobar_vacia(nombre)

        self.rnd = random.Random(2026)
        self.ahora = timezone.now()
        self.hoy = timezone.localdate(self.ahora)
        self.reloj = self.ahora
        self.sin_actas = options["sin_actas"]
        self.actas_fallidas = []

        from apps.work_orders.models import WorkOrderStatusHistory

        campo_hist = WorkOrderStatusHistory._meta.get_field("changed_at")
        default_original = campo_hist.default

        with ExitStack() as pila:
            # Todo `timezone.now()` del dominio devuelve el reloj de la semilla.
            pila.enter_context(mock.patch.object(timezone, "now", lambda: self.reloj))
            # `default=timezone.now` guarda la funcion original: no la alcanza el
            # parche anterior y el historial de estados saldria con la hora real.
            campo_hist.default = lambda: timezone.now()
            campo_hist.__dict__.pop("_get_default", None)
            pila.callback(self._restaurar_default, campo_hist, default_original)
            if self.sin_actas:
                from apps.reports import tasks as tareas_reportes

                pila.enter_context(mock.patch.object(tareas_reportes.generate_work_order_pdf, "delay"))
            self._sembrar()

        self.reloj = self.ahora
        self._resumen(nombre)

    @staticmethod
    def _restaurar_default(campo, original):
        campo.default = original
        campo.__dict__.pop("_get_default", None)

    def _comprobar_vacia(self, nombre):
        from apps.assets.models import Hospital
        from apps.users.models import User

        hay = (
            Hospital.objects.filter(code__in=[CODIGO_NORTE, CODIGO_SUR]).exists()
            or User.objects.filter(email__endswith="@" + DOMINIO).exists()
        )
        if hay:
            raise CommandError(_explicar_reinicio(nombre))

    # ── reloj ────────────────────────────────────────────────────────────────

    def _en(self, dias_atras, hora=9, minuto=0):
        dia = self.hoy - timedelta(days=dias_atras)
        return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))

    def _fijar(self, momento):
        self.reloj = momento
        return momento

    def _fecha(self, dias_atras):
        return self.hoy - timedelta(days=dias_atras)

    # ── orquestacion ─────────────────────────────────────────────────────────

    def _sembrar(self):
        self._fijar(self._en(205, 8))
        self._usuarios()
        self._hospitales_y_arbol()
        self._unidades()
        self._equipos()
        self._checklists()
        self._protocolos()

        self._historia()          # OT finalizadas (y de paso las siguientes tareas)
        self._fijar(self.ahora)
        self._calendario()        # vencidas / proximas / lejanas
        self._lecturas()
        self._contratos()
        self._ot_en_vivo()

    # ── usuarios, hospitales, arbol ──────────────────────────────────────────

    def _usuarios(self):
        from apps.users.models import User

        self.u = {}
        for clave, (email, clave_acceso, nombre, apellido, rol) in USUARIOS.items():
            self.u[clave] = User.objects.create_user(
                email=email, password=clave_acceso, first_name=nombre, last_name=apellido,
                role=rol, is_staff=(rol == "ADMIN"),
                employee_code=f"DEMO-{rol}", phone="3000000000",
            )

    def _hospitales_y_arbol(self):
        from apps.assets.models import AssetNode, Hospital

        self.h = {
            "N": Hospital.objects.create(
                name="Clínica Demo Norte", code=CODIGO_NORTE, nit="900000001-1",
                address="Cra 15 # 100-12", city="Bogotá", department="Cundinamarca",
                contact_name="Biomédica Demo", contact_phone="3000000001",
                contact_email=USUARIOS["cli"][0],
                latitude=Decimal("4.6780000"), longitude=Decimal("-74.0480000"),
            ),
            "S": Hospital.objects.create(
                name="Hospital Demo Sur", code=CODIGO_SUR, nit="900000002-2",
                address="Cl 10 Sur # 50-30", city="Medellín", department="Antioquia",
                contact_name="Jefe de mantenimiento", contact_phone="3000000002",
                contact_email="mantenimiento.sur@" + DOMINIO,
                latitude=Decimal("6.2000000"), longitude=Decimal("-75.5700000"),
            ),
        }
        # La biomédica del cliente solo ve Clínica Demo Norte.
        self.u["cli"].hospital = self.h["N"]
        self.u["cli"].save(update_fields=["hospital", "updated_at"])
        self.n = {}

        def sitio(h, codigo):
            # Direccion y punto propios del nodo (los mismos que rellena
            # completar_ubicaciones_demo en una base ya creada).
            direccion, lat, lng = UBICACIONES[(h.code, codigo)]
            return {"address": direccion, "latitude": Decimal(lat), "longitude": Decimal(lng)}

        for k, h in self.h.items():
            bloque = AssetNode.objects.create(
                hospital=h, name="Bloque A", node_type="BUILDING", code=f"{k}-BA",
                **sitio(h, f"{k}-BA"),
            )
            self.n[(k, "P1")] = AssetNode.objects.create(
                hospital=h, parent=bloque, name="Piso 1 - Urgencias", node_type="FLOOR", code=f"{k}-P1",
                **sitio(h, f"{k}-P1"),
            )
            # Sin punto propio: hereda el del Bloque A.
            self.n[(k, "P3")] = AssetNode.objects.create(
                hospital=h, parent=bloque, name="Piso 3 - Hospitalización", node_type="FLOOR", code=f"{k}-P3",
            )
            self.n[(k, "SOT")] = AssetNode.objects.create(
                hospital=h, name="Sótano - Central de gases", node_type="AREA", code=f"{k}-SOT",
                **sitio(h, f"{k}-SOT"),
            )

    def _unidades(self):
        from apps.assets.models import MeterUnit

        self.psi, _ = MeterUnit.objects.get_or_create(
            name="PRESION", symbol="PSI", defaults={"is_counter": False, "sort_order": 3},
        )
        self.horas, _ = MeterUnit.objects.get_or_create(
            name="HORAS", symbol="H", defaults={"is_counter": True, "sort_order": 1},
        )

    def _equipos(self):
        from apps.assets.models import Asset

        self.a = {}
        for i, (codigo, nombre, h, nodo, tipo, fabricante, modelo) in enumerate(EQUIPOS, start=1):
            self.a[codigo] = Asset.objects.create(
                hospital=self.h[h], node=self.n[(h, nodo)], code=codigo, name=nombre,
                manufacturer=fabricante, model=modelo, serial_number=f"DEMO-{i:04d}",
                asset_type=tipo, classification_1="Gases medicinales",
                priority=Asset.Priority.HIGH if "ALM" in codigo or "CMP" in codigo else Asset.Priority.MEDIUM,
                installation_date=self._fecha(900 + i * 7),
                equipment_location=self.n[(h, nodo)].name,
            )

    # ── checklists ───────────────────────────────────────────────────────────

    def _publicar(self, nombre, descripcion, campos, grupos=()):
        from apps.checklists.models import (
            ChecklistField,
            ChecklistTemplate,
            ChecklistTemplateVersion,
        )

        plantilla = ChecklistTemplate.objects.create(name=nombre, description=descripcion, is_active=True)
        version = ChecklistTemplateVersion.objects.create(
            template=plantilla, version_number=1, published_by=self.u["admin"],
            published_at=self.reloj, is_current=True, repeatable_groups=list(grupos),
        )
        for orden, (etiqueta, tipo, grupo, obligatorio, opciones, ayuda) in enumerate(campos):
            ChecklistField.objects.create(
                version=version, label=etiqueta, field_type=tipo, group=grupo,
                is_required=obligatorio, sort_order=orden, options_json=opciones, help_text=ayuda,
            )
        return plantilla, version

    def _checklists(self):
        sin_na = {"allow_na": True}
        medidor = {"meter_unit": str(self.psi.id)}
        # Sin campos Foto ni Firma: la OT ya tiene fotos de evidencia y firmas.
        self.tpl_tomas, self.ver_tomas = self._publicar(
            "Mantenimiento de tomas",
            "Revisión de cada toma de la red de gases medicinales.",
            [
                ("Localización del punto", "GPS", "", False, [], "Toma las coordenadas junto a la toma."),
                ("Estado general", "BOOLEAN", "Toma", True, sin_na, "Cuerpo, acople y tapa en buen estado."),
                ("Fuga", "BOOLEAN", "Toma", True, sin_na, "Sí = la toma presenta fuga."),
                ("Señalización", "BOOLEAN", "Toma", True, sin_na, "Identificación del gas visible."),
                ("Presión de la toma", "METER", "Toma", False, medidor, "Lectura en PSI."),
                ("Observaciones", "TEXTAREA", "Toma", False, [], ""),
            ],
            grupos=["Toma"],
        )
        self.tpl_alarma, self.ver_alarma = self._publicar(
            "Revisión de alarma de presión",
            "Prueba funcional de la alarma de presión de área.",
            [
                ("Alarma sonora funciona", "BOOLEAN", "", True, [], ""),
                ("Indicador luminoso funciona", "BOOLEAN", "", True, [], ""),
                ("Presión de la red", "METER", "", True, medidor, "Lectura en PSI."),
                ("Umbral de alarma baja verificado (PSI)", "NUMBER", "", False, {"min": 45, "max": 55}, ""),
                ("Observaciones", "TEXTAREA", "", False, [], ""),
            ],
        )
        self.tpl_correctivo, self.ver_correctivo = self._publicar(
            "Reporte de intervención correctiva",
            "Diagnóstico y acción de un correctivo.",
            [
                ("Diagnóstico", "TEXTAREA", "", True, [], ""),
                ("Acción realizada", "TEXTAREA", "", True, [], ""),
                ("Repuestos usados", "TEXT", "", False, [], ""),
                ("Equipo quedó operativo", "BOOLEAN", "", True, [], ""),
            ],
        )

    # ── protocolos ───────────────────────────────────────────────────────────

    def _protocolos(self):
        from apps.maintenance.models import MaintenancePlan, PlanTask

        self.plan_tomas = MaintenancePlan.objects.create(
            name="Mant. salidas de gases",
            description="Mantenimiento semestral de las tomas de oxígeno, aire y vacío.",
            classification_1="Gases medicinales",
        )
        self.pt_tomas = PlanTask.objects.create(
            plan=self.plan_tomas, name="Mantenimiento de salidas de gases",
            task_type="PREVENTIVE", checklist_template=self.tpl_tomas,
            block_counts={"Toma": 5}, trigger=PlanTask.Trigger.DATE,
            frequency_value=6, frequency_unit="MONTHS", estimated_duration=timedelta(hours=2),
        )
        self.plan_alarma = MaintenancePlan.objects.create(
            name="Alarma de presión",
            description="Revisión semestral y atención de presión baja.",
            classification_1="Gases medicinales", priority=MaintenancePlan.Priority.HIGH,
        )
        self.pt_alarma = PlanTask.objects.create(
            plan=self.plan_alarma, name="Revisión de alarma de presión",
            task_type="PREVENTIVE", checklist_template=self.tpl_alarma,
            trigger=PlanTask.Trigger.DATE, frequency_value=6, frequency_unit="MONTHS",
            estimated_duration=timedelta(hours=1), sort_order=0,
        )
        self.pt_presion = PlanTask.objects.create(
            plan=self.plan_alarma, name="Presión baja en la red (< 50 PSI)",
            task_type="CORRECTIVE", priority="HIGH", checklist_template=self.tpl_alarma,
            trigger=PlanTask.Trigger.WHEN, meter_unit=self.psi,
            meter_comparator="LT", meter_threshold=Decimal(50), sort_order=1,
        )

    def _asignar(self, codigo, plan, fecha):
        """Asigna el protocolo al equipo; su primera tarea cae en `fecha`."""
        from apps.maintenance import services
        from apps.maintenance.models import PlanTask

        tareas_fecha = PlanTask.objects.filter(plan=plan, trigger=PlanTask.Trigger.DATE)
        tareas_fecha.update(start_date=fecha)
        try:
            services.set_asset_plan(self.a[codigo], plan, created_by=self.u["admin"])
        finally:
            tareas_fecha.update(start_date=None)

    # ── historia: OT finalizadas ─────────────────────────────────────────────

    def _historia(self):
        T, A = "tomas", "alarma"
        # dias atras, hospital, nodo, equipos, protocolo (o None = correctivo manual), ctx
        historia = [
            (185, "N", "P1", ["N-URG-O2-01", "N-URG-O2-02"], T, {}),
            (100, "N", "P3", ["N-HOS-O2-01"], T, {"fuga": 3}),
            (75, "S", "P3", ["S-HOS-VAC-01"], T, {}),
            (60, "N", "P1", ["N-URG-ALM-01"], A, {}),
            (40, "S", "SOT", ["S-SOT-BMB-01"], None, {
                "titulo": "Bomba de vacío: ruido anormal y vibración",
                "diag": "Rodamiento del motor con desgaste; vibración por encima de lo normal.",
                "accion": "Se cambió el rodamiento lado acople y se alineó la bomba.",
                "repuestos": "Rodamiento 6205-2RS", "operativo": True,
            }),
            (22, "N", "P1", ["N-URG-CV-01"], None, {
                "titulo": "Caja de válvulas Urgencias: manómetro dañado",
                "diag": "Manómetro de la línea de oxígeno sin lectura.",
                "accion": "Se reemplazó el manómetro y se verificó la presión de línea.",
                "repuestos": "Manómetro 0-100 PSI", "operativo": True,
            }),
            (9, "S", "P3", ["S-HOS-CV-01"], None, {
                "titulo": "Caja de válvulas Hospitalización: válvula de corte dura",
                "diag": "La válvula de corte del vacío opera con dificultad.",
                "accion": "Se lubricó y se verificó el cierre. Queda en observación.",
                "repuestos": "", "operativo": True,
                "hallazgo": {
                    "asset": "S-HOS-VAC-01", "severity": "MEDIUM", "fuera": False,
                    "texto": "La toma de vacío de la habitación 305 no tiene la placa de identificación; "
                          "conviene reponerla antes de la próxima auditoría.",
                },
            }),
            (3, "N", "SOT", ["N-SOT-CMP-01"], None, {
                "titulo": "Compresor de aire medicinal: disparo por alta temperatura",
                "diag": "El compresor se detiene por alta temperatura; la válvula termostática no abre.",
                "accion": "Se aisló el compresor. Se requiere cambio de la válvula termostática y del filtro de aceite.",
                "repuestos": "", "operativo": False,
                "hallazgo": {
                    "asset": "N-SOT-CMP-01", "severity": "CRITICAL", "fuera": True,
                    "texto": "Fuga de aceite en el cabezal y sobretemperatura: el compresor queda fuera de "
                          "servicio hasta cambiar la válvula termostática. La central opera con el respaldo.",
                },
            }),
        ]
        for dias, h, nodo, equipos, plan, ctx in historia:
            self._ot_historica(dias, h, nodo, equipos, plan, ctx)

        # Horas de operacion de compresor y bomba (contador): una lectura al mes.
        from apps.assets.meters import meter_for, record_manual

        for codigo, base in (("N-SOT-CMP-01", 4210), ("S-SOT-BMB-01", 2100)):
            medidor = meter_for(self.a[codigo], self.horas)
            for meses in range(5, 0, -1):
                record_manual(
                    medidor, Decimal(base + (5 - meses) * 180 + self.rnd.randint(0, 20)),
                    read_at=self._en(30 * meses - 3, 8), user=self.u["tec"], note="Lectura del horómetro",
                )

    def _ot_historica(self, dias, h, nodo, equipos, plan, ctx):
        from apps.maintenance import services
        from apps.maintenance.models import Task
        from apps.work_orders.models import WorkOrder
        from apps.work_orders.transitions import apply_transition

        dia = self._fecha(dias)
        location = self.n[(h, nodo)]
        if plan is not None:
            protocolo = self.plan_tomas if plan == "tomas" else self.plan_alarma
            self._fijar(self._en(dias + 2, 9))
            for codigo in equipos:
                self._asignar(codigo, protocolo, dia)
            self._fijar(self._en(dias, 7, 30))
            tareas = list(Task.objects.filter(
                asset__code__in=equipos, status=Task.Status.PENDING,
                plan_task__plan=protocolo, plan_task__trigger="DATE",
            ).select_related("asset"))
            ot, _ = services.create_work_order_for_tasks(
                tareas, self.u["sup"], assigned_to=self.u["tec"], scheduled_date=dia,
                location=location,
            )
        else:
            self._fijar(self._en(dias, 7, 30))
            ot = services.create_manual_work_order(
                [(self.a[c], self.ver_correctivo) for c in equipos], self.u["sup"],
                location=location, task_type="CORRECTIVE", title=ctx["titulo"],
                description=ctx["diag"], status=WorkOrder.Status.PENDING,
                priority=WorkOrder.Priority.HIGH, scheduled_date=dia, assigned_to=self.u["tec"],
            )

        # En campo
        self._fijar(self._en(dias, 8, 0))
        apply_transition(ot, WorkOrder.Status.IN_PROGRESS, self.u["tec"])
        tareas_ot = list(ot.tasks.order_by("sort_order").select_related("asset"))
        self._foto(ot, tareas_ot[0], "BEFORE", self._en(dias, 8, 10), "Antes del trabajo")
        n = 0
        for tarea in tareas_ot:
            n = self._responder(tarea, dias, n, ctx)
        self._foto(ot, tareas_ot[-1], "AFTER", self._en(dias, 10, 40), "Después del trabajo")
        self._firmas(ot, dias)
        if "hallazgo" in ctx:
            self._hallazgo(ot, dias, ctx["hallazgo"])

        self._fijar(self._en(dias, 11, 0))
        apply_transition(ot, WorkOrder.Status.IN_REVIEW, self.u["tec"])
        self._firma_guardada_de(self.u["sup"])
        self._fijar(self._en(dias, 16, 0))
        apply_transition(ot, WorkOrder.Status.COMPLETED, self.u["sup"], comment="Revisada y aprobada.")

        # El compresor con hallazgo critico queda fuera de servicio.
        if "hallazgo" in ctx and ctx["hallazgo"]["fuera"]:
            from apps.assets.models import Asset

            activo = self.a[ctx["hallazgo"]["asset"]]
            antes = activo.status
            activo.status = Asset.Status.OUT_OF_SERVICE
            activo.save(update_fields=["status", "updated_at"])
            services.asset_status_changed(activo, antes, created_by=self.u["sup"])

    # ── checklist respondido ─────────────────────────────────────────────────

    def _responder(self, tarea, dias, n, ctx):
        from apps.assets.meters import record_from_checklist
        from apps.checklists.models import ChecklistFieldResponse

        respuesta = tarea.checklist_response
        if respuesta.started_at is None:
            respuesta.started_at = self._en(dias, 8, 15) + timedelta(seconds=40 * n)
            respuesta.save(update_fields=["started_at"])
        for campo, rep in respuesta.slots():
            valor, nota = self._valor(campo, rep, tarea, ctx)
            if valor == "" and not nota:
                continue
            n += 1
            fr = ChecklistFieldResponse.objects.create(
                response=respuesta, field=campo, repetition=rep, value=valor, notes=nota,
                answered_at=self._en(dias, 8, 15) + timedelta(seconds=40 * n),
                geo_address=("Cra 15 # 100-12, Bogotá" if campo.field_type == "GPS" and tarea.asset.hospital.code == CODIGO_NORTE
                             else ("Cl 10 Sur # 50-30, Medellín" if campo.field_type == "GPS" else "")),
            )
            if campo.field_type == "METER":
                record_from_checklist(fr, self.u["tec"])
        respuesta.completed_at = self._en(dias, 10, 30)
        respuesta.completed_by = self.u["tec"]
        respuesta.save()
        return n

    def _valor(self, campo, rep, tarea, ctx):
        """(valor, nota) de una respuesta realista para ese campo."""
        etiqueta, tipo = campo.label, campo.field_type
        hosp = tarea.asset.hospital
        if tipo == "GPS":
            lat, lon = (4.6780, -74.0480) if hosp.code == CODIGO_NORTE else (6.2000, -75.5700)
            return f"{lat + self.rnd.uniform(-0.0002, 0.0002):.6f},{lon + self.rnd.uniform(-0.0002, 0.0002):.6f}", ""
        if etiqueta == "Estado general":
            return "true", ""
        if etiqueta == "Fuga":
            if ctx.get("fuga") == rep:
                return "true", "Fuga leve en el acople; se reapretó y se verificó con solución jabonosa."
            return "false", ""
        if etiqueta == "Señalización":
            return ("na" if rep == 5 else "true"), ""
        if etiqueta == "Presión de la toma":
            return f"{self.rnd.uniform(50.5, 56.0):.1f}", ""
        if etiqueta == "Observaciones":
            return "", ""
        if etiqueta in ("Alarma sonora funciona", "Indicador luminoso funciona"):
            return "true", ""
        if etiqueta == "Presión de la red":
            return f"{self.rnd.uniform(54.0, 60.0):.1f}", ""
        if etiqueta.startswith("Umbral de alarma"):
            return "50", ""
        if etiqueta == "Diagnóstico":
            return ctx.get("diag", ""), ""
        if etiqueta == "Acción realizada":
            return ctx.get("accion", ""), ""
        if etiqueta == "Repuestos usados":
            return ctx.get("repuestos", ""), ""
        if etiqueta == "Equipo quedó operativo":
            return ("true" if ctx.get("operativo", True) else "false"), ""
        return "", ""

    # ── evidencia ────────────────────────────────────────────────────────────

    def _guardar(self, nombre, contenido):
        return default_storage.save(f"{FOTO_URL}/{nombre}", ContentFile(contenido))

    def _imagen(self, texto, color):
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (800, 600), color)
        dibujo = ImageDraw.Draw(img)
        for y in range(0, 600, 40):
            dibujo.line([(0, y), (800, y + 80)], fill=tuple(min(255, c + 25) for c in color), width=6)
        dibujo.rectangle([40, 230, 760, 370], fill=(255, 255, 255))
        dibujo.text((60, 285), texto, fill=(20, 40, 70))
        salida = io.BytesIO()
        img.save(salida, "JPEG", quality=80)
        return salida.getvalue()

    def _foto(self, ot, tarea, etapa, cuando, leyenda, hallazgo=None):
        from apps.evidence.models import Photo

        etiqueta = {"BEFORE": "ANTES", "AFTER": "DESPUÉS"}.get(etapa, "HALLAZGO")
        contenido = self._imagen(
            f"{etiqueta} - {tarea.asset.code}",
            (60, 110, 160) if etapa == "BEFORE" else ((60, 140, 100) if etapa == "AFTER" else (170, 90, 60)),
        )
        clave = self._guardar(f"{ot.wo_code}/{etapa.lower() or 'hallazgo'}-{tarea.asset.code}.jpg", contenido)
        hosp = tarea.asset.hospital
        return Photo.objects.create(
            work_order=ot, task=tarea, finding=hallazgo, file_url=clave,
            latitude=hosp.latitude, longitude=hosp.longitude, taken_at=cuando,
            caption=leyenda, stage=etapa if etapa in ("BEFORE", "AFTER") else "",
            file_hash=hashlib.sha256(contenido).hexdigest(), uploaded_by=self.u["tec"],
        )

    def _firmas(self, ot, dias):
        from PIL import Image, ImageDraw

        from apps.evidence.models import Signature

        def trazo(semilla):
            r = random.Random(semilla)
            img = Image.new("RGB", (500, 200), (255, 255, 255))
            d = ImageDraw.Draw(img)
            puntos = [(20 + i * 22, 100 + r.randint(-60, 60)) for i in range(21)]
            d.line(puntos, fill=(20, 30, 90), width=3)
            salida = io.BytesIO()
            img.save(salida, "PNG")
            return salida.getvalue()

        quien = {
            "TECHNICIAN": ("Técnico Demo", "Técnico de mantenimiento", self._en(dias, 10, 45)),
            "CLIENT": ("Laura Ríos", "Ingeniera biomédica", self._en(dias, 10, 50)),
        }
        for tipo, (nombre, rol, cuando) in quien.items():
            contenido = trazo(f"{ot.wo_number}{tipo}")
            clave = self._guardar(f"{ot.wo_code}/firma-{tipo.lower()}.png", contenido)
            Signature.objects.create(
                work_order=ot, signature_type=tipo, file_url=clave, signer_name=nombre,
                signer_role=rol, file_hash=hashlib.sha256(contenido).hexdigest(),
                signed_at=cuando, latitude=ot.hospital.latitude, longitude=ot.hospital.longitude,
            )

    def _firma_guardada_de(self, user):
        """Aprobar firma con la firma guardada de quien aprueba: el supervisor de la demo tiene una."""
        from PIL import Image, ImageDraw

        from apps.evidence.models import UserSignature

        if UserSignature.objects.filter(user=user).exists():
            return
        img = Image.new("RGB", (500, 200), (255, 255, 255))
        ImageDraw.Draw(img).line([(20 + i * 22, 100 + (-1) ** i * 35) for i in range(21)], fill=(20, 30, 90), width=3)
        salida = io.BytesIO()
        img.save(salida, "PNG")
        contenido = salida.getvalue()
        clave = self._guardar(f"firmas-guardadas/{user.id}.png", contenido)
        UserSignature.objects.create(user=user, file_url=clave, file_hash=hashlib.sha256(contenido).hexdigest())

    def _hallazgo(self, ot, dias, datos):
        from apps.work_orders.models import Finding

        hallazgo = Finding.objects.create(
            work_order=ot, asset=self.a[datos["asset"]], description=datos["texto"],
            severity=datos["severity"], out_of_service=datos["fuera"], resolved_on_site=False,
            reported_by=self.u["tec"], reported_at=self._en(dias, 10, 20),
            status=Finding.Status.PENDING,
        )
        tarea = ot.tasks.filter(asset=hallazgo.asset).first() or ot.tasks.first()
        if datos["severity"] == "CRITICAL":
            self._foto(ot, tarea, "", self._en(dias, 10, 22), "Evidencia del hallazgo", hallazgo=hallazgo)
        return hallazgo

    # ── calendario vivo ──────────────────────────────────────────────────────

    def _calendario(self):
        """Tareas pendientes: vencidas, en los proximos 30 dias y mas adelante."""
        def desde_hoy(n):
            return self.hoy + timedelta(days=n)

        self._asignar("N-URG-AIR-01", self.plan_tomas, desde_hoy(-12))      # vencida
        self._asignar("S-URG-ALM-01", self.plan_alarma, desde_hoy(-6))      # vencida
        self._asignar("S-URG-O2-01", self.plan_tomas, desde_hoy(9))         # proxima
        self._asignar("N-HOS-ALM-01", self.plan_alarma, desde_hoy(22))      # proxima
        # Las ya hechas conservan su siguiente fecha (6 meses despues del cierre)
        # y las que se hicieron en historia no se vuelven a asignar.

    def _lecturas(self):
        """Presion baja en una alarma: abre sola la tarea del activador por medidor."""
        from apps.assets.meters import meter_for, record_manual

        medidor = meter_for(self.a["S-URG-ALM-01"], self.psi)
        for dias, valor in ((6, "58.5"), (3, "56.0"), (1, "52.5")):
            record_manual(medidor, Decimal(valor), read_at=self._en(dias, 8), user=self.u["tec"])
        self._fijar(self.ahora)
        record_manual(medidor, Decimal("44.0"), read_at=self.ahora, user=self.u["tec"],
                      note="Presión por debajo del umbral")

    def _contratos(self):
        from apps.assets.models import Asset, Contract, ContractAsset

        self._fijar(self.ahora)
        Contract.objects.create(
            kind=Contract.Kind.MAINTENANCE, name="Contrato de mantenimiento 2026 - Clínica Demo Norte",
            description="Mantenimiento preventivo y correctivo de la red de gases medicinales.",
            hospital=self.h["N"], start_date=self.hoy - timedelta(days=340),
            end_date=self.hoy + timedelta(days=25), created_by=self.u["admin"],
        )
        garantia = Contract.objects.create(
            kind=Contract.Kind.WARRANTY, name="Garantía compresor y manifold - Clínica Demo Norte",
            description="Garantía del fabricante por 24 meses.",
            hospital=self.h["N"], start_date=self.hoy - timedelta(days=200),
            end_date=self.hoy + timedelta(days=530), created_by=self.u["admin"],
        )
        for codigo in ("N-SOT-CMP-01", "N-SOT-MAN-01"):
            ContractAsset.objects.create(contract=garantia, asset=self.a[codigo])
            Asset.objects.filter(pk=self.a[codigo].pk).update(warranty_expiry=garantia.end_date)

    # ── la OT de la demo ─────────────────────────────────────────────────────

    def _ot_en_vivo(self):
        from apps.maintenance import services
        from apps.maintenance.models import Task

        tareas = list(Task.objects.filter(
            asset__code__in=["N-URG-O2-01", "N-URG-O2-02"], status=Task.Status.PENDING,
            plan_task=self.pt_tomas,
        ).select_related("asset"))
        self.ot_vivo, _ = services.create_work_order_for_tasks(
            tareas, self.u["sup"], assigned_to=self.u["tec"], scheduled_date=self.hoy,
            location=self.n[("N", "P1")],
            title="Mantenimiento de tomas - Urgencias (Piso 1)",
            description="Preventivo semestral de las tomas de oxígeno de Urgencias.",
        )

    # ── resumen ──────────────────────────────────────────────────────────────

    def _resumen(self, nombre):
        from apps.assets.models import Asset, Contract, Hospital, Meter, MeterReading
        from apps.checklists.models import ChecklistTemplate
        from apps.evidence.models import Photo, Signature
        from apps.maintenance.models import MaintenancePlan, Task
        from apps.reports.models import GeneratedReport
        from apps.users.models import User
        from apps.work_orders.models import Finding, WorkOrder

        fin = WorkOrder.objects.filter(status="COMPLETED")
        actas = GeneratedReport.objects.filter(work_order__in=fin).values("work_order").distinct().count()
        hoy = self.hoy
        abiertas = Task.objects.filter(status__in=Task.OPEN_STATUSES)
        lineas = [
            f"Base de demostración lista: {nombre}",
            f"  Hospitales: {Hospital.objects.count()}  Equipos: {Asset.objects.count()}",
            (f"  Usuarios: {User.objects.count()}  Checklists: {ChecklistTemplate.objects.count()}  "
            f"Protocolos: {MaintenancePlan.objects.count()}"),
            (f"  OT finalizadas: {fin.count()}  (con acta: {actas})  OT pendientes: "
            f"{WorkOrder.objects.filter(status='PENDING').count()}"),
            (f"  Tareas pendientes sin OT: {Task.objects.filter(status='PENDING').count()}  "
            f"(vencidas: {Task.objects.filter(status='PENDING', scheduled_date__lt=hoy).count()}, "
            f"próximos 30 días: {Task.objects.filter(status='PENDING', scheduled_date__gte=hoy, scheduled_date__lte=hoy + timedelta(days=30)).count()}, "
            f"más adelante: {Task.objects.filter(status='PENDING', scheduled_date__gt=hoy + timedelta(days=30)).count()})  "
            f"abiertas en total: {abiertas.count()}"),
            (f"  Fotos: {Photo.objects.count()}  Firmas: {Signature.objects.count()}  "
            f"Medidores: {Meter.objects.count()}  Lecturas: {MeterReading.objects.count()}"),
            (f"  Hallazgos pendientes: {Finding.objects.filter(status='PENDING').count()}  "
            f"Contratos/garantías: {Contract.objects.count()}"),
        ]
        if fin.count() != actas and not self.sin_actas:
            lineas.append(
                f"  AVISO: {fin.count() - actas} OT finalizadas quedaron sin acta "
                "(¿falta WeasyPrint o sus librerías?). El resto de la demo funciona igual."
            )
        for linea in lineas:
            self.stdout.write(linea)
        self.stdout.write(self.style.SUCCESS(
            f"Listo. OT de la demo: {self.ot_vivo.wo_code} (pendiente, asignada a {USUARIOS['tec'][0]})."
        ))
