---
id: RNF-PDF-03
issue: 88
titulo: "Librería y tecnología de generación"
tipo: non-functional
prioridad: must-have
modulo: pdf
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: pdf']
---

# RNF-PDF-03 - Librería y tecnología de generación

### RNF-PDF-03: Librería y tecnología de generación
**Prioridad:** M

**Descripción:**
La librería de generación de PDFs es madura, compatible con el stack de Django, y capaz de manejar layouts complejos con imágenes y estilos.

**Criterios de aceptación:**
- Se usa **WeasyPrint** (renderizado HTML/CSS → PDF) o **ReportLab** (generación programática) como librería principal. La elección se define en la fase de desarrollo inicial basándose en la complejidad del template de PDF requerido por la empresa. WeasyPrint es preferible si el template tiene CSS complejo; ReportLab si el layout es muy estructurado.
- La librería elegida soporta: imágenes incrustadas desde URLs de S3, texto con caracteres especiales del español (ñ, acentos, ü), tablas con bordes y estilos, paginación automática para checklists largos, y cabecera/pie de página repetido en cada página.
- La generación de PDFs corre en un worker de Celery **separado** del worker de tareas generales, para que una cola de PDFs larga no bloquee otras tareas asíncronas del sistema (notificaciones, envío de correos).

---

## RNF-BAK — Respaldo y Retención de Datos

---

---

**Metadatos de importacion**
- Tipo: `Requisito no funcional`
- Fase: `2`
- Repositorio destino: `sdeossag/TodoGas`
- Categoria: `PDF - Generación de Documentos PDF`
- Prioridad: `M`
- Fuente: `CMMS Gases Medicinales - Fase 2: Requisitos No Funcionales`

**Implementación (revisión del 2026-10-27):**
- [x] WeasyPrint o ReportLab — WeasyPrint 69, ADR-001
- [x] Imágenes de S3, caracteres del español, tablas y pie repetido — Acta con tablas y pie en cada página
- [ ] Worker de Celery de PDFs separado del general — Un solo worker (--concurrency 2) y una sola cola

Commits: 45090aa
Archivos: `docs/adr/ADR-001-pdf-library.md`, `infra/terraform/ecs.tf`, `backend/requirements.txt`
