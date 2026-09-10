---
id: RNF-BAK-02
issue: 90
titulo: "Política de respaldo de archivos (S3)"
tipo: non-functional
prioridad: must-have
modulo: backup-retencion
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: backup-retencion']
---

# RNF-BAK-02 - Política de respaldo de archivos (S3)

### RNF-BAK-02: Política de respaldo de archivos (S3)
**Prioridad:** M

**Descripción:**
Las fotos, PDFs, y firmas almacenadas en S3 están protegidas contra eliminación accidental y pérdida.

**Criterios de aceptación:**
- **Versionado de S3 habilitado** en el bucket de archivos críticos (fotos de OTs, PDFs de reportes, imágenes de firmas). Si un objeto se elimina o sobreescribe accidentalmente, la versión anterior es recuperable.
- **S3 Object Lock (modo Governance)** habilitado para los PDFs de reportes con más de 30 días de antigüedad. Esto impide su eliminación incluso por el administrador de AWS, excepto con un proceso de desbloqueo explícito que requiere MFA. Protege la integridad de los registros de mantenimiento contra eliminación malintencionada.
- El bucket de S3 tiene **replicación cross-region** habilitada hacia otra región de AWS (ej: us-east-2 si la región principal es us-east-1), protegiendo contra pérdida de una región completa de AWS (evento extremadamente raro pero posible).
- Las fotos de OTs que ya fueron sincronizadas al servidor y están en S3 no se eliminan del servidor bajo ninguna circunstancia, incluso si la OT asociada es cancelada (se registra la foto con estado "huérfana" en lugar de eliminarla).
