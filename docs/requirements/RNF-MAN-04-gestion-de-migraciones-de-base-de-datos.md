---
id: RNF-MAN-04
issue: 95
titulo: "Gestión de migraciones de base de datos"
tipo: non-functional
prioridad: must-have
modulo: mantenibilidad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: mantenibilidad']
---

# RNF-MAN-04 - Gestión de migraciones de base de datos

### RNF-MAN-04: Gestión de migraciones de base de datos
**Prioridad:** M

**Descripción:**
Las migraciones de base de datos se gestionan de forma segura para garantizar que los despliegues no generen downtime ni pérdida de datos.

**Criterios de aceptación:**
- Todas las migraciones de esquema se generan con **Django Migrations** (`makemigrations`) y se incluyen en el repositorio como archivos versionados.
- Las migraciones son **backwards compatible** cuando es posible (añadir columnas con `null=True` primero, luego hacerlas required en una migración posterior). Esto permite despliegues sin downtime.
- Las migraciones que no son backwards compatible (ej: renombrar una columna, cambiar un tipo de dato) se planifican para ejecutarse durante una ventana de mantenimiento notificada con 24 horas de anticipación.
- **Las migraciones nunca se corren manualmente en producción.** El pipeline de CD ejecuta `python manage.py migrate` como parte del proceso de despliegue de forma automática y controlada.
- Existe un proceso documentado para el rollback de una migración fallida (restaurar desde backup de RDS en el peor caso).

---

*Fin del documento Fase 2 — Requisitos No Funcionales*

---

## Resumen ejecutivo por categoría

| Categoría | Must Have | Should Have | Could Have | Total |
|---|---|---|---|---|
| RNF-REN — Rendimiento | 3 | 1 | 0 | 4 |
| RNF-DIS — Disponibilidad | 3 | 0 | 0 | 3 |
| RNF-SEG — Seguridad | 6 | 0 | 0 | 6 |
| RNF-ESC — Escalabilidad | 1 | 1 | 0 | 2 |
| RNF-USA — Usabilidad en Campo | 2 | 2 | 0 | 4 |
| RNF-COM — Cumplimiento Normativo | 4 | 0 | 0 | 4 |
| RNF-AND — Compatibilidad Android | 4 | 0 | 0 | 4 |
| RNF-PDF — Documentos PDF | 3 | 0 | 0 | 3 |
| RNF-BAK — Respaldo y Retención | 3 | 0 | 0 | 3 |
| RNF-MAN — Mantenibilidad | 4 | 0 | 0 | 4 |
| **TOTAL** | **33** | **4** | **0** | **37** |

---

## Marco normativo colombiano aplicable — Resumen

| Norma | Qué regula | Impacto directo en el CMMS |
|---|---|---|
| **Decreto 4725/2005** (INVIMA) | Clasificación de gases medicinales como medicamentos | Trazabilidad completa de mantenimiento de equipos asociados |
| **Resolución 1403/2007** (Min. Salud) | Requisitos técnicos de sistemas de gases medicinales en IPS | Documentación de intervenciones, checklist, firmas, periodicidad |
| **NTC 3561 / ISO 7396-1** | Sistemas de tuberías de gases medicinales | Sección 8 define requisitos de registros de mantenimiento |
| **Ley 1581/2012 + Decreto 1377/2013** | Protección de datos personales (Habeas Data) | Inventario de datos, consentimiento, derechos del titular, seguridad |
| **Ley 527/1999 + Decreto 2364/2012** | Comercio electrónico y firma electrónica | Validez de firmas digitales capturadas en las OTs |
| **Resolución 3100/2019** (Min. Salud) | Procedimientos y condiciones para la habilitación de IPS | Los hospitales clientes usan los reportes del CMMS en sus procesos de habilitación |

> **Nota importante:** este análisis normativo es una interpretación técnica basada en el contexto del proyecto. Antes del lanzamiento a producción, se recomienda que la empresa valide el marco de cumplimiento con un asesor jurídico especializado en regulación sanitaria colombiana y con un oficial de protección de datos (DPO), especialmente para el cumplimiento de Ley 1581.

---

**Metadatos de importacion**
- Tipo: `Requisito no funcional`
- Fase: `2`
- Repositorio destino: `sdeossag/TodoGas`
- Categoria: `MAN - Mantenibilidad y Operaciones`
- Prioridad: `M`
- Fuente: `CMMS Gases Medicinales - Fase 2: Requisitos No Funcionales`
