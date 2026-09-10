---
id: RF-OT-02
issue: 9
titulo: "Creación manual de OT correctiva o predictiva"
tipo: functional
prioridad: must-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: ordenes-trabajo']
---

# RF-OT-02 - Creación manual de OT correctiva o predictiva

### RF-OT-02: Creación manual de OT correctiva o predictiva
**Prioridad:** M

**Descripción:**
Solo el `ADMIN` puede crear OTs correctivas y predictivas manualmente. El formulario de creación captura toda la información necesaria para la ejecución y el reporte posterior.

**Criterios de aceptación:**
- Solo usuarios con rol `ADMIN` tienen acceso al formulario de creación de OT. Cualquier otro rol que intente acceder recibe error 403.
- **Campos obligatorios:** activo afectado (buscador con autocompletado), tipo de OT (Correctiva o Predictiva), descripción de la falla o trabajo a realizar (texto libre, mín. 20 caracteres), técnico asignado (selección de lista de técnicos activos), fecha y hora límite de atención, prioridad (Alta / Media / Baja).
- **Campos opcionales:** checklist a aplicar (selección de plantilla existente del catálogo), lista de repuestos anticipados (preselección del inventario), observaciones adicionales para el técnico.
- Para OTs predictivas: el campo "motivo de generación predictiva" se vuelve obligatorio automáticamente al seleccionar ese tipo.
- Al guardar, el número de OT se genera automáticamente con formato `OT-{AÑO}-{SECUENCIAL_5_DÍGITOS}` (ej: `OT-2026-00001`). El secuencial es global (no por hospital).
- El estado inicial de toda OT creada manualmente es **"Pendiente"**.
- Al crear la OT, el sistema envía inmediatamente: notificación push a la app Android del técnico asignado y correo electrónico al mismo técnico con el detalle de la OT.
