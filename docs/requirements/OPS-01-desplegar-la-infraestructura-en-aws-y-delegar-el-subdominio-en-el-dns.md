---
id: OPS-01
issue: 146
titulo: "Desplegar la infraestructura en AWS y delegar el subdominio en el DNS"
tipo: chore
prioridad: must-have
modulo: disponibilidad
estado: OPEN
etiquetas: ['priority: must-have', 'type: chore', 'mod: disponibilidad', 'platform: infra', 'blocked']
---

# OPS-01 - Desplegar la infraestructura en AWS y delegar el subdominio en el DNS

### OPS-01: Desplegar la infraestructura en AWS y delegar el subdominio en el DNS
**Prioridad:** M

**Descripción:**
Se necesita publicar el sistema en AWS con el código de infraestructura existente. Para el dominio solo se añaden registros NS del subdominio, sin tocar los existentes.

**Criterios de aceptación:**
- [ ] Se aplica la infraestructura en el entorno de prueba y luego en producción
- [ ] Se delegan los 4 registros NS del subdominio sin tocar los demás
- [ ] La app responde con HTTPS en el subdominio
- [ ] Los correos y las tareas programadas funcionan
- [ ] El procedimiento queda documentado

**Implementación:**
Pendiente. El Terraform está listo en `infra/terraform`; pasos en `infra/README.md`. Bloqueada: depende de que se apruebe el costo del alojamiento.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `disponibilidad`
- Prioridad: `M`
- Fuente: `Operación`
