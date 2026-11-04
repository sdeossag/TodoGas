"""Importa una sede completa desde el JSON del extractor de Fracttal.

    python manage.py importar_fracttal_json archivo.json            (vista previa)
    python manage.py importar_fracttal_json archivo.json --aplicar --usuario admin@x.com

Sin --aplicar solo muestra el resumen: no escribe nada.
"""

import json
import time

from django.core.management.base import BaseCommand, CommandError

from apps.assets import importacion_fracttal_json as imp
from apps.assets.importacion_fracttal import ImportacionError
from apps.users.models import User


class Command(BaseCommand):
    help = "Importa ubicaciones, activos, protocolos y el historial de OT desde el JSON del extractor de Fracttal."

    def add_arguments(self, parser):
        parser.add_argument("archivo", help="Ruta del JSON (formato fracttal-json-v1)")
        parser.add_argument("--aplicar", action="store_true", help="Escribe en la base de datos")
        parser.add_argument("--usuario", help="Email del usuario que importa (por defecto, el primer ADMIN)")
        parser.add_argument("--json", action="store_true", help="Imprime el resumen como JSON")

    def handle(self, *args, **opts):
        t0 = time.monotonic()
        try:
            datos = imp.leer(opts["archivo"])
        except (ImportacionError, OSError) as exc:
            raise CommandError(str(exc))
        t_leer = time.monotonic() - t0
        plan = imp.planificar(datos)
        t_plan = time.monotonic() - t0 - t_leer
        resumen = plan.resumen()
        tiempos = {"leer_s": round(t_leer, 2), "planificar_s": round(t_plan, 2)}

        if opts["aplicar"]:
            if plan.errores:
                self._imprimir(resumen, opts["json"], tiempos)
                raise CommandError("El plan tiene errores; no se aplicó nada.")
            if opts["usuario"]:
                user = User.objects.filter(email__iexact=opts["usuario"]).first()
            else:
                user = User.objects.filter(role=User.Role.ADMIN, is_active=True).order_by("created_at").first()
            if user is None:
                raise CommandError("No encontré el usuario que importa (usa --usuario email).")
            t1 = time.monotonic()
            try:
                conteos = imp.aplicar(plan, user)
            except ImportacionError as exc:
                raise CommandError(str(exc))
            tiempos["aplicar_s"] = round(time.monotonic() - t1, 2)
            resumen = plan.resumen(aplicado=True)
            imp.auditar(user, opts["archivo"], resumen, conteos)
            resumen["applied_counts"] = conteos
        self._imprimir(resumen, opts["json"], tiempos)

    def _imprimir(self, r, como_json, tiempos):
        if como_json:
            self.stdout.write(json.dumps({**r, "timings": tiempos}, ensure_ascii=False, indent=2, default=str))
            return
        w = self.stdout.write
        modo = "APLICADO" if r["applied"] else "VISTA PREVIA (no se escribió nada)"
        w(f"Importación de Fracttal — sede «{r['sede']}» — {modo}")
        w(f"Hospitales a crear: {', '.join(r['hospitals']['create']) or 'ninguno'}")
        w(f"Hospitales existentes: {', '.join(r['hospitals']['existing']) or 'ninguno'}")
        w("Ubicaciones: {create} a crear, {update} a actualizar".format(**r["locations"]))
        w("Activos: {create} a crear, {update} a actualizar".format(**r["assets"]))
        w("Protocolos: {create} a crear, {update} existentes".format(**r["plans"]))
        w("Tareas de protocolo: {create} a crear, {update} existentes".format(**r["plan_tasks"]))
        tipos = ", ".join(f"{k}: {v}" for k, v in sorted(r["field_types"].items()))
        w(f"Campos de checklist: {r['checklist_fields']} ({tipos})")
        trig = ", ".join(f"{k}: {v}" for k, v in r["triggers"].items()) or "ninguno"
        w(f"Activadores de tareas: {trig}")
        o = r["work_orders"]
        w(f"OT históricas: {o['create']} a crear ({o['completed']} finalizadas, {o['cancelled']} canceladas), "
          f"{o['existing']} ya importadas")
        w(f"  Tareas de OT: {r['tasks']}   Respuestas de checklist: {r['responses']}   "
          f"OT con firma: {r['signatures']}   Fotos pendientes de descargar: {r['photos_pending']}")
        w(f"Errores: {r['errors_count']}   Avisos: {r['warnings_count']}")
        for m in r["errors"]:
            w(f"  ERROR: {m}")
        for g in r["warnings"]:
            ejemplos = f" (ej.: {'; '.join(g['ejemplos'])})" if g["ejemplos"] else ""
            w(f"  aviso x{g['cantidad']}: {g['mensaje']}{ejemplos}")
        if "applied_counts" in r:
            w(f"Aplicado: {r['applied_counts']}")
        w("Tiempos: " + ", ".join(f"{k}={v}" for k, v in tiempos.items()))
