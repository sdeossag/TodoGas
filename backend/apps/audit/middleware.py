import json
import logging
import re
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

_PATH_ENTITY_MAP = [
    ('/api/evidence/photos/', 'Photo'),
    ('/api/evidence/signatures/', 'Signature'),
    ('/api/asset-nodes/', 'AssetNode'),
    ('/api/assets/', 'Asset'),
    ('/api/hospitals/', 'Hospital'),
    ('/api/work-orders/', 'WorkOrder'),
    ('/api/checklist-templates/', 'ChecklistTemplate'),
    ('/api/maintenance-plans/', 'MaintenancePlan'),
    ('/api/users/', 'User'),
    ('/api/inventory/items/', 'InventoryItem'),
    ('/api/inventory/movements/', 'StockMovement'),
]

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
