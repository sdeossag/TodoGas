"""
Permisos extra por usuario (primer audio del cliente, 10:18: "que un tecnico
pueda tener mas permisos").

El rol sigue siendo la base. El administrador marca casillas de este catalogo
por usuario y eso SOLO suma: nunca quita lo que el rol ya trae, y tampoco
amplia el alcance por hospital (apps.users.scope sigue filtrando igual: un
tecnico limitado a una clinica con "revisar OT" solo revisa las de su alcance).

El catalogo es fijo en el codigo y en la base solo se guarda el codigo
(PermisoExtra), asi que sumar una capacidad no pide migracion. Quedan fuera,
y siguen siendo solo del administrador: usuarios, formato del acta, tipos de
tarea, hospitales, campos personalizados y auditoria.

Una cuenta de hospital (CLI) nunca recibe permisos: ve el portal del cliente y
nada mas, y `permisos_efectivos` la ignora aunque alguien insertara una fila.
"""

from dataclasses import dataclass

from django.db import transaction

from .models import PermisoExtra, User

ADMIN, SUP, TEC, CLI = User.Role.ADMIN, User.Role.SUP, User.Role.TEC, User.Role.CLI


@dataclass(frozen=True)
class Permiso:
    codigo: str
    nombre: str
    descripcion: str
    area: str
    # Roles que ya lo traen. Para SUP es lo que el servidor le deja hacer hoy
    # (no se le quita nada), aunque la pantalla antes no se lo mostrara.
    roles: tuple


CATALOGO = (
    # ── Ordenes de trabajo ──────────────────────────────────────────────────
    Permiso("ot.crear_manual", "Crear órdenes de trabajo",
            "Crear una OT a mano, eligiendo los equipos y el técnico.",
            "Órdenes de trabajo", (ADMIN,)),
    Permiso("ot.crear_desde_pendientes", "Crear órdenes desde pendientes",
            "Agrupar tareas pendientes en una OT, o sumarlas y sacarlas de una OT que no empezó.",
            "Órdenes de trabajo", (ADMIN, SUP)),
    Permiso("ot.asignar", "Asignar y reasignar",
            "Elegir quién ejecuta una OT y cambiarlo mientras esté abierta.",
            "Órdenes de trabajo", (ADMIN, SUP)),
    Permiso("ot.revisar", "Revisar y aprobar",
            "Revisar una OT enviada, aprobarla, devolverla al técnico y corregir sus respuestas, fotos y fechas.",
            "Órdenes de trabajo", (ADMIN, SUP)),
    Permiso("ot.cancelar", "Cancelar órdenes",
            "Cancelar una OT que no se hizo, dejando el motivo.",
            "Órdenes de trabajo", (ADMIN,)),
    # ── Planificacion ───────────────────────────────────────────────────────
    Permiso("tareas.planificar", "Planificar tareas pendientes",
            "Ver las tareas por hacer, cambiarles la fecha o anularlas, y cambiar el checklist de una tarea.",
            "Planificación", (ADMIN, SUP)),
    Permiso("protocolos.gestionar", "Gestionar protocolos",
            "Crear y editar los protocolos de mantenimiento y asignarlos a los equipos.",
            "Planificación", (ADMIN,)),
    Permiso("checklists.gestionar", "Gestionar checklists",
            "Crear plantillas de checklist, publicar versiones y elegir la vigente.",
            "Planificación", (ADMIN, SUP)),
    # ── Equipos y contratos ─────────────────────────────────────────────────
    Permiso("activos.gestionar", "Gestionar equipos y ubicaciones",
            "Crear y editar equipos, darlos de baja, armar el árbol de ubicaciones y registrar lecturas de medidores.",
            "Equipos y contratos", (ADMIN, SUP)),
    Permiso("contratos.gestionar", "Gestionar contratos y garantías",
            "Cargar y corregir contratos de mantenimiento y garantías, con su documento.",
            "Equipos y contratos", (ADMIN,)),
    Permiso("hallazgos.decidir", "Decidir hallazgos",
            "Convertir un hallazgo en una tarea o descartarlo desde la bandeja.",
            "Equipos y contratos", (ADMIN, SUP)),
    # ── Inventario ──────────────────────────────────────────────────────────
    Permiso("inventario.articulos", "Gestionar artículos de inventario",
            "Crear y editar los artículos del inventario.",
            "Inventario", (ADMIN,)),
    Permiso("inventario.movimientos", "Registrar movimientos de inventario",
            "Registrar entradas, salidas y ajustes de stock, con o sin OT.",
            "Inventario", (ADMIN, SUP)),
    # ── Reportes ────────────────────────────────────────────────────────────
    Permiso("reportes.ver", "Ver reportes y actas",
            "Ver el tablero y las actas de todos los hospitales de su alcance.",
            "Reportes", (ADMIN, SUP)),
)

_POR_CODIGO = {p.codigo: p for p in CATALOGO}
CODIGOS = frozenset(_POR_CODIGO)

# Con cualquiera de estos, un tecnico deja de ver solo lo asignado y ve las OT
# de su alcance (como un supervisor): sin eso no podria revisar, asignar ni
# planificar lo que no ejecuta el.
_DE_GESTION_DE_OT = (
    "ot.crear_manual", "ot.crear_desde_pendientes", "ot.asignar", "ot.revisar",
    "ot.cancelar", "tareas.planificar", "hallazgos.decidir",
)


def permisos_del_rol(rol):
    """Codigos que trae el rol, sin extras."""
    return {p.codigo for p in CATALOGO if rol in p.roles}


def _extras(user):
    if user.role == CLI:
        return set()  # una cuenta de hospital nunca recibe permisos
    # .all() y no values_list: la lista de usuarios los trae con prefetch.
    return {p.codigo for p in user.permisos_extra.all()} & CODIGOS


def permisos_efectivos(user):
    """
    Rol + extras. Se calcula una vez por objeto usuario: una peticion revisa
    varios permisos y cada uno iria a la base. `establecer` limpia el cache.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    cache = getattr(user, "_permisos_efectivos", None)
    if cache is None:
        cache = permisos_del_rol(user.role) | _extras(user)
        user._permisos_efectivos = cache
    return cache


def puede(user, codigo):
    return codigo in permisos_efectivos(user)


def puede_alguno(user, *codigos):
    return bool(permisos_efectivos(user) & set(codigos))


def es_gestor(user):
    """
    Lee las pantallas de gestion (listas de hospitales, protocolos, ubicaciones):
    admin, supervisor, o quien tenga algun permiso extra. Es de lectura; lo que
    se puede cambiar lo decide cada permiso.
    """
    if not user or not getattr(user, "is_authenticated", False) or user.role == CLI:
        return False
    return user.role in (ADMIN, SUP) or bool(permisos_efectivos(user))


def ve_ots_en_alcance(user):
    """
    Ve las OT de su alcance y no solo las que tiene asignadas. Admin y
    supervisor siempre; un tecnico, si se le dio algun permiso sobre OT.
    """
    if not user or not getattr(user, "is_authenticated", False) or user.role == CLI:
        return False
    return user.role in (ADMIN, SUP) or puede_alguno(user, *_DE_GESTION_DE_OT)


def edita_ot_completa(user):
    """Edita titulo, fecha, prioridad... de una OT ajena (el tecnico solo la suya)."""
    return user.role in (ADMIN, SUP) or puede_alguno(user, "ot.asignar", "ot.crear_manual")


def extras_de(user):
    """Codigos extra guardados, ordenados (lo que el administrador marco)."""
    return sorted(_extras(user))


def catalogo_para_api():
    return [
        {"codigo": p.codigo, "nombre": p.nombre, "descripcion": p.descripcion,
         "area": p.area, "roles": list(p.roles)}
        for p in CATALOGO
    ]


def normalizar(rol, codigos):
    """
    Valida lo que manda el administrador y devuelve los codigos que de verdad
    se guardan: sin repetidos y sin lo que el rol ya trae. Lanza ValueError con
    el motivo, listo para mostrarse.
    """
    codigos = list(dict.fromkeys(codigos or []))
    desconocidos = [c for c in codigos if c not in CODIGOS]
    if desconocidos:
        raise ValueError(f"Permiso desconocido: {', '.join(map(str, desconocidos))}.")
    if rol == CLI:
        if codigos:
            raise ValueError("Una cuenta de hospital no puede tener permisos adicionales.")
        return set()
    return set(codigos) - permisos_del_rol(rol)


@transaction.atomic
def establecer(user, codigos, por, request=None):
    """
    Deja los permisos extra de `user` exactamente en `codigos`. Devuelve
    (otorgados, quitados). Si cambia algo, queda en la auditoria con quien
    lo hizo; si no cambia nada, no se escribe nada.
    """
    deseados = normalizar(user.role, codigos)
    actuales = set(PermisoExtra.objects.filter(user=user).values_list("codigo", flat=True))
    otorgados = sorted(deseados - actuales)
    quitados = sorted(actuales - deseados)
    for c in otorgados:
        PermisoExtra.objects.create(user=user, codigo=c, otorgado_por=por)
    if quitados:
        PermisoExtra.objects.filter(user=user, codigo__in=quitados).delete()
    # Lo calculado antes (y lo precargado por la lista) ya no vale.
    user.__dict__.pop("_permisos_efectivos", None)
    getattr(user, "_prefetched_objects_cache", {}).pop("permisos_extra", None)
    if otorgados or quitados:
        from apps.audit.ip import client_ip
        from apps.audit.models import AuditLog

        AuditLog.objects.create(
            user=por,
            action=AuditLog.Action.UPDATE,
            entity_type="User",
            entity_id=user.id,
            changes={"permisos_extra": {"otorgados": otorgados, "quitados": quitados}},
            ip_address=client_ip(request) if request is not None else None,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500] if request is not None else "",
        )
    return otorgados, quitados


def otorgar(user, codigo, por, request=None):
    """Suma un permiso a los que ya tiene."""
    actuales = set(PermisoExtra.objects.filter(user=user).values_list("codigo", flat=True))
    return establecer(user, actuales | {codigo}, por, request)
