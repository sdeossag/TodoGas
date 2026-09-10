---
id: RNF-MAN-03
issue: 94
titulo: "Pipeline de CI/CD"
tipo: non-functional
prioridad: must-have
modulo: mantenibilidad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: mantenibilidad']
---

# RNF-MAN-03 - Pipeline de CI/CD

### RNF-MAN-03: Pipeline de CI/CD
**Prioridad:** M

**Descripción:**
El proyecto tiene un pipeline de integración y despliegue continuo que garantiza que los cambios no rompan funcionalidades existentes antes de llegar a producción.

**Criterios de aceptación:**
- El pipeline corre automáticamente en **GitHub Actions** en cada Pull Request y en cada merge a las ramas `main` (producción) y `staging`.
- **Pasos del pipeline en cada PR:**
  1. Linting (Ruff/Flake8 para Python, ESLint para JS): el pipeline falla si hay errores de estilo.
  2. Tests del backend (pytest-django): el pipeline falla si algún test falla.
  3. Reporte de cobertura de tests (no falla el pipeline, pero muestra el % actual).
  4. `pip audit` y `npm audit`: el pipeline alerta (no falla) si hay dependencias con vulnerabilidades críticas.
- **Despliegue a staging:** automático al hacer merge a la rama `staging`. El despliegue es blue-green o rolling para cero downtime.
- **Despliegue a producción:** manual (requiere aprobación explícita en GitHub Actions) al hacer merge a `main`. Nunca automático a producción.
- El tiempo total del pipeline (lint + tests) no supera los **10 minutos** para mantener el ciclo de feedback rápido.
