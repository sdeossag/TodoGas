# Aviso de privacidad

Versión: 2026-10-28

> Nota: el mismo texto vive en `frontend/src/legal/avisoPrivacidad.js` (constante `PARRAFOS`). Deben cambiarse juntos y subir la versión en ambos, y en `PRIVACY_NOTICE_VERSION` del backend (`backend/config/settings/base.py`). Al subir la versión, todos los usuarios vuelven a aceptar el aviso al entrar.

---

[RAZÓN SOCIAL], NIT [NIT], es la responsable del tratamiento de los datos personales que se registran en esta aplicación de gestión de mantenimiento.

Tratamos su nombre, correo, teléfono, rol y firma, la ubicación GPS de las fotos de evidencia, su dirección IP y el registro de su actividad en la aplicación.

Los usamos para gestionar el mantenimiento de los equipos, generar las actas de servicio, mantener la trazabilidad que exige la normativa sanitaria y enviarle comunicaciones propias del servicio.

Usted tiene derecho a conocer, actualizar y rectificar sus datos, a solicitar su supresión, a revocar la autorización y a presentar quejas ante la Superintendencia de Industria y Comercio (SIC).

Puede ver y descargar sus datos en «Mi perfil». También puede escribirnos a [CORREO DE CONTACTO]. La supresión no alcanza las actas, firmas, fotos ni registros de auditoría ya generados, porque la normativa sanitaria obliga a conservarlos.

La política completa de tratamiento de datos la publica [RAZÓN SOCIAL] y está disponible para todos los titulares.

---

Cómo se presenta en la app:

- **Primer ingreso:** pantalla bloqueante con el texto y los botones «Cerrar sesión» y «Acepto». Sin aceptar la versión vigente no se usa la aplicación. La aceptación queda registrada (versión, fecha, IP y user agent).
- **Página pública `/privacidad`:** el mismo texto, sin iniciar sesión.
- **Bajo la firma de quien recibe en el hospital:** «Al firmar autoriza el tratamiento de su nombre, cargo y firma para el acta de servicio, según el aviso de privacidad de [RAZÓN SOCIAL].», con enlace al aviso.
- **Si el backend configura `PRIVACY_POLICY_URL`:** el enlace «Ver la política completa» abre esa dirección fuera de la aplicación. Si está vacía, el enlace despliega la frase de que la política la publica [RAZÓN SOCIAL].
