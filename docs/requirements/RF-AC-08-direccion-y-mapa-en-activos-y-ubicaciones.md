---
id: RF-AC-08
issue: 129
titulo: "Dirección y mapa en activos y ubicaciones"
tipo: functional
prioridad: should-have
modulo: activos
estado: CLOSED
etiquetas: ['priority: should-have', 'type: functional', 'mod: activos', 'platform: backend', 'platform: web', 'platform: android']
---

# RF-AC-08 - Dirección y mapa en activos y ubicaciones

### RF-AC-08: Dirección y mapa en activos y ubicaciones
**Prioridad:** S

**Descripción:**
Para llegar al sitio hace falta saber dónde está. Los equipos y las ubicaciones guardan un punto en el mapa y su dirección, que se completa al sincronizar.

**Criterios de aceptación:**
- [x] El equipo guarda la localización GPS y se obtiene la dirección
- [x] Cada ubicación del árbol tiene dirección y punto en el mapa
- [x] La web muestra un mapa en la ficha
- [x] La dirección se completa al sincronizar desde el teléfono
- [x] El acta incluye un mapa pequeño

**Implementación:**
Implementado en `2ad7943` (localización GPS con dirección y mapa) y `8caf0ef` (dirección y mapa por ubicación). Archivos clave: `backend/apps/assets/geo.py`, `backend/apps/assets/models.py`, `frontend/src/components/maps/GoogleMap.jsx`, `frontend/src/pages/assets/LocationsPage.jsx`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `activos`
- Prioridad: `S`
- Fuente: `Revisión con el cliente (2026-09-10)`
