"""Exportacion CSV del log de auditoria: filtros, permisos, formato y rango."""

import csv
import datetime as dt
import io
import json
import uuid
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.exporter import resolve_date_range
from apps.audit.models import AuditLog
from apps.users.models import User

URL = '/api/audit/export/'
BOGOTA = ZoneInfo('America/Bogota')


# ── Helpers ──────────────────────────────────────────────────────────────────

def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_user(role, first='Ana', last='Lopez'):
    return User.objects.create_user(
        email=f'{uuid.uuid4()}@test.com',
        password='pass',
        first_name=first,
        last_name=last,
        role=role,
    )


def make_log(user, action, entity_type='Asset', timestamp=None, changes=None, ip=None):
    return AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=uuid.uuid4(),
        changes=changes or {},
        ip_address=ip,
        timestamp=timestamp or timezone.now(),
    )


def get_csv(response):
    """Devuelve (texto sin BOM, filas) de una respuesta en streaming."""
    raw = b''.join(response.streaming_content).decode('utf-8')
    assert raw.startswith('﻿'), 'el CSV debe empezar con BOM UTF-8'
    rows = list(csv.reader(io.StringIO(raw[1:])))
    return rows[0], rows[1:]


def days_ago(n):
    return timezone.now() - dt.timedelta(days=n)


# ── Permisos y formato ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_only_admin_can_export():
    admin = make_user(User.Role.ADMIN)
    sup = make_user(User.Role.SUP)
    tec = make_user(User.Role.TEC)
    make_log(admin, AuditLog.Action.CREATE)

    assert auth_client(admin).get(URL).status_code == 200
    assert auth_client(sup).get(URL).status_code == 403
    assert auth_client(tec).get(URL).status_code == 403


@pytest.mark.django_db
def test_anonymous_cannot_export():
    resp = APIClient().get(URL)
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_export_headers_bom_and_columns():
    admin = make_user(User.Role.ADMIN)
    make_log(admin, AuditLog.Action.CREATE, ip='10.0.0.1')

    resp = auth_client(admin).get(URL)

    assert resp.status_code == 200
    assert resp['Content-Type'] == 'text/csv; charset=utf-8'
    assert resp['Content-Disposition'].startswith('attachment; filename="auditoria_')
    assert resp['Content-Disposition'].endswith('.csv"')
    assert resp['Cache-Control'] == 'no-store'

    header, rows = get_csv(resp)
    assert header == [
        'fecha_hora', 'usuario', 'rol', 'accion', 'entidad',
        'id_entidad', 'ip', 'cambios',
    ]
    # Dos filas: el evento creado y la propia exportacion, que queda registrada
    # al iniciarse y cae dentro del rango por defecto.
    assert len(rows) == 2
    creado = next(r for r in rows if r[3] == 'Crear')
    assert creado[1] == admin.email
    assert creado[6] == '10.0.0.1'
    assert any(r[3] == 'Exportación' and r[4] == 'AuditLog' for r in rows)


@pytest.mark.django_db
def test_filename_uses_effective_range():
    admin = make_user(User.Role.ADMIN)
    resp = auth_client(admin).get(URL, {'date_from': '2026-01-05', 'date_to': '2026-02-10'})
    assert resp.status_code == 200
    assert resp['Content-Disposition'] == 'attachment; filename="auditoria_2026-01-05_2026-02-10.csv"'


@pytest.mark.django_db
def test_row_values_timezone_role_label_and_compact_json():
    admin = make_user(User.Role.ADMIN, first='Mónica', last='Ruiz')
    # 2026-03-10 15:30 UTC son las 10:30 en Bogota (UTC-5, sin horario de verano).
    ts = dt.datetime(2026, 3, 10, 15, 30, tzinfo=dt.timezone.utc)
    make_log(
        admin, AuditLog.Action.UPDATE, entity_type='Asset', timestamp=ts,
        changes={'nombre': {'from': 'Bomba', 'to': 'Bomba de vacío'}},
    )

    resp = auth_client(admin).get(URL, {'date_from': '2026-03-01', 'date_to': '2026-03-31'})
    header, rows = get_csv(resp)

    assert len(rows) == 1
    fecha, usuario, rol, accion, entidad, _id, ip, cambios = rows[0]
    assert fecha == '2026-03-10 10:30:00'
    assert usuario == admin.email
    assert rol == 'Administrador'
    assert accion == 'Actualizar'
    assert entidad == 'Asset'
    assert ip == ''
    # JSON compacto (sin espacios) y con tildes sin escapar. El orden de las
    # claves no se compara: JSONB de PostgreSQL no lo conserva.
    assert cambios == json.dumps(json.loads(cambios), ensure_ascii=False, separators=(',', ':'))
    assert 'vacío' in cambios
    assert json.loads(cambios) == {'nombre': {'from': 'Bomba', 'to': 'Bomba de vacío'}}


@pytest.mark.django_db
def test_system_rows_have_empty_user_and_role():
    admin = make_user(User.Role.ADMIN)
    make_log(None, AuditLog.Action.LOGIN, entity_type='Authentication')

    resp = auth_client(admin).get(URL)
    _, rows = get_csv(resp)
    assert rows[0][1] == ''
    assert rows[0][2] == ''


@pytest.mark.django_db
def test_csv_quotes_commas_and_newlines_in_changes():
    admin = make_user(User.Role.ADMIN)
    make_log(admin, AuditLog.Action.UPDATE, changes={'nota': 'uno, dos\ntres'})

    _, rows = get_csv(auth_client(admin).get(URL))
    assert rows[0][7] == '{"nota":"uno, dos\\ntres"}'


@pytest.mark.django_db
def test_export_is_chronological_ascending():
    admin = make_user(User.Role.ADMIN)
    make_log(admin, AuditLog.Action.CREATE, timestamp=days_ago(1))
    make_log(admin, AuditLog.Action.CREATE, timestamp=days_ago(3))

    _, rows = get_csv(auth_client(admin).get(URL))
    assert rows[0][0] < rows[1][0]


# ── Filtros ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_export_applies_same_filters_as_listing():
    admin = make_user(User.Role.ADMIN)
    other = make_user(User.Role.ADMIN)
    make_log(admin, AuditLog.Action.CREATE, entity_type='Asset')
    make_log(admin, AuditLog.Action.DELETE, entity_type='Asset')
    make_log(admin, AuditLog.Action.CREATE, entity_type='Hospital')
    make_log(other, AuditLog.Action.CREATE, entity_type='Asset')
    c = auth_client(admin)

    _, rows = get_csv(c.get(URL, {'action': 'CREATE', 'entity_type': 'Asset'}))
    assert len(rows) == 2
    assert all(r[3] == 'Crear' and r[4] == 'Asset' for r in rows)

    _, rows = get_csv(c.get(URL, {'user_id': str(other.id)}))
    assert len(rows) == 1
    assert rows[0][1] == other.email


@pytest.mark.django_db
def test_export_filter_by_entity_id():
    admin = make_user(User.Role.ADMIN)
    target = uuid.uuid4()
    AuditLog.objects.create(user=admin, action=AuditLog.Action.UPDATE,
                            entity_type='Asset', entity_id=target)
    make_log(admin, AuditLog.Action.UPDATE, entity_type='Asset')

    _, rows = get_csv(auth_client(admin).get(URL, {'entity_id': str(target)}))
    assert len(rows) == 1
    assert rows[0][5] == str(target)


@pytest.mark.django_db
def test_export_filter_by_search_text():
    admin = make_user(User.Role.ADMIN)
    make_log(admin, AuditLog.Action.CREATE, entity_type='Hospital')
    make_log(admin, AuditLog.Action.CREATE, entity_type='Asset')

    _, rows = get_csv(auth_client(admin).get(URL, {'search': 'hosp'}))
    assert len(rows) == 1
    assert rows[0][4] == 'Hospital'


@pytest.mark.django_db
def test_export_date_filter_is_inclusive():
    admin = make_user(User.Role.ADMIN)
    ts = dt.datetime(2026, 4, 15, 12, 0, tzinfo=dt.timezone.utc)  # 07:00 en Bogota
    make_log(admin, AuditLog.Action.CREATE, timestamp=ts)
    make_log(admin, AuditLog.Action.CREATE, timestamp=ts + dt.timedelta(days=5))
    c = auth_client(admin)

    _, rows = get_csv(c.get(URL, {'date_from': '2026-04-15', 'date_to': '2026-04-15'}))
    assert len(rows) == 1
    _, rows = get_csv(c.get(URL, {'date_from': '2026-04-15', 'date_to': '2026-04-20'}))
    assert len(rows) == 2


@pytest.mark.django_db
def test_no_date_filter_exports_only_last_90_days():
    admin = make_user(User.Role.ADMIN)
    make_log(admin, AuditLog.Action.CREATE, timestamp=days_ago(2))
    make_log(admin, AuditLog.Action.CREATE, timestamp=days_ago(200))

    resp = auth_client(admin).get(URL)
    _, rows = get_csv(resp)
    # El evento reciente mas la propia exportacion; el de hace 200 dias queda fuera.
    assert len(rows) == 2
    assert all(r[3] in ('Crear', 'Exportación') for r in rows)
    today = timezone.localdate()
    assert resp['Content-Disposition'] == (
        f'attachment; filename="auditoria_{(today - dt.timedelta(days=89))}_{today}.csv"'
    )


@pytest.mark.django_db
def test_only_date_from_defaults_to_today():
    admin = make_user(User.Role.ADMIN)
    resp = auth_client(admin).get(URL, {'date_from': '2026-10-01'})
    assert resp.status_code == 200
    today = timezone.localdate()
    assert resp['Content-Disposition'].endswith(f'_{today}.csv"')


# ── Rango maximo y validaciones ──────────────────────────────────────────────

@pytest.mark.django_db
def test_range_over_366_days_is_rejected_with_400():
    admin = make_user(User.Role.ADMIN)
    resp = auth_client(admin).get(URL, {'date_from': '2025-01-01', 'date_to': '2026-01-02'})
    assert resp.status_code == 400
    assert '366' in resp.json()['detail']


@pytest.mark.django_db
def test_range_of_exactly_366_days_is_allowed():
    admin = make_user(User.Role.ADMIN)
    # 2025-01-01 .. 2026-01-01 son 366 dias contando los dos extremos.
    resp = auth_client(admin).get(URL, {'date_from': '2025-01-01', 'date_to': '2026-01-01'})
    assert resp.status_code == 200


@pytest.mark.django_db
def test_inverted_range_is_rejected():
    admin = make_user(User.Role.ADMIN)
    resp = auth_client(admin).get(URL, {'date_from': '2026-05-10', 'date_to': '2026-05-01'})
    assert resp.status_code == 400


@pytest.mark.django_db
def test_invalid_date_format_is_rejected():
    admin = make_user(User.Role.ADMIN)
    resp = auth_client(admin).get(URL, {'date_from': '01/05/2026'})
    assert resp.status_code == 400


@pytest.mark.django_db
def test_export_does_not_fail_on_empty_result():
    admin = make_user(User.Role.ADMIN)
    resp = auth_client(admin).get(URL, {'date_from': '2020-01-01', 'date_to': '2020-01-02'})
    header, rows = get_csv(resp)
    assert resp.status_code == 200
    assert header[0] == 'fecha_hora'
    assert rows == []


# ── Unidad: resolve_date_range ───────────────────────────────────────────────

def test_resolve_date_range_defaults_use_today():
    today = dt.date(2026, 10, 28)
    assert resolve_date_range(None, None, today=today) == (
        dt.date(2026, 7, 31), dt.date(2026, 10, 28),
    )
    assert resolve_date_range('2026-10-20', None, today=today) == (
        dt.date(2026, 10, 20), dt.date(2026, 10, 28),
    )


# ── Registro de auditoria de la propia exportacion ──────────────────────────

@pytest.mark.django_db
def test_export_creates_audit_entry_with_filters_and_range():
    admin = make_user(User.Role.ADMIN)
    make_log(admin, AuditLog.Action.CREATE, entity_type='Asset')

    resp = auth_client(admin).get(
        URL,
        {'action': 'CREATE', 'entity_type': 'Asset', 'date_from': '2026-03-01', 'date_to': '2026-03-31'},
        HTTP_USER_AGENT='pruebas-export',
    )
    assert resp.status_code == 200
    # El registro se crea al iniciar la exportacion, aunque aun no se haya leido el cuerpo.
    entries = AuditLog.objects.filter(action=AuditLog.Action.EXPORT)
    assert entries.count() == 1
    entry = entries.get()
    assert entry.user == admin
    assert entry.entity_type == 'AuditLog'
    assert entry.user_agent == 'pruebas-export'
    assert entry.changes == {
        'filters': {'action': 'CREATE', 'entity_type': 'Asset'},
        'date_from': '2026-03-01',
        'date_to': '2026-03-31',
    }


@pytest.mark.django_db
def test_export_audit_entry_uses_effective_range_when_no_dates():
    admin = make_user(User.Role.ADMIN)
    auth_client(admin).get(URL)

    entry = AuditLog.objects.get(action=AuditLog.Action.EXPORT)
    today = timezone.localdate()
    assert entry.changes['date_to'] == today.isoformat()
    assert entry.changes['date_from'] == (today - dt.timedelta(days=89)).isoformat()
    assert entry.changes['filters'] == {}


@pytest.mark.django_db
def test_rejected_export_creates_no_audit_entry():
    admin = make_user(User.Role.ADMIN)
    resp = auth_client(admin).get(URL, {'date_from': '2025-01-01', 'date_to': '2026-01-02'})
    assert resp.status_code == 400
    assert not AuditLog.objects.filter(action=AuditLog.Action.EXPORT).exists()


@pytest.mark.django_db
def test_forbidden_export_creates_no_audit_entry():
    tec = make_user(User.Role.TEC)
    assert auth_client(tec).get(URL).status_code == 403
    assert not AuditLog.objects.filter(action=AuditLog.Action.EXPORT).exists()
