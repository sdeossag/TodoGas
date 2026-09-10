---
id: RNF-COM-04
issue: 81
titulo: "Retención y disponibilidad de registros para auditoría"
tipo: non-functional
prioridad: must-have
modulo: cumplimiento-legal
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: cumplimiento-legal']
---

# RNF-COM-04 - Retención y disponibilidad de registros para auditoría

### RNF-COM-04: Retención y disponibilidad de registros para auditoría
**Prioridad:** M

**Descripción:**
El sistema garantiza que los registros críticos están disponibles para auditorías externas (INVIMA, Ministerio de Salud, clientes) en cualquier momento durante el período de retención definido.

**Criterios de aceptación:**
- Todos los registros de mantenimiento (OTs completadas + PDFs + fotos + firmas + log de auditoría) se conservan **sin posibilidad de eliminación** durante un mínimo de **5 años** desde la fecha del registro.
- Los registros son accesibles en ≤ 24 horas ante una solicitud de auditoría: el ADMIN puede generar reportes exportables de cualquier activo, hospital, o período desde la interfaz web.
- Los PDFs de reportes almacenados en S3 tienen **versionado habilitado** y **Object Lock** configurado (modo Governance) para los objetos con más de 1 año de antigüedad, evitando su eliminación accidental o malintencionada.
- El sistema puede exportar el log de auditoría completo en formato CSV para un período de tiempo dado, útil para presentar a auditores.
- La empresa debe designar un responsable (ADMIN) como punto de contacto para solicitudes de auditoría. El sistema provee las herramientas; la gestión del proceso es responsabilidad de la empresa.

---

## RNF-AND — Compatibilidad de la App Android
