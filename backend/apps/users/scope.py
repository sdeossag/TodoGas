"""
Sobre que registros trabaja cada usuario (#117, decision del 2026-09-23).

Es el eje "sobre que" de Fracttal ("Limitar acceso a esta localizacion"):
un usuario puede quedar limitado a un hospital y, dentro de el, a una parte
del arbol (bloque, piso, servicio). Aplica a todos los roles menos ADMIN,
que siempre ve todo para no poder quedar fuera de su propio sistema.

Todas las vistas filtran por aqui. Asi una ruta nueva no puede olvidar el
limite de una cuenta de hospital, que fue lo que paso con las respuestas de
checklist: se filtraban para el tecnico y a un cliente le llegaban las de
todos los hospitales.
"""

from django.db.models import Exists, OuterRef, Q

from apps.users.models import User


class _SinAcceso(Exception):
    pass


def _limitado(user):
    """
    True si hay que filtrar. Un cliente sin hospital no ve nada (no "todo"):
    si una cuenta de hospital quedara mal creada, lo seguro es que no vea.
    """
    if user.role == User.Role.ADMIN:
        return False
    if user.hospital_id is None:
        if user.role == User.Role.CLI:
            raise _SinAcceso
        return False
    return True


def _filtrar(fn):
    def envoltura(qs, user, *args, **kwargs):
        try:
            return fn(qs, user, *args, **kwargs)
        except _SinAcceso:
            return qs.none()
    envoltura.__doc__ = fn.__doc__
    envoltura.__name__ = fn.__name__
    return envoltura


def _nodos(user):
    """Ids del nodo del usuario y de todo lo que cuelga de el, o None."""
    if not user.scope_node_id:
        return None
    from apps.assets.models import AssetNode

    cache = getattr(user, "_scope_node_ids", None)
    if cache is None:
        cache = AssetNode.subtree_ids(user.scope_node_id)
        user._scope_node_ids = cache
    return cache


@_filtrar
def hospitals(qs, user):
    return qs.filter(pk=user.hospital_id) if _limitado(user) else qs


@_filtrar
def asset_nodes(qs, user):
    if not _limitado(user):
        return qs
    qs = qs.filter(hospital_id=user.hospital_id)
    nodos = _nodos(user)
    return qs.filter(pk__in=nodos) if nodos is not None else qs


@_filtrar
def assets(qs, user, prefix=""):
    """`prefix` para filtrar un modelo que llega al activo por una relacion ("asset__")."""
    if not _limitado(user):
        return qs
    qs = qs.filter(**{f"{prefix}hospital_id": user.hospital_id})
    nodos = _nodos(user)
    return qs.filter(**{f"{prefix}node_id__in": nodos}) if nodos is not None else qs


@_filtrar
def work_orders(qs, user, prefix=""):
    """
    Una OT se ve si es del hospital y, con un nodo, si alguna de sus tareas es
    sobre un activo de esa parte del arbol: una visita puede cubrir varios
    pisos y el acta es una sola.
    """
    if not _limitado(user):
        return qs
    qs = qs.filter(**{f"{prefix}hospital_id": user.hospital_id})
    nodos = _nodos(user)
    if nodos is None:
        return qs
    from apps.maintenance.models import Task

    tareas = Task.objects.filter(
        work_order_id=OuterRef(f"{prefix}pk" if prefix else "pk"),
        asset__node_id__in=nodos,
    )
    return qs.filter(Exists(tareas))


@_filtrar
def contracts(qs, user):
    """
    Contratos y garantias del hospital. Con un nodo: el contrato que cubre
    todo el hospital, una rama por encima o por debajo de la suya, y la
    garantia con algun equipo de su parte del arbol. El contrato de otro
    piso no le toca.
    """
    if not _limitado(user):
        return qs
    qs = qs.filter(hospital_id=user.hospital_id)
    nodos = _nodos(user)
    if nodos is None:
        return qs
    from apps.assets.models import AssetNode, ContractAsset

    ancestros, actual = [], user.scope_node_id
    while actual:
        ancestros.append(actual)
        actual = AssetNode.objects.filter(pk=actual).values_list("parent_id", flat=True).first()
    equipos = ContractAsset.objects.filter(contract_id=OuterRef("pk"), asset__node_id__in=nodos)
    return qs.filter(
        Q(kind="MAINTENANCE", node__isnull=True)
        | Q(kind="MAINTENANCE", node_id__in=[*nodos, *ancestros])
        | Q(kind="WARRANTY") & Exists(equipos)
    )


def needs_node(context):
    """
    Un usuario limitado a un nodo no puede crear en la raiz del hospital: eso
    queda fuera de su parte del arbol.
    """
    user = getattr(context.get("request"), "user", None)
    return bool(user and user.role != User.Role.ADMIN and user.hospital_id and user.scope_node_id)


def can_see_work_order(user, work_order):
    from apps.work_orders.models import WorkOrder

    return work_orders(WorkOrder.objects.filter(pk=work_order.pk), user).exists()


_POR_TIPO = {
    "hospitals": hospitals,
    "nodes": asset_nodes,
    "assets": assets,
    "tasks": lambda qs, user: assets(qs, user, prefix="asset__"),
}


class ScopedFieldsMixin:
    """
    Limita los ids que acepta un serializer a los del alcance del usuario:
    `scoped_fields = {"task_ids": "tasks"}`. Un supervisor limitado a una
    clinica no puede armar una OT ni reprogramar tareas de otra mandando sus
    ids a mano. Se hace en get_fields (y no en __init__) para que tambien
    funcione en serializers anidados, que reciben el contexto al enlazarse.
    El serializer necesita `request` en el contexto; sin el, no acepta nada.
    """

    scoped_fields = {}

    def get_fields(self):
        campos = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        for nombre, tipo in self.scoped_fields.items():
            campo = campos.get(nombre)
            if campo is None:
                continue
            relacion = getattr(campo, "child_relation", campo)
            if user is None or not user.is_authenticated:
                relacion.queryset = relacion.queryset.none()
            else:
                relacion.queryset = _POR_TIPO[tipo](relacion.queryset, user)
        return campos
