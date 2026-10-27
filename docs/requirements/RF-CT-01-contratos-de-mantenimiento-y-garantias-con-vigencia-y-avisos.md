---
id: RF-CT-01
issue: 125
titulo: "Contratos de mantenimiento y garantías con vigencia y avisos"
tipo: functional
prioridad: should-have
modulo: contratos
estado: CLOSED
etiquetas: ['priority: should-have', 'type: functional', 'platform: backend', 'platform: web', 'mod: contratos']
---

# RF-CT-01 - Contratos de mantenimiento y garantías con vigencia y avisos

### RF-CT-01: Contratos de mantenimiento y garantías con vigencia y avisos
**Prioridad:** S

**Descripción:**
Se necesita llevar los contratos de mantenimiento y las garantías, con sus fechas, para saber cuándo vencen. El sistema solo avisa; no bloquea nada.

**Criterios de aceptación:**
- [x] Se registra un contrato o garantía por hospital o rama del árbol de ubicaciones
- [x] Se asocia una lista de equipos al contrato
- [x] Se guarda la vigencia y el documento PDF
- [x] Se envía correo a los administradores a los 60 y 30 días del vencimiento
- [x] El portal del hospital ve la vigencia y el PDF

**Implementación:**
Implementado en `56383e5`. Archivos clave: `backend/apps/assets/contracts.py`, `backend/apps/assets/models.py`, `backend/apps/assets/serializers_contracts.py`, migración `0006_contratos_y_garantias.py`.

---

**Metadatos**
- Repositorio destino: `sdeossag/TodoGas`
- Módulo: `contratos`
- Prioridad: `S`
- Fuente: `Revisión con el cliente (2026-10-23)`
