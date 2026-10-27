---
id: REV-25
issue: 139
titulo: "Campo libre tipo «Otro» en el activo"
tipo: functional
prioridad: could-have
modulo: activos
estado: OPEN
etiquetas: ['priority: could-have', 'type: functional', 'mod: activos', 'platform: backend', 'platform: web']
---

# REV-25 - Campo libre tipo «Otro» en el activo

### REV-25: Campo libre tipo «Otro» en el activo
**Prioridad:** C

**Descripción:**
Algunos equipos tienen un dato que no cabe en los campos actuales. Se pide un campo libre para anotarlo sin cambiar el sistema.

**Criterios de aceptación:**
- [ ] El administrador puede activar un campo libre «Otro» en el activo
- [ ] El valor se guarda y se muestra en la ficha
- [ ] Se puede editar desde el formulario
- [ ] Aparece en el acta solo si tiene valor
- [ ] Existen pruebas del campo

**Implementación:**
Pendiente. Implica ampliar el modelo de activo en `backend/apps/assets/models.py` y el formulario web.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `activos`
- Prioridad: `C`
- Fuente: `Revisión con el cliente (2026-10-23)`
