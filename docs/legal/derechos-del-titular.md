# Cómo se atienden los derechos del titular

Guía para el administrador del CMMS. Cada solicitud llega a `[CORREO DE CONTACTO]` y la atiende `[CARGO DEL RESPONSABLE]`.

> Funciones disponibles en el sistema: «Mis datos personales» con descarga JSON en «Mi perfil»; exportación de los datos de un usuario por el administrador; exportación CSV del log de auditoría; anonimización de cuentas inactivas por el administrador. Las tres exportaciones y la anonimización quedan en el registro de auditoría. Si una función no está desplegada en el entorno del cliente, se atiende a mano y se deja constancia.

## Reglas generales

1. Verificar la identidad del solicitante antes de entregar o cambiar datos (correo registrado o documento de identidad). No entregar datos de una persona a un tercero sin autorización del titular o poder.
2. Registrar la solicitud: fecha de recibo, titular, derecho invocado, responsable, respuesta y fecha. El plazo corre desde el recibo.
3. Plazos (Ley 1581 de 2012):
   - **Consulta**: 10 días hábiles; prorrogable por 5 días hábiles más con aviso de los motivos (art. 14).
   - **Reclamo** (rectificación, actualización, supresión, revocación): 15 días hábiles; prorrogable por 8 días hábiles más con aviso (art. 15). Si el reclamo está incompleto, se pide subsanar dentro de los 5 días siguientes; pasados 2 meses sin respuesta se entiende desistido.
4. La consulta es gratuita. Quedan registradas en la auditoría las acciones que el administrador haga en el sistema.
5. Si la solicitud no procede (por ejemplo, supresión de un registro que debe conservarse), responder por escrito con el motivo y recordar que puede acudir a la SIC.

## Consultar (acceso)

| Qué | Cómo |
|---|---|
| Datos de la cuenta | El titular los ve en «Mis datos personales», dentro de «Mi perfil»: nombre, correo, teléfono, alcance, si tiene firma guardada, último acceso, aceptación del aviso y un resumen de su actividad. El administrador puede revisar el usuario en la gestión de usuarios |
| Descarga del titular | En «Mi perfil», botón «Descargar mis datos (JSON)». El archivo no incluye la imagen de la firma |
| Entrega completa | El administrador exporta los datos del usuario desde la gestión de usuarios («Exportar datos», archivo JSON). Queda en auditoría con acción `EXPORT` |
| Actividad | Pantalla de auditoría, filtrada por el usuario, con exportación CSV. Cada exportación queda en auditoría con acción `EXPORT`, sus filtros y el rango de fechas (máximo 366 días por exportación) |
| Receptor que firma el acta | Se entrega copia del acta firmada donde aparece |
| Prueba de la autorización | Registro de aceptación del aviso: versión, fecha, IP y user agent (modelo `PrivacyConsent`). Aparece en «Mis datos personales» y en la exportación del administrador. Para el receptor del hospital, la línea de autorización bajo su firma queda en el acta firmada |

Entregar los datos por un medio seguro al correo registrado.

## Actualizar y rectificar

| Titular | Cómo |
|---|---|
| Usuario con sesión | El titular edita su nombre, teléfono y firma guardada en «Mi perfil» |
| Cambio de correo, rol o alcance | El administrador edita el usuario |
| Contacto de hospital | El administrador edita el hospital (nombre, teléfono, correo de contacto) |
| Receptor de un acta firmada | El nombre y cargo de la firma no se modifican: la firma es inmutable por diseño. Si el dato estaba mal, se emite una nota aclaratoria asociada al acta y se informa al titular |

Los cambios quedan en el registro de auditoría con el valor anterior y el nuevo.

## Suprimir

La supresión se hace por **anonimización**, no por borrado físico (RNF-COM-02, RNF-BAK-03).

1. **Cuenta de usuario**: el administrador puede anonimizar una cuenta que esté desactivada y lleve más de 730 días inactiva (`ANONYMIZE_MIN_INACTIVE_DAYS`). La fecha de referencia es la más reciente entre la desactivación, el último acceso y la creación de la cuenta; así no se anonimiza a quien acaba de salir. Al anonimizar:
   - Nombre pasa a «Usuario anonimizado»; apellido, a «#» seguido de los 8 primeros caracteres del identificador.
   - Correo pasa a `anonimizado-<identificador>@anonimizado.invalid`.
   - Teléfono y código de empleado quedan vacíos.
   - La contraseña se inutiliza (no puede volver a entrar) y la firma guardada se borra, con su archivo.
   - Se conserva el identificador para el historial. La operación queda en auditoría con acción `ANONYMIZE`.
   - Una cuenta ya anonimizada no se puede volver a anonimizar.
   - Un administrador no puede anonimizarse a sí mismo.
2. **Antes de cumplirse el plazo**: se desactiva la cuenta (ver «Revocar») y se explica al titular que la anonimización se hará al cumplirse el plazo. `A confirmar con el asesor legal si el plazo puede acortarse a solicitud del titular cuando no haya deber de conservar los datos de contacto.`
3. **Qué no se borra ni anonimiza, y por qué**:
   - **Actas y firmas en actas** (incluidos nombre, cargo y firma del receptor del hospital): son registros de mantenimiento que deben conservarse 5 años por la normativa sanitaria y las auditorías. La base de datos los protege con triggers de inmutabilidad y el bucket tiene Object Lock. Su integridad y autenticidad dependen de que no se alteren (Ley 527 de 1999).
   - **Registro de auditoría**: es append-only, se conserva 5 años como evidencia de las medidas de seguridad y para posibles disputas.
   - **OTs, fotos y hallazgos**: forman parte del historial de trazabilidad.
   - **Consentimientos del aviso (`PrivacyConsent`)**: son la prueba de la autorización y no se borran al anonimizar.
4. La ley admite la negativa a suprimir cuando exista un deber legal o contractual de permanecer en la base de datos. Se responde por escrito, indicando el fundamento y el plazo de conservación, y se limita el uso de esos datos a la trazabilidad.
5. Vencido el plazo de 5 años, el administrador y el responsable legal deciden por escrito la supresión o anonimización de esos registros.

## Revocar la autorización

1. El administrador **desactiva la cuenta** (`is_active = false`): el titular ya no puede entrar y se dejan de enviar notificaciones y correos.
2. Se quitan al titular como contacto de hospital o de destinatarios de reportes si lo era.
3. Se informa que la revocación no afecta los registros que deben conservarse (ver «Suprimir»), y se anonimiza la cuenta cuando cumpla más de 730 días inactiva.
4. En el teléfono del técnico, cerrar sesión y pedirle desinstalar o borrar los datos de la app una vez sincronizado todo.

## Presentación de quejas

Si el titular no está conforme con la respuesta, puede presentar queja ante la Superintendencia de Industria y Comercio. Incluirlo siempre en la respuesta.
