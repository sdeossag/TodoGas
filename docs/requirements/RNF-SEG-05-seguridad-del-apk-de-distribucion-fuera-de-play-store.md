---
id: RNF-SEG-05
issue: 70
titulo: "Seguridad del APK de distribución fuera de Play Store"
tipo: non-functional
prioridad: must-have
modulo: seguridad
estado: CLOSED
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: seguridad']
---

# RNF-SEG-05 - Seguridad del APK de distribución fuera de Play Store

### RNF-SEG-05: Seguridad del APK de distribución fuera de Play Store
**Prioridad:** M

**Descripción:**
Dado que el APK se distribuye fuera del Play Store (sideloading), se implementan controles adicionales para garantizar que solo usuarios autorizados puedan instalar y usar la app.

**Criterios de aceptación:**
- El APK está **firmado** con un keystore de la empresa (no con un keystore de debug). El keystore se almacena de forma segura y con respaldo, no en el repositorio.
- El APK incluye **ProGuard/R8** habilitado en la build de producción para ofuscar el código y dificultar la ingeniería inversa.
- La app implementa **certificate pinning** para el dominio del API: la app solo acepta el certificado SSL del servidor de producción, rechazando conexiones si el certificado es reemplazado (protección contra ataques MitM).
- La distribución del APK se realiza a través de un canal seguro y controlado (ej: enlace privado en S3 con URL pre-firmada, o correo directo al dispositivo). El enlace de descarga expira y no es público.
- La app no almacena el password del usuario en el dispositivo, solo el refresh token (en SecureStorage de Capacitor / Android Keystore).
- El refresh token almacenado en el dispositivo está cifrado con la API de Android Keystore (no en SharedPreferences en texto claro).
