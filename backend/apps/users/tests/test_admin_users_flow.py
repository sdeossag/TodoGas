"""
Contrato que consume la gestion de usuarios del frontend (/usuarios, /auditoria).

Cada test replica exactamente la llamada que hace la UI, con el mismo payload,
para que un cambio en el backend que rompa la pantalla falle aqui primero.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework import status

from apps.assets.models import Hospital
from apps.audit.models import AuditLog

User = get_user_model()

USERS_URL = "/api/users/"
AUDIT_URL = "/api/audit/"

# La misma forma que genera generateTempPassword() en UsersPage.jsx
TEMP_PASSWORD = "Kp7x!mQ2vRt9Zb"


@pytest.fixture
def hospital(db):
    return Hospital.objects.create(name="Hospital San Vicente", code="HSV-001")


def create_payload(**overrides):
    """Payload identico al que arma CreateUserModal."""
    payload = {
        "first_name": "Carlos",
        "last_name": "Ramirez",
        "email": "carlos.ramirez@todogas.com",
        "role": "TEC",
        "employee_code": "1017234567",
        "phone": "3001234567",
        "hospital": None,
        "password": TEMP_PASSWORD,
    }
    payload.update(overrides)
    return payload


class TestListado:
    """PASO 1 del flujo: la tabla se llena."""

    def test_lista_viene_paginada(self, admin_client, admin_user):
        resp = admin_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_200_OK
        # Antes este endpoint devolvia un array plano y el test lo fijaba
        # asi, avisando de que UsersPage filtra en memoria. Ahora la API
        # pagina por defecto (RF-AC-05, RNF-REN-01) y es useUsers() quien
        # recorre las paginas, de modo que la tabla sigue recibiendo la
        # lista completa y el filtrado en memoria sigue siendo correcto.
        assert set(resp.data) >= {"count", "next", "previous", "results"}
        assert any(u["email"] == admin_user.email for u in resp.data["results"])

    def test_expone_los_campos_que_pinta_la_tabla(self, admin_client):
        resp = admin_client.get(USERS_URL)
        row = resp.data["results"][0]
        for field in ("id", "full_name", "email", "role", "hospital", "is_active"):
            assert field in row, f"la tabla necesita {field}"


class TestCrearUsuario:
    """PASOS 2 y 3 del flujo: crear tecnico y crear cliente."""

    def test_crea_tecnico_y_envia_correo_de_bienvenida(self, admin_client):
        mail.outbox.clear()
        resp = admin_client.post(USERS_URL, create_payload(), format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        creado = User.objects.get(email="carlos.ramirez@todogas.com")
        assert creado.role == "TEC"
        assert creado.employee_code == "1017234567"
        assert creado.must_change_password is True
        assert creado.check_password(TEMP_PASSWORD)

        assert len(mail.outbox) == 1
        assert TEMP_PASSWORD in mail.outbox[0].body

    def test_crea_cliente_vinculado_a_hospital(self, admin_client, hospital):
        payload = create_payload(
            email="cliente@hsv.com",
            role="CLI",
            hospital=str(hospital.id),
            employee_code="",
            phone="",
        )
        resp = admin_client.post(USERS_URL, payload, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        assert User.objects.get(email="cliente@hsv.com").hospital_id == hospital.id

    def test_email_duplicado_devuelve_el_error_bajo_la_clave_email(self, admin_client):
        admin_client.post(USERS_URL, create_payload(), format="json")
        resp = admin_client.post(USERS_URL, create_payload(), format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        # CreateUserModal lo pinta debajo del campo email leyendo esta clave.
        assert "email" in resp.data

    def test_la_temporal_generada_pasa_el_validador(self, admin_client):
        resp = admin_client.post(USERS_URL, create_payload(), format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data


class TestAccionesDeFila:
    """PASOS 4 y 5 del flujo: restablecer contrasena y desactivar/activar."""

    def test_restablecer_contrasena(self, admin_client, tech_user):
        mail.outbox.clear()
        anterior = tech_user.password

        resp = admin_client.post(f"{USERS_URL}{tech_user.id}/reset-password/")

        assert resp.status_code == status.HTTP_200_OK
        tech_user.refresh_from_db()
        assert tech_user.password != anterior
        assert tech_user.must_change_password is True
        assert len(mail.outbox) == 1

    def test_desactivar(self, admin_client, tech_user):
        resp = admin_client.post(f"{USERS_URL}{tech_user.id}/deactivate/")

        assert resp.status_code == status.HTTP_200_OK
        tech_user.refresh_from_db()
        assert tech_user.is_active is False

    def test_reactivar_por_patch(self, admin_client, tech_user):
        tech_user.is_active = False
        tech_user.save(update_fields=["is_active"])

        # No existe accion `activate`: el boton Activar manda este PATCH.
        resp = admin_client.patch(
            f"{USERS_URL}{tech_user.id}/", {"is_active": True}, format="json"
        )

        assert resp.status_code == status.HTTP_200_OK, resp.data
        tech_user.refresh_from_db()
        assert tech_user.is_active is True

    def test_admin_no_puede_desactivarse_por_la_accion(self, admin_client, admin_user):
        resp = admin_client.post(f"{USERS_URL}{admin_user.id}/deactivate/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        admin_user.refresh_from_db()
        assert admin_user.is_active is True

    def test_admin_no_puede_desactivarse_por_patch(self, admin_client, admin_user):
        resp = admin_client.patch(
            f"{USERS_URL}{admin_user.id}/", {"is_active": False}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        admin_user.refresh_from_db()
        assert admin_user.is_active is True


class TestEdicion:
    """PASO 4: el modal de edicion guarda los campos editables."""

    def test_actualiza_datos_sin_tocar_el_rol(self, admin_client, tech_user):
        resp = admin_client.patch(
            f"{USERS_URL}{tech_user.id}/",
            {
                "first_name": "Nombre",
                "last_name": "Nuevo",
                "phone": "3009998877",
                "employee_code": "999",
                "role": "ADMIN",  # el modal no lo manda; si llegara, se ignora
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK
        tech_user.refresh_from_db()
        assert tech_user.first_name == "Nombre"
        assert tech_user.phone == "3009998877"
        assert tech_user.role == "TEC", "el rol no debe poder escalarse por PATCH"


class TestAuditoria:
    """PASOS 6 y 7 del flujo: la pagina de auditoria y sus filtros."""

    @pytest.fixture
    def logs(self, db, admin_user, tech_user):
        AuditLog.objects.create(
            user=admin_user, action="CREATE", entity_type="User",
            entity_id=tech_user.id, changes={"email": tech_user.email},
        )
        AuditLog.objects.create(
            user=admin_user, action="UPDATE", entity_type="WorkOrder",
            entity_id=tech_user.id,
            changes={"assigned_to": {"from": None, "to": str(tech_user.id)}},
        )
        AuditLog.objects.create(
            user=tech_user, action="LOGIN", entity_type="User",
            entity_id=tech_user.id, changes={},
        )

    def test_lista_paginada_con_los_campos_de_la_tabla(self, admin_client, logs):
        resp = admin_client.get(AUDIT_URL)

        assert resp.status_code == status.HTTP_200_OK
        assert "results" in resp.data and "count" in resp.data
        row = resp.data["results"][0]
        for field in ("timestamp", "user", "action", "entity_type", "entity_id", "changes"):
            assert field in row

    def test_filtra_por_usuario_y_por_accion(self, admin_client, logs, admin_user):
        por_usuario = admin_client.get(AUDIT_URL, {"user_id": str(admin_user.id)})
        assert por_usuario.data["count"] == 2

        por_accion = admin_client.get(AUDIT_URL, {"action": "LOGIN"})
        assert por_accion.data["count"] == 1

    def test_page_size_limita_la_actividad_reciente(self, admin_client, logs, admin_user):
        # El modal de usuario pide los ultimos 5 con page_size, no con limit.
        resp = admin_client.get(AUDIT_URL, {"user_id": str(admin_user.id), "page_size": 5})
        assert len(resp.data["results"]) <= 5

    def test_solo_admin_entra(self, tech_client, logs):
        assert tech_client.get(AUDIT_URL).status_code == status.HTTP_403_FORBIDDEN
