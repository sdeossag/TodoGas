---
id: RNF-BAK-03
issue: 91
titulo: "Retención de datos históricos"
tipo: non-functional
prioridad: must-have
modulo: backup-retencion
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: backup-retencion']
---

# RNF-BAK-03 - Retención de datos históricos

### RNF-BAK-03: Retención de datos históricos
**Prioridad:** M

**Descripción:**
El sistema define claramente cuánto tiempo se retiene cada tipo de dato, combinando requisitos regulatorios, legales, y operacionales.

**Criterios de aceptación:**

| Tipo de dato | Retención mínima | Justificación |
|---|---|---|
| Registros de OTs completadas (datos + PDF + fotos + firmas) | 5 años | Requisitos GMP/BPM INVIMA, auditorías hospitalarias |
| Log de auditoría del sistema | 5 años | GMP/BPM, Ley 1581 (evidencia de medidas de seguridad), potenciales disputas legales |
| Datos personales de usuarios activos | Durante la vida del contrato + 2 años | Ley 1581 de 2012 |
| Datos personales de usuarios inactivos | 2 años desde la desactivación | Ley 1581 de 2012 |
| Backups de base de datos (RDS) | 30 días (rolling) | RTO/RPO operacional |
| Dumps semanales de base de datos | 90 días | Protección adicional contra pérdida |
| OTs canceladas y sus datos | 5 años | Coherencia de historial y posibles auditorías |
| Versiones archivadas de checklists | Indefinido mientras haya OTs que las referencien | Trazabilidad regulatoria |

- La retención de datos se implementa como una política de ciclo de vida: no se elimina automáticamente nada sin aprobación explícita del ADMIN y del responsable legal de la empresa.
- El sistema **no tiene purgas automáticas** de datos operacionales (OTs, activos, log). Las eliminaciones son siempre manuales y auditadas.
- Para datos que deban eliminarse por solicitud de Habeas Data (datos personales), el proceso es de anonimización, no eliminación física, para preservar la integridad de los registros de mantenimiento (ver RNF-COM-02).

---

## RNF-MAN — Mantenibilidad y Operaciones
