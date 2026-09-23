import json
import logging
import re
import uuid

from django.utils.deprecation import MiddlewareMixin

from .services import AUTH_ENTITY_TYPE

logger = logging.getLogger(__name__)

_PATH_ENTITY_MAP = [
    ('/api/evidence/photos/', 'Photo'),
    ('/api/evidence/signatures/', 'Signature'),
    ('/api/asset-nodes/', 'AssetNode'),
    ('/api/asset-custom-fields/', 'AssetCustomField'),
    ('/api/assets/', 'Asset'),
    ('/api/hospitals/', 'Hospital'),
    ('/api/work-orders/', 'WorkOrder'),
    # Estos dos prefijos estaban escritos con guion ('/api/checklist-templates/',
    # '/api/maintenance-plans/') y las rutas reales llevan barra, asi que no
    # coincidian nunca: toda la actividad de checklists y de planes PM se
    # guardaba como URL cruda y quedaba fuera del filtro de la auditoria.
    # Incluido submit-field y complete, que es el rastro de lo que el tecnico
    # verifico en cada OT.
    ('/api/checklists/templates/', 'ChecklistTemplate'),
    ('/api/checklists/responses/', 'ChecklistResponse'),
    ('/api/maintenance/plans/', 'MaintenancePlan'),
    # Modelo de tareas (fase 2): la tarea del plan, cada tarea con su fecha
    # (reprogramar y anular quedan como acciones sobre Task) y el catalogo
    # de causas.
    ('/api/maintenance/plan-tasks/', 'PlanTask'),
    ('/api/tasks/', 'Task'),
    ('/api/reschedule-causes/', 'RescheduleCause'),
    ('/api/reports/', 'GeneratedReport'),
    ('/api/report-settings/', 'ReportSettings'),
    ('/api/users/', 'User'),
    ('/api/inventory/items/', 'InventoryItem'),
    ('/api/inventory/movements/', 'StockMovement'),
    # Logout, refresh y cambio de contrasena. Sin esta entrada _entity_type_from_path
    # devolvia la ruta cruda ('/api/auth/logout/') como tipo de entidad, que no
    # coincide con ninguna opcion del filtro de la pantalla de auditoria y dejaba
    # esos eventos fuera de cualquier busqueda. Va al final: es el prefijo mas
    # generico y no debe ganarle a ninguno de los de arriba.
    ('/api/auth/', AUTH_ENTITY_TYPE),
]

# El login se audita en LoginView, que es el unico sitio donde se conoce la
# identidad: aqui la peticion todavia es anonima y todo inicio de sesion acababa
# registrado como "Sistema".
_VIEW_AUDITED_PATHS = ('/api/auth/login/',)

_UUID_RE = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I
)
_SENTINEL_UUID = uuid.UUID(int=0)


def _entity_type_from_path(path):
    for prefix, name in _PATH_ENTITY_MAP:
        if prefix in path:
            return name
    return path


def _entity_id_from_path(path):
    matches = _UUID_RE.findall(path)
    if matches:
        return uuid.UUID(matches[-1])
    return None


def _entity_id_from_body(response):
    try:
        content_type = response.get('Content-Type', '')
        if 'application/json' in content_type:
            data = json.loads(response.content)
            if isinstance(data, dict):
                for key in ('id', 'pk'):
                    val = data.get(key)
                    if val:
                        return uuid.UUID(str(val))
    except Exception:
        pass
    return None


class AuditMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        try:
            path = request.path
            if not path.startswith('/api/'):
                return response
            if request.method == 'GET':
                return response
            if path in _VIEW_AUDITED_PATHS:
                return response

            status_code = response.status_code
            # Only record write operations that resulted in a change or a failed attempt
            if 300 <= status_code < 400:
                return response

            from apps.audit.models import AuditLog

            _action_map = {
                'POST': AuditLog.Action.CREATE,
                'PUT': AuditLog.Action.UPDATE,
                'PATCH': AuditLog.Action.UPDATE,
                'DELETE': AuditLog.Action.DELETE,
            }
            action = _action_map.get(request.method)
            if not action:
                return response

            entity_type = _entity_type_from_path(path)

            entity_id = _entity_id_from_path(path)
            if entity_id is None and status_code in (200, 201):
                entity_id = _entity_id_from_body(response)
            if entity_id is None:
                entity_id = _SENTINEL_UUID

            user = (
                request.user
                if hasattr(request, 'user') and request.user.is_authenticated
                else None
            )

            changes = {'method': request.method, 'status_code': status_code}
            if status_code >= 400:
                changes['failed'] = True

            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
            ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')

            AuditLog.objects.create(
                user=user,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                changes=changes,
                ip_address=ip or None,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception as exc:
            logger.warning('AuditMiddleware: failed to create log: %s', exc)
        return response
