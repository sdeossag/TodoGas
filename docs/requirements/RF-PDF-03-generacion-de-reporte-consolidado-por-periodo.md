---
id: RF-PDF-03
issue: 31
titulo: "Generación de reporte consolidado por período"
tipo: functional
prioridad: should-have
modulo: pdf
estado: OPEN
etiquetas: ['priority: should-have', 'type: functional', 'mod: pdf']
---

# RF-PDF-03 - Generación de reporte consolidado por período

### RF-PDF-03: Generación de reporte consolidado por período
**Prioridad:** S

**Descripción:**
El `ADMIN` puede generar reportes consolidados en PDF para un hospital específico o para todos, filtrando por período de tiempo.

**Criterios de aceptación:**
- El `ADMIN` selecciona: hospital (o "todos"), rango de fechas, tipo de OT (o todos los tipos), y solicita el reporte consolidado.
- El reporte consolidado contiene: resumen ejecutivo (total de OTs por tipo, % de completadas, activos intervenidos), tabla de OTs del período (número, tipo, activo, técnico, fecha, estado, referencia al PDF individual), y gráfico de cumplimiento si se filtra por un solo hospital.
- La generación tarda máx. 60 segundos para períodos de hasta 12 meses con el universo de 3,940 activos.
- El consolidado puede descargarse directamente o enviarse por correo al destinatario que el ADMIN indique.

---

## MÓDULO TR — Trazabilidad e Historial Inmutable

---

---

**Metadatos de importacion**
- Repositorio destino: `sdeossag/TodoGas`
- Modulo: `PDF - Generación de Documentos`
- Prioridad: `S`
- Fuente: `CMMS_Fase1_Requisitos_Funcionales.md`

**Implementación (revisión del 2026-10-27):**
- [x] Filtros: hospital o todos, fechas, tipo de OT — ReportsPage.jsx y ConsolidatedReportView (solo ADMIN).
- [x] Resumen ejecutivo: total, % completadas, activos intervenidos — consolidated_report.html.
- [x] Tabla de OT con número, tipo, activo, técnico, fecha, estado
- [ ] Referencia al PDF individual en la tabla — No aparece.
- [ ] Gráfico de cumplimiento si es un solo hospital — El PDF solo trae una tabla de estados.
- [ ] Máximo 60 s para 12 meses con 3.940 activos — Sin prueba ni medición.
- [ ] Descargar directo o enviar por correo a quien indique el ADMIN — La tarea guarda el PDF y devuelve un enlace, pero la pantalla no lo muestra ni se envía correo, aunque el texto dice que sí. No hay campo de destinatario.

Commits: 334d516
Archivos: `backend/apps/reports/tasks.py`, `backend/apps/reports/templates/reports/consolidated_report.html`, `frontend/src/pages/reports/ReportsPage.jsx`
