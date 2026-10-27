---
id: OPS-04
issue: 149
titulo: "Verificar el bloqueo por intentos fallidos de inicio de sesión"
tipo: chore
prioridad: should-have
modulo: seguridad
estado: CLOSED
etiquetas: ['priority: should-have', 'type: chore', 'mod: seguridad', 'platform: backend']
---

# OPS-04 - Verificar el bloqueo por intentos fallidos de inicio de sesión

### OPS-04: Verificar el bloqueo por intentos fallidos de inicio de sesión
**Prioridad:** S

**Descripción:**
Se mencionó que la cuenta se bloquea tras muy pocos intentos. Hay que comprobar el límite real y dejarlo documentado.

**Criterios de aceptación:**
- [ ] Se confirma el límite actual con una prueba
- [ ] Se decide si se ajusta
- [ ] Se documenta límite y duración
- [ ] La prueba automática cubre el valor
- [ ] El mensaje al usuario es claro

**Implementación:**
Pendiente. En `backend/apps/users/throttling.py` el límite es `MAX_ATTEMPTS = 5` con bloqueo de 30 minutos (`LOCKOUT_SECONDS`); falta verificarlo en las vistas de autenticación y documentarlo.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `seguridad`
- Prioridad: `S`
- Fuente: `Operación`
