---
id: RNF-MAN-01
issue: 92
titulo: "Estructura y calidad del código"
tipo: non-functional
prioridad: must-have
modulo: mantenibilidad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: mantenibilidad']
---

# RNF-MAN-01 - Estructura y calidad del código

### RNF-MAN-01: Estructura y calidad del código
**Prioridad:** M

**Descripción:**
El código base es mantenible, legible, y sigue convenciones consistentes que permiten a nuevos desarrolladores incorporarse sin una curva de aprendizaje excesiva.

**Criterios de aceptación:**
- **Backend (Django):** código en inglés para nombres de variables, funciones, clases, y comentarios técnicos. Los mensajes al usuario final (UI, correos, errores) están en español. Se sigue PEP 8 enforceado con **Ruff** o **Flake8** en el pipeline de CI.
- **Frontend (React):** componentes en inglés, lógica separada de presentación, estilos con Tailwind CSS (sin CSS-in-JS ni archivos CSS separados excepto para estilos globales). Se usa **ESLint** con las reglas de `eslint-plugin-react` en el pipeline de CI.
- **Cobertura de tests:** el backend tiene cobertura de tests automatizados (pytest-django) mínima del **70%** en los módulos críticos: autenticación, permisos, gestión de OTs, generación de PDF, sincronización offline. Se mide con `coverage.py` en el pipeline de CI.
- **Documentación de APIs:** el API de Django REST Framework expone una especificación **OpenAPI 3.0** auto-generada (vía drf-spectacular) accesible en el entorno de desarrollo. Esta documentación es la fuente de verdad para el desarrollo del frontend y la app.
- El repositorio tiene un `README.md` con instrucciones completas para levantar el entorno de desarrollo local desde cero en menos de 30 minutos (incluyendo dependencias, variables de entorno, migraciones, y datos de prueba).
