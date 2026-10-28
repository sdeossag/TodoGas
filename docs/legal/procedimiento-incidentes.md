# Procedimiento ante incidentes de seguridad con datos personales

Un incidente es cualquier hecho que comprometa la confidencialidad, integridad o disponibilidad de datos personales: acceso no autorizado, filtración, pérdida o robo de un teléfono con la app, envío de un acta al destinatario equivocado, cuenta comprometida, pérdida de un respaldo, uso indebido por un empleado.

## Roles

| Rol | Persona | Función |
|---|---|---|
| Responsable del incidente | `[CARGO DEL RESPONSABLE]` | Dirige la respuesta y decide la notificación |
| Responsable técnico | `[CARGO TÉCNICO]` | Contención, análisis de logs, recuperación |
| Responsable legal | `[CARGO LEGAL]` | Evalúa la obligación de reporte y redacta las comunicaciones |
| Contacto con hospitales | `[CARGO COMERCIAL]` | Avisa a los hospitales afectados |

Contacto interno de emergencia: `[CORREO DE CONTACTO]`, `[TELÉFONO]`.

## 1. Detección

Fuentes: alarmas de CloudWatch y del balanceador (picos de errores 4xx/5xx, accesos fallidos), Sentry si está activo (errores inesperados, nunca datos de usuario), el log de auditoría (accesos desde IP inusuales, exportaciones `EXPORT`, cambios fuera de horario), reportes de técnicos (teléfono perdido) o de hospitales, y avisos del proveedor de nube.

Toda persona que sospeche un incidente avisa de inmediato al responsable del incidente. No se espera a confirmarlo.

## 2. Registro inicial

Abrir el registro del incidente (plantilla en la sección 8) con fecha y hora en que la empresa **tuvo conocimiento**; de esa hora corre el plazo de 15 días hábiles.

## 3. Contención

- Desactivar las cuentas comprometidas (`is_active = false`) y obligar a cambiar contraseña (`must_change_password`).
- Si se perdió un teléfono: desactivar la cuenta del técnico o cerrar sus sesiones y cambiar su contraseña.
- Rotar secretos expuestos (claves de AWS, `SECRET_KEY`, DSN, credenciales de base de datos).
- Bloquear IP o rutas abusivas en el balanceador o el WAF.
- Si el origen es un bucket o un respaldo: restringir el acceso sin borrar evidencia. El bucket de evidencia tiene Object Lock; no se elimina nada.
- Conservar la evidencia: no sobrescribir logs, exportar los de CloudWatch y la auditoría antes de limpiar.

## 4. Evaluación del alcance

Con el log de auditoría (`audit_auditlog`: usuario, acción, entidad, IP, user agent, cambios, hora), que es append-only:

1. Filtrar por usuario sospechoso, IP, rango de fechas y tipo de acción en la pantalla de auditoría.
2. Exportar el resultado en CSV desde la misma pantalla. La exportación queda registrada como acción `EXPORT`; guardar el archivo en un lugar restringido, porque contiene IP y usuarios.
3. Determinar: qué datos (categorías del `inventario-datos-personales.md`), cuántos titulares, de qué hospitales, durante qué periodo, y si hubo acceso, copia o solo exposición.
4. Considerar si los datos eran de especial cuidado (firmas, ubicación).
5. Evaluar el riesgo para los titulares: suplantación con una firma, localización de personas, correo para phishing.
6. Documentar las limitaciones: el log registra IP y usuario de las acciones por la API, pero no cubre accesos directos a la base de datos ni al bucket (para esos, revisar CloudTrail y los registros de acceso de AWS).

## 5. Notificación a la SIC

El artículo 17, literal n), de la Ley 1581 de 2012 obliga al responsable a informar a la autoridad de protección de datos (SIC) cuando se presenten violaciones a los códigos de seguridad y existan riesgos en la administración de la información de los titulares. Las instrucciones de la SIC fijan que el reporte se hace dentro de los **quince (15) días hábiles siguientes** al momento en que se detecta y se pone en conocimiento del área encargada. `A confirmar con el asesor legal: formulario vigente de la SIC, medio de reporte (RNBD) y contenido exigido.`

Contenido recomendado del reporte: descripción del incidente, fecha de ocurrencia y de conocimiento, tipos de datos y número aproximado de titulares, causas probables, medidas de contención y mitigación tomadas, datos de contacto del responsable.

No hace falta tener toda la información para reportar: se reporta a tiempo y se complementa después.

## 6. Aviso a los titulares y a los hospitales

La ley no fija un texto para este aviso, pero informar a los titulares es una buena práctica y procede cuando el incidente suponga riesgo para ellos (por ejemplo, filtración de firmas o de contraseñas). El aviso debe decir en lenguaje claro: qué pasó, qué datos se vieron afectados, qué hicimos, qué debe hacer el titular (cambiar contraseña, estar atento a correos sospechosos) y a quién contactar. Si el incidente afecta datos de personal de un hospital, avisar también a su contacto y revisar si el contrato exige notificación en un plazo.

## 7. Recuperación y cierre

Restablecer servicios, forzar cambio de contraseñas, verificar la integridad de actas y firmas (los hash guardados permiten comprobar que no fueron alteradas), reforzar controles y cerrar el incidente con el responsable legal.

## 8. Registro del incidente

Para cada incidente guardar: identificador, fecha y hora de conocimiento, quién lo detectó, descripción, datos y titulares afectados, medidas de contención con hora, evidencia (exportaciones de auditoría y logs), decisión de reporte a la SIC con su justificación y radicado, avisos enviados, causa raíz, acciones correctivas con responsable y fecha. El registro se conserva 5 años.

## 9. Lecciones aprendidas

Dentro de los 15 días siguientes al cierre: reunión del equipo, ajustar el inventario, la política, las alarmas y la capacitación, y verificar que se cumplieron las acciones correctivas.

## Preparación permanente

- Probar al menos una vez al año el filtrado y la exportación del log de auditoría.
- Mantener actualizados los contactos de los roles.
- Capacitar a técnicos sobre pérdida de teléfono: avisar de inmediato, usar bloqueo de pantalla.
- Revisar que las alarmas de CloudWatch lleguen a un correo vigente.
