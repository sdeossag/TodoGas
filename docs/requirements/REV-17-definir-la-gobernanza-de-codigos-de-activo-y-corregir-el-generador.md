---
id: REV-17
issue: 113
titulo: "Definir la gobernanza de códigos de activo y corregir el generador"
tipo: functional
prioridad: should-have
modulo: activos
estado: CLOSED
etiquetas: ['priority: should-have', 'type: functional', 'mod: activos']
---

# REV-17 - Definir la gobernanza de códigos de activo y corregir el generador

### REV-17: Definir la gobernanza de códigos de activo y corregir el generador
**Prioridad:** S

**Descripción:**
El cliente arrastra varios sistemas de codificación y dejó abierta la decisión del formato. Además el generador produce códigos malformados porque toma el guion del código del hospital y no maneja el tipo vacío.

**Criterios de aceptación:**
- [ ] Formato de código acordado con el cliente
- [ ] Generador corregido (sin guiones dobles ni tipo vacío)
- [ ] Decisión sobre migrar los códigos existentes

**Implementación:**
Pendiente. La importación desde Fracttal conserva los códigos que trae (8fcd0b1), pero no define el formato.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `activos`
- Prioridad: `S`
- Fuente: `Revisión con el cliente (2026-09-10)`
