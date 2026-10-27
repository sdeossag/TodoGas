---
id: REV-23
issue: 118
titulo: "El costo total de la OT siempre queda en $0"
tipo: bug
prioridad: should-have
modulo: inventario
estado: CLOSED
etiquetas: ['priority: should-have', 'type: bug', 'mod: inventario']
---

# REV-23 - El costo total de la OT siempre queda en $0

### REV-23: El costo total de la OT siempre queda en $0
**Prioridad:** S

**Descripción:**
El costo unitario del ítem no se copiaba al movimiento de salida y el costo total de la OT quedaba en cero. El cliente después decidió que la OT no debe llevar costo.

**Criterios de aceptación:**
- [ ] Copiar el costo unitario al movimiento (descartado: ya no se usa costo en la OT)

**Implementación:**
Reemplazada por la decisión de octubre: el costo no se muestra ni se escribe en la OT; la columna se conserva por los datos existentes (nota en backend/apps/work_orders/models.py). Queda una columna «Costo unit.» en la pestaña de repuestos que conviene retirar.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `inventario`
- Prioridad: `S`
- Fuente: `Barrido QA (2026-09-08)`
