---
id: RF-FD-03
issue: 28
titulo: "Cumplimiento con Ley 527 de 1999"
tipo: functional
prioridad: must-have
modulo: firma-digital
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: firma-digital', 'needs-fracttal-review']
---

# RF-FD-03 - Cumplimiento con Ley 527 de 1999

### RF-FD-03: Cumplimiento con Ley 527 de 1999
**Prioridad:** M

**Descripción:**
La implementación de firma digital cumple con los requisitos mínimos de la Ley 527 de 1999 (Colombia) para que las firmas tengan validez como mensajes de datos con efectos legales.

**Criterios de aceptación:**
- La firma del técnico cumple el criterio de "firma atribuible" de la Ley 527: está vinculada a un usuario autenticado con credenciales únicas (correo + contraseña), con registro de la acción de autenticación en el log.
- Se genera y almacena un hash SHA-256 del conjunto {datos de la OT + imagen de firma del técnico + timestamp de firma}. Este hash garantiza que cualquier alteración posterior del documento sea detectable.
- El hash de integridad se incluye en el pie de página del PDF del reporte con el texto: "Documento firmado electrónicamente. Hash de integridad: [valor]. Verificable en el sistema CMMS."
- El log de auditoría del sistema registra el evento de firma con: ID de usuario, método de autenticación usado, timestamp, hash generado. Este log es parte del registro probatorio.
- El sistema almacena los datos de firma por mínimo 5 años sin posibilidad de eliminación.

> ⚠️ **Nota de alcance:** Esta implementación cubre **firma electrónica simple** (Ley 527, Art. 7). No implementa firma electrónica certificada con PKI ni firma digital con certificado de entidad de certificación reconocida (más compleja y costosa). Si en el futuro se requiere mayor fuerza probatoria, se puede evolucionar a firma certificada sin rediseñar el sistema.

---

## MÓDULO PDF — Generación de Documentos
