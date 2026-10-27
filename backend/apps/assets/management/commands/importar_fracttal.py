"""Importa activos desde las exportaciones a Excel de Fracttal.

Sin --aplicar solo imprime el resumen (no escribe nada).
"""

import json

from django.core.management.base import BaseCommand, CommandError

from apps.assets import importacion_fracttal as imp
from apps.users.models import User


class Command(BaseCommand):
    help = "Importa ubicaciones y equipos de Fracttal desde Excel. Sin --aplicar, solo muestra el resumen."

    def add_arguments(self, parser):
        parser.add_argument("--ubicaciones", help="Ruta del Excel de ubicaciones")
        parser.add_argument("--equipos", help="Ruta del Excel de equipos")
        parser.add_argument("--aplicar", action="store_true", help="Escribe en la base de datos")
        parser.add_argument("--usuario", help="Email del usuario que importa (por defecto, el primer ADMIN)")
        parser.add_argument("--json", action="store_true", help="Imprime el resumen como JSON")

    def handle(self, *args, **opts):
        if not opts["ubicaciones"] and not opts["equipos"]:
            raise CommandError("Indica --ubicaciones y/o --equipos.")
        try:
            ubicaciones = imp.leer_ubicaciones(opts["ubicaciones"]) if opts["ubicaciones"] else []
            equipos = imp.leer_equipos(opts["equipos"]) if opts["equipos"] else []
        except (imp.ImportacionError, OSError) as exc:
            raise CommandError(str(exc))
        plan = imp.planificar(ubicaciones, equipos)
        resumen = plan.resumen()

        if opts["aplicar"]:
            if plan.errores:
                self._imprimir(resumen, opts["json"])
                raise CommandError("El plan tiene errores; no se aplicó nada.")
            if opts["usuario"]:
                user = User.objects.filter(email__iexact=opts["usuario"]).first()
            else:
                user = User.objects.filter(role=User.Role.ADMIN, is_active=True).order_by("created_at").first()
            if user is None:
                raise CommandError("No encontré el usuario que importa (usa --usuario email).")
            try:
                conteos = imp.aplicar(plan, user)
            except imp.ImportacionError as exc:
                raise CommandError(str(exc))
            resumen = plan.resumen(aplicado=True)
            archivos = {k: opts[k] for k in ("ubicaciones", "equipos") if opts[k]}
            imp.auditar(user, archivos, resumen, conteos)
            resumen["applied_counts"] = conteos
        self._imprimir(resumen, opts["json"])

    def _imprimir(self, r, como_json):
        if como_json:
            self.stdout.write(json.dumps(r, ensure_ascii=False, indent=2, default=str))
            return
        w = self.stdout.write
        w("Hospitales a crear: %s" % (", ".join(r["hospitals"]["create"]) or "ninguno"))
        w("Hospitales existentes: %s" % (", ".join(r["hospitals"]["existing"]) or "ninguno"))
        w("Ubicaciones: %(create)d a crear, %(update)d a actualizar" % r["locations"])
        w("Equipos: %(create)d a crear, %(update)d a actualizar" % r["assets"])
        w("Protocolos a crear (vacios): %s" % (", ".join(r["plans"]["create"]) or "ninguno"))
        w("Protocolos existentes: %s" % (", ".join(r["plans"]["existing"]) or "ninguno"))
        w("Errores: %d   Avisos: %d   Aplicado: %s" % (r["errors_count"], r["warnings_count"], "SI" if r["applied"] else "no"))
        if "applied_counts" in r:
            w("Aplicado: %s" % r["applied_counts"])
        for f in r["rows"]:
            if f["errors"] or f["warnings"]:
                w("  [%s fila %d] %s (%s)" % (f["file"], f["row"], f["name"], f["action"]))
                for m in f["errors"]:
                    w("      ERROR: %s" % m)
                for m in f["warnings"]:
                    w("      aviso: %s" % m)
