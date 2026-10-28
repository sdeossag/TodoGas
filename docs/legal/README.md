# Documentación legal: protección de datos personales

Esta carpeta reúne los documentos base para cumplir con la Ley 1581 de 2012 y el Decreto 1377 de 2013 (compilado en el Decreto 1074 de 2015) en el uso del CMMS TodoGas. El repositorio es público: los documentos usan marcadores entre corchetes y no contienen datos reales de la empresa ni de sus clientes.

## Contenido

| Archivo | Para qué sirve |
|---|---|
| `inventario-datos-personales.md` | Qué datos personales trata el sistema, de quién, para qué, dónde se guardan, quién los ve y por cuánto tiempo. Es la base para el Registro Nacional de Bases de Datos (RNBD) ante la SIC. |
| `politica-tratamiento-plantilla.md` | Plantilla de la Política de Tratamiento de Información de la empresa. |
| `aviso-privacidad.md` | Texto del aviso que la app muestra en el primer ingreso y en `/privacidad`. |
| `procedimiento-incidentes.md` | Pasos ante un incidente de seguridad con datos personales. |
| `derechos-del-titular.md` | Cómo el administrador atiende cada derecho del titular. |

## Qué debe completar el cliente

1. Reemplazar todos los marcadores: `[RAZÓN SOCIAL]`, `[NIT]`, `[DIRECCIÓN]`, `[CIUDAD]`, `[CORREO DE CONTACTO]`, `[TELÉFONO]`, `[CARGO DEL RESPONSABLE]`.
2. Publicar la política en un lugar accesible a los titulares (sitio web de la empresa) y poner esa dirección en el aviso de privacidad.
3. Registrar las bases de datos en el RNBD (SIC) si la empresa está obligada. La obligación depende de los activos de la empresa y de su naturaleza; lo confirma el asesor legal.
4. Definir los puntos marcados «A confirmar» en cada documento (plazos de retención, modo del Object Lock, proveedores, región de AWS, responsable de peticiones).
5. Fijar el proceso de onboarding que obtiene la autorización del titular antes de crear su usuario. El sistema sí registra la aceptación del aviso en el primer ingreso (con versión, fecha, IP y user agent) y muestra un recordatorio al crear usuarios, pero no reemplaza la autorización previa del titular.

## Qué hace hoy el sistema

- **Aviso con aceptación al primer ingreso.** La app bloquea el uso hasta que el usuario acepta la versión vigente del aviso. La aceptación se guarda en `PrivacyConsent`. Si cambia la versión (`PRIVACY_NOTICE_VERSION`), se vuelve a pedir.
- **Línea de autorización bajo la firma** del receptor del hospital, con enlace al aviso.
- **Recordatorio al crear usuarios** de confirmar la autorización del titular.
- **«Mis datos personales»** en Mi perfil, con descarga JSON. El administrador puede exportar los datos de cualquier usuario; cada exportación queda en auditoría (`EXPORT`).
- **Anonimización** por el administrador de cuentas desactivadas con más de 730 días de inactividad; queda en auditoría (`ANONYMIZE`). No se borran OT, firmas de actas, fotos, auditoría ni consentimientos.
- **Exportación CSV del log de auditoría**, registrada como `EXPORT`.
- **Auditoría automática** de escrituras: guarda método, estado, entidad, usuario, IP y user agent. No guarda el cuerpo de las peticiones, así que no quedan contraseñas ni tokens. Los intentos de inicio de sesión guardan el correo y el resultado.

## Revisión

Un asesor legal del cliente debe revisar todos los textos antes de publicarlos. Estos documentos son una base técnica elaborada a partir de lo que el sistema guarda de verdad; no sustituyen asesoría jurídica ni constituyen concepto legal.

## Mantenimiento

- El texto del aviso de privacidad vive también en `frontend/src/legal/avisoPrivacidad.js`. Se cambian juntos y se sube la versión.
- Si se agrega un modelo o campo con datos personales, actualizar el inventario en el mismo cambio.
- Las funciones descritas arriba existen en el código (aviso, «Mis datos», exportaciones, anonimización). Antes de prometer un plazo a un titular, confirmar que la versión desplegada las incluye.
