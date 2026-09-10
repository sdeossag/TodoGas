---
id: RF-AC-02
issue: 2
titulo: "Ficha técnica de activo"
tipo: functional
prioridad: must-have
modulo: activos
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: activos']
---

# RF-AC-02 - Ficha técnica de activo

### RF-AC-02: Ficha técnica de activo
**Prioridad:** M

**Descripción:**
Cada activo en nivel "Equipo" o "Componente" tiene una ficha técnica completa con campos predefinidos obligatorios, campos predefinidos opcionales, y la posibilidad de añadir campos personalizados configurables por tipo de activo.

**Criterios de aceptación:**
- **Campos predefinidos obligatorios:** nombre del activo, código interno (único en el sistema), tipo de activo, marca, modelo, número de serie, año de fabricación, estado (Activo / Inactivo / En mantenimiento / Dado de baja), hospital al que pertenece, área/ubicación dentro del hospital, fecha de instalación.
- **Campos predefinidos opcionales:** potencia, presión de trabajo nominal, tipo de gas manejado (Oxígeno / Nitrógeno / CO₂ / Aire medicinal / Vacío / Otro), capacidad, número de reguladores, número de salidas, fecha de último mantenimiento registrado, número de placa INVIMA (si aplica al equipo).
- El ADMIN puede definir hasta 20 campos personalizados por tipo de activo (no por activo individual). Tipos de campo disponibles: texto libre, número con unidades, fecha, selección desplegable (lista de valores definida por el ADMIN). Los campos personalizados aplican automáticamente a todos los activos del mismo tipo.
- La ficha es visible (solo lectura) para `ADMIN`, `SUP`, y `TEC` cuando el activo tiene OTs asignadas a ese técnico.
- El `CLI` solo puede ver la ficha de los activos de su propio hospital.
- La ficha muestra el último mantenimiento registrado y la próxima fecha de mantenimiento preventivo programado.
