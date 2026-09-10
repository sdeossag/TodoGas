---
id: RF-NT-03
issue: 58
titulo: "Notificación de nueva OT al técnico por correo"
tipo: functional
prioridad: must-have
modulo: notificaciones
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: notificaciones']
---

# RF-NT-03 - Notificación de nueva OT al técnico por correo

### RF-NT-03: Notificación de nueva OT al técnico por correo
**Prioridad:** M

**Descripción:**
Complementariamente a la notificación push, el técnico recibe un correo electrónico al ser asignado a una OT, con todos los detalles necesarios para prepararse antes de la visita.

**Criterios de aceptación:**
- **Asunto del correo:** `Nueva OT asignada — {número} | {nombre del activo} | {hospital} | Prioridad: {nivel}`
- **Contenido:** nombre y código del activo, hospital y área de ubicación, descripción del trabajo a realizar, fecha y hora límite, checklist asignado (solo el nombre, no el contenido completo), observaciones del ADMIN, enlace directo a la OT en la web (como referencia; el TEC trabaja principalmente desde la app).
- El correo se envía dentro de los 2 minutos de la creación/asignación de la OT.

---

*Fin del documento Fase 1 — Requisitos Funcionales*

---

## Resumen ejecutivo por módulo

| Módulo | Must Have | Should Have | Could Have | Total |
|--------|-----------|-------------|------------|-------|
| AC — Activos | 6 | 1 | 0 | 7 |
| OT — Órdenes de Trabajo | 8 | 0 | 0 | 8 |
| PM — Planes Preventivos | 3 | 1 | 0 | 4 |
| CK — Checklists | 4 | 0 | 0 | 4 |
| EV — Evidencia | 2 | 0 | 0 | 2 |
| FD — Firma Digital | 3 | 0 | 0 | 3 |
| PDF — Documentos | 2 | 1 | 0 | 3 |
| TR — Trazabilidad | 3 | 0 | 0 | 3 |
| US — Usuarios y Roles | 4 | 0 | 0 | 4 |
| BI — Dashboard / BI | 1 | 2 | 0 | 3 |
| IN — Inventario | 4 | 0 | 0 | 4 |
| OF — Modo Offline | 3 | 0 | 0 | 3 |
| CL — Portal Cliente | 3 | 0 | 0 | 3 |
| MI — Migración | 4 | 0 | 0 | 4 |
| NT — Notificaciones | 3 | 0 | 0 | 3 |
| **TOTAL** | **53** | **5** | **0** | **58** |

---

## Pendientes de validar con capturas de Fracttal

Los siguientes ítems requieren revisión directa del sistema Fracttal con rol administrador antes de finalizar la especificación:

1. **RF-AC-01** — Niveles exactos de la jerarquía de activos en Fracttal.
2. **RF-US-02** — Existencia y alcance del rol Supervisor en Fracttal.
3. **RF-PDF-01** — Revisar los templates de PDF existentes (acta de servicio y reporte de mantenimiento) para mapear los campos exactos.
4. **RF-MI-01/02/03** — Revisar el módulo de exportación de Fracttal para confirmar formatos y campos disponibles para migración.
5. **RF-FD-03** — Verificar si Fracttal usa firma electrónica o solo firma canvas, para entender la expectativa actual del cliente con la firma.

---

**Metadatos de importacion**
- Repositorio destino: `sdeossag/TodoGas`
- Modulo: `NT - Notificaciones y Comunicaciones`
- Prioridad: `M`
- Fuente: `CMMS_Fase1_Requisitos_Funcionales.md`
