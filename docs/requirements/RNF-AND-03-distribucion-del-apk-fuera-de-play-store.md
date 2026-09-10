---
id: RNF-AND-03
issue: 84
titulo: "Distribución del APK fuera de Play Store"
tipo: non-functional
prioridad: must-have
modulo: android
estado: CLOSED
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: android']
---

# RNF-AND-03 - Distribución del APK fuera de Play Store

### RNF-AND-03: Distribución del APK fuera de Play Store
**Prioridad:** M

**Descripción:**
El APK se distribuye directamente a los técnicos fuera de Google Play Store (sideloading). El proceso de distribución e instalación es controlado y seguro.

**Criterios de aceptación:**
- El APK se distribuye a través de un enlace privado generado por el equipo de desarrollo (S3 pre-signed URL con expiración de 7 días), enviado individualmente a cada técnico.
- El proceso de instalación requiere que el técnico habilite "Instalar apps de fuentes desconocidas" en su dispositivo Android. El equipo de desarrollo o el ADMIN realiza esta configuración en el dispositivo en la primera instalación (no se deja al técnico hacerlo solo).
- Las **actualizaciones del APK** se distribuyen manualmente: el ADMIN notifica a los técnicos cuando hay una nueva versión, proporciona el enlace, y verifica que todos actualizaron antes de desactivar la versión anterior del API si hay cambios incompatibles.
- La app implementa un mecanismo de **verificación de versión mínima**: al iniciar, consulta el API para saber si la versión instalada es compatible. Si no lo es, muestra una pantalla de "Actualización requerida" con instrucciones para descargar la nueva versión. El técnico no puede usar la app hasta actualizar.
- El `versionCode` del APK se incrementa en cada release y sigue semver (ej: `1.0.0`, `1.1.0`, `1.2.0`).
