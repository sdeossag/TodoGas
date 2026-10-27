---
id: RF-FD-04
issue: 132
titulo: "Firma guardada por usuario, usable sin red"
tipo: functional
prioridad: must-have
modulo: firma-digital
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: firma-digital', 'platform: backend', 'platform: web', 'platform: android']
---

# RF-FD-04 - Firma guardada por usuario, usable sin red

### RF-FD-04: Firma guardada por usuario, usable sin red
**Prioridad:** M

**Descripción:**
Firmar cada orden a mano es repetitivo. Cada usuario registra su firma una vez en Mi perfil y la reutiliza, incluso sin red; al cerrar sesión se borra del teléfono.

**Criterios de aceptación:**
- [x] El usuario registra su firma en Mi perfil
- [x] La firma se puede usar al cerrar una OT sin conexión
- [x] Se borra del teléfono al cerrar sesión
- [x] Técnicos y cuentas de hospital pueden abrir Mi perfil
- [x] El acta usa la firma guardada

**Implementación:**
Implementado en `5e92475` (firma guardada) con ajustes de acceso en `02c2a4b` (técnico) y `c86bc96` (hospital). Archivos clave: `backend/apps/evidence/firma_guardada.py`, `backend/apps/evidence/models.py`, `frontend/src/router/index.jsx`, `frontend/src/utils/layoutPerfil.js`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `firma-digital`
- Prioridad: `M`
- Fuente: `Revisión con el cliente (2026-10-23)`
