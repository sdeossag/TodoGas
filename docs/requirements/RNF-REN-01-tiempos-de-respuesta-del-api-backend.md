---
id: RNF-REN-01
issue: 59
titulo: "Tiempos de respuesta del API (backend)"
tipo: non-functional
prioridad: must-have
modulo: rendimiento
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: rendimiento']
---

# RNF-REN-01 - Tiempos de respuesta del API (backend)

### RNF-REN-01: Tiempos de respuesta del API (backend)
**Prioridad:** M

**Descripción:**
El API de Django REST Framework debe responder en tiempos aceptables para todos los roles bajo la carga normal de operación (≤25 usuarios concurrentes). Los tiempos se miden desde que la petición llega al servidor hasta que la respuesta completa sale del servidor (sin incluir latencia de red del cliente).

**Criterios de aceptación:**
- **Percentil 95 (P95) de todas las peticiones:** ≤ 500 ms en condiciones de carga normal (hasta 25 usuarios concurrentes).
- **Percentil 99 (P99) de todas las peticiones:** ≤ 1,500 ms.
- **Endpoints de listados paginados** (activos, OTs, hospitales): ≤ 500 ms para los primeros 50 registros con filtros aplicados sobre el universo completo de datos.
- **Endpoints de detalle** (ficha de activo, detalle de OT): ≤ 300 ms.
- **Endpoints de escritura** (crear OT, cambiar estado, guardar checklist): ≤ 600 ms.
- **Búsqueda de activos por texto libre:** ≤ 2,000 ms (con índices de texto completo en PostgreSQL).
- Las consultas SQL individuales no deben superar los 200 ms. Ninguna vista del API debe ejecutar más de 10 queries SQL (evitar N+1 con select_related/prefetch_related en Django ORM).
- Los tiempos se verifican con pruebas de carga usando **Locust** o **k6** antes de cada release a producción.

---

---

**Metadatos de importacion**
- Tipo: `Requisito no funcional`
- Fase: `2`
- Repositorio destino: `sdeossag/TodoGas`
- Categoria: `REN - Rendimiento`
- Prioridad: `M`
- Fuente: `CMMS Gases Medicinales - Fase 2: Requisitos No Funcionales`

**Implementación (revisión del 2026-10-27):**
- [ ] P95/P99, detalle y escritura dentro de los límites — No hay medición; la infraestructura no está desplegada
- [x] Listados paginados de 50 registros — Paginación por defecto de 50
- [x] Búsqueda de texto con índices GIN/trigram — Índices trigram en activos
- [ ] Máximo 10 consultas SQL por vista (sin N+1) — Hay select_related/prefetch_related, pero solo 2 pruebas de número de consultas
- [ ] Pruebas de carga con Locust o k6 antes de cada release — No existe ningún script ni paso de CI

Commits: 03f69e8
Archivos: `backend/config/settings/base.py`, `backend/apps/assets/models.py`, `backend/config/pagination.py`
