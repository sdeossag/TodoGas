---
id: RNF-COM-01
issue: 78
titulo: "Trazabilidad para auditorías GMP/BPM (INVIMA)"
tipo: non-functional
prioridad: must-have
modulo: cumplimiento-legal
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: cumplimiento-legal']
---

# RNF-COM-01 - Trazabilidad para auditorías GMP/BPM (INVIMA)

### RNF-COM-01: Trazabilidad para auditorías GMP/BPM (INVIMA)
**Prioridad:** M

**Descripción:**
El sistema soporta los requisitos de trazabilidad de las Buenas Prácticas de Manufactura (BPM/GMP) aplicables a empresas que mantienen equipos de gases medicinales, en cumplimiento con la normatividad INVIMA colombiana y los requisitos de habilitación de prestadores de servicios de salud del Ministerio de Salud.

**Marco normativo aplicable:**
- **Decreto 4725 de 2005** (INVIMA): clasifica los gases medicinales como medicamentos e impone requisitos de trazabilidad en su fabricación, distribución y mantenimiento.
- **Resolución 1403 de 2007** (Ministerio de Protección Social): define requisitos técnicos y de documentación para sistemas de distribución de gases medicinales en instituciones de salud.
- **NTC 3561 / ISO 7396-1**: estándar para sistemas de tuberías de gases medicinales. La Sección 8 (Mantenimiento) requiere: programa de mantenimiento documentado, registros de cada intervención con fecha y personal, resultados de pruebas, firma del responsable.

**Criterios de aceptación:**
- Cada OT completada genera un registro que contiene todos los elementos requeridos por ISO 7396-1 sección 8 para un registro de mantenimiento válido: identificación inequívoca del equipo intervenido, fecha y hora de la intervención, identificación del personal que la realizó (nombre + identificación), descripción del trabajo realizado, resultados de pruebas o verificaciones (checklist), firma del técnico responsable.
- El sistema garantiza que los registros de mantenimiento son **inalterables** una vez completados (ver RF-TR-03). En una auditoría INVIMA, la empresa puede demostrar que los registros no han sido modificados gracias al hash de integridad (RF-FD-03).
- El historial de mantenimiento de cada activo puede exportarse como PDF consolidado que sirve como "expediente del equipo" presentable ante auditores (ver RF-AC-06).
- Los perfiles de usuarios en el sistema incluyen el nombre completo del técnico, que aparece en todos los registros de mantenimiento, cumpliendo el requisito de identificación del personal.
- El sistema mantiene los registros por **mínimo 5 años** desde la fecha de la intervención (ver RNF-BAK-03). Esto excede el mínimo típico de registros GMP (generalmente 2-3 años para equipos médicos) para dar margen de seguridad.
- El ADMIN puede generar un reporte de "todas las intervenciones sobre un activo específico" en un rango de fechas, directamente útil para responder a solicitudes de auditoría INVIMA o habilitación hospitalaria.
