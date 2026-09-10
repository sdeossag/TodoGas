---
id: RNF-AND-01
issue: 82
titulo: "Versiones de Android soportadas"
tipo: non-functional
prioridad: must-have
modulo: android
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: android']
---

# RNF-AND-01 - Versiones de Android soportadas

### RNF-AND-01: Versiones de Android soportadas
**Prioridad:** M

**Descripción:**
La app Android soporta un rango de versiones que cubre los dispositivos que los técnicos de campo utilizan actualmente y los que puedan adquirir durante la vida útil del sistema.

**Criterios de aceptación:**
- **Versión mínima soportada: Android 8.0 (API Level 26 — Oreo).** Esta versión fue lanzada en 2017; a la fecha, cubre más del 95% de los dispositivos Android activos en el mercado.
- **Versión objetivo (compilación): Android 14 (API Level 34).** El APK se compila con el `targetSdkVersion` más reciente estable.
- La app se prueba explícitamente en Android 8.0, Android 10, Android 12, y Android 14 antes de cada release.
- Funcionalidades que dependen de versiones específicas de Android (ej: Biometric API, Keystore) se implementan con comprobación de versión en runtime y fallback para versiones anteriores.
- **No se soporta Android inferior a 8.0.** Si un técnico tiene un dispositivo con Android 7 o anterior, la app no le permite instalarla y muestra un mensaje claro de requisito mínimo.
