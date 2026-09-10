---
id: RNF-COM-03
issue: 80
titulo: "Firma electrónica — Ley 527 de 1999"
tipo: non-functional
prioridad: must-have
modulo: cumplimiento-legal
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: cumplimiento-legal']
---

# RNF-COM-03 - Firma electrónica — Ley 527 de 1999

### RNF-COM-03: Firma electrónica — Ley 527 de 1999
**Prioridad:** M

**Descripción:**
La implementación técnica de la firma digital en el sistema cumple los requisitos mínimos de la Ley 527 de 1999 para que las firmas capturadas tengan validez legal en Colombia como mensajes de datos.

*(Los requisitos técnicos específicos están en RF-FD-03 de la Fase 1. Este RNF define los requerimientos de cumplimiento y validación legal.)*

**Marco normativo aplicable:**
- **Ley 527 de 1999**: Ley de Comercio Electrónico. El Art. 7 establece los requisitos de una firma electrónica válida en Colombia.
- **Decreto 2364 de 2012**: reglamenta el Art. 7 de la Ley 527 respecto a la firma electrónica.

**Criterios de aceptación:**
- La firma implementada cumple los 3 criterios del Art. 7 de la Ley 527 y el Decreto 2364: (1) es **única** respecto al firmante (vinculada al usuario autenticado), (2) es susceptible de **verificación** (hash de integridad verificable), (3) está bajo el **control exclusivo** del firmante en el momento de firmar (sesión autenticada del técnico).
- El sistema conserva la evidencia de respaldo de cada firma (log de autenticación + metadatos de la firma + hash) por **mínimo 5 años**, plazo suficiente para cualquier disputa legal o proceso contractual con hospitales.
- La implementación es de **firma electrónica simple** (no firma digital certificada con PKI). Este nivel es suficiente para documentos de mantenimiento interno y relaciones contractuales B2B. Si en el futuro la empresa requiere firma con mayor fuerza probatoria (ej: documentos con valor notarial), se puede evolucionar sin rediseño del sistema.
- El PDF de reporte incluye una nota al pie con el aviso legal: *"Este documento ha sido firmado electrónicamente en cumplimiento de la Ley 527 de 1999. El hash de integridad garantiza que el documento no ha sido alterado desde su firma."*
