---
id: REV-21
issue: 116
titulo: "Un usuario Cliente puede quedarse sin hospital y ver un portal vacío"
tipo: bug
prioridad: should-have
modulo: usuarios-roles
estado: CLOSED
etiquetas: ['priority: should-have', 'type: bug', 'mod: usuarios-roles']
---

# REV-21 - Un usuario Cliente puede quedarse sin hospital y ver un portal vacío

### REV-21: Un usuario Cliente puede quedarse sin hospital y ver un portal vacío
**Prioridad:** S

**Descripción:**
El formulario de creación exigía hospital para el rol Cliente, pero el de edición ofrecía «Sin hospital» y el servidor no validaba, dejando un portal vacío sin explicación. No había fuga de datos.

**Criterios de aceptación:**
- [x] El serializer valida que un usuario Cliente tenga hospital
- [x] El formulario de edición no ofrece «Sin hospital» para ese rol

**Implementación:**
Validación «Una cuenta de hospital necesita su hospital» en el serializer (286710e). Archivo: backend/apps/users/serializers.py.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `usuarios-roles`
- Prioridad: `S`
- Fuente: `Barrido QA (2026-09-08)`
