"""Ninguna ruta real debe acabar guardada como URL cruda en la auditoria.

Regresion: _PATH_ENTITY_MAP tenia '/api/checklist-templates/' y
'/api/maintenance-plans/' escritos con guion, mientras las rutas reales llevan
barra ('/api/checklists/templates/', '/api/maintenance/plans/'). No coincidian
nunca, asi que toda la actividad de checklists y planes PM se guardaba con la
URL entera como entity_type y quedaba fuera del filtro de la pantalla de
auditoria. Un fallo silencioso: nada peta, la traza simplemente deja de ser
consultable justo donde mas importa (submit-field y complete son el rastro de
lo que el tecnico verifico).
"""

import pytest
from django.urls import Resolver404, resolve

from apps.audit.middleware import _PATH_ENTITY_MAP, _entity_type_from_path

# Un endpoint representativo por modulo, tal y como los llama el frontend.
RUTAS_REALES = [
    "/api/hospitals/",
    "/api/assets/",
    "/api/asset-nodes/",
    "/api/asset-custom-fields/",
    "/api/work-orders/",
    "/api/checklists/templates/",
    "/api/checklists/responses/",
    "/api/maintenance/plans/",
    "/api/maintenance/plan-tasks/",
    "/api/tasks/",
    "/api/reschedule-causes/",
    "/api/inventory/items/",
    "/api/inventory/movements/",
    "/api/evidence/photos/",
    "/api/evidence/signatures/",
    "/api/reports/",
    "/api/users/",
    "/api/auth/logout/",
]


@pytest.mark.parametrize("ruta", RUTAS_REALES)
def test_route_exists(ruta):
    """Si esto falla, el prefijo del mapa apunta a una ruta que no existe."""
    try:
        resolve(ruta)
    except Resolver404:
        pytest.fail(f"{ruta} no resuelve: el mapa de auditoria esta desalineado")


@pytest.mark.parametrize("ruta", RUTAS_REALES)
def test_route_maps_to_a_named_entity(ruta):
    entidad = _entity_type_from_path(ruta)
    assert not entidad.startswith("/api/"), (
        f"{ruta} se guardaria como URL cruda ('{entidad}') en vez de un tipo de "
        "entidad filtrable"
    )


@pytest.mark.parametrize(
    "ruta,esperado",
    [
        ("/api/checklists/templates/abc/publish-version/", "ChecklistTemplate"),
        ("/api/checklists/responses/abc/submit-field/", "ChecklistResponse"),
        ("/api/checklists/responses/abc/complete/", "ChecklistResponse"),
        ("/api/maintenance/plans/abc/assign-assets/", "MaintenancePlan"),
        ("/api/maintenance/plan-tasks/abc/create-occurrence/", "PlanTask"),
        ("/api/tasks/abc/reschedule/", "Task"),
        ("/api/tasks/cancel/", "Task"),
        ("/api/reports/consolidated/", "GeneratedReport"),
        ("/api/auth/login/", "Authentication"),
    ],
)
def test_nested_actions_keep_their_entity(ruta, esperado):
    """Las acciones anidadas heredan la entidad de su modulo, no la URL."""
    assert _entity_type_from_path(ruta) == esperado


def test_specific_prefixes_win_over_generic_ones():
    """El orden del mapa importa: gana el primero que casa.

    '/api/auth/' es el mas generico y va al final; si subiera, se comeria rutas
    de otros modulos.
    """
    assert _entity_type_from_path("/api/asset-nodes/x/") == "AssetNode"
    assert _entity_type_from_path("/api/assets/x/") == "Asset"
    assert _entity_type_from_path("/api/asset-custom-fields/x/") == "AssetCustomField"
    assert _PATH_ENTITY_MAP[-1][0] == "/api/auth/"
