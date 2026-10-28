# Inventario de datos personales

Responsable del tratamiento: `[RAZÓN SOCIAL]`, NIT `[NIT]`. Elaborado a partir de los modelos del backend (`backend/apps/*/models.py`), la app móvil (`frontend/src/db`), la configuración de producción y `infra/terraform`. Fecha de revisión: 2026-10-28.

Abreviaturas: BD = base de datos PostgreSQL (RDS); S3 = bucket de evidencia con Object Lock; Tel = base SQLite local de la app Android.

## 1. Usuario interno (administrador y supervisor)

| Aspecto | Detalle |
|---|---|
| Datos | Nombre y apellido, correo (es el login), teléfono, cédula o código de empleado, rol, hospital/nodo de alcance, contraseña (solo hash), firma guardada (imagen y hash), aceptación del aviso de privacidad (versión, fecha, IP y user agent, `PrivacyConsent`), IP y user agent de sus acciones (auditoría), notificaciones recibidas |
| Fuente | El propio titular o el administrador al crear el usuario |
| Finalidad | Autenticación, control de acceso, asignación y aprobación de OTs, trazabilidad de acciones, validación de actas |
| Base | Autorización del titular (onboarding) y relación laboral o contractual; trazabilidad por obligación legal y sanitaria |
| Dónde | BD (`users_user`, `users_privacyconsent`, `evidence_usersignature`, `audit_auditlog`, `notifications_notificationlog`); S3 (imagen de la firma); Tel (firma local para uso sin red) |
| Quién accede | Administradores; el propio titular (su perfil, sus datos personales y su firma). La firma guardada solo la ve y usa su dueña |
| Retención | Activos: vigencia de la relación + 2 años. Inactivos: 2 años desde la desactivación (RNF-BAK-03). Auditoría y firmas ya aplicadas en actas: 5 años |
| Supresión | Anonimización por el administrador de una cuenta desactivada con más de 730 días de inactividad: reemplaza nombre, apellido, correo, teléfono y código de empleado, inutiliza la contraseña y borra la firma guardada (con su archivo). El titular puede borrar su firma guardada en cualquier momento; las copias en actas no se tocan. El consentimiento del aviso y la auditoría se conservan |

## 2. Técnico

| Aspecto | Detalle |
|---|---|
| Datos | Los de usuario interno, más: fotos de evidencia con GPS y hora (`Photo.latitude/longitude/taken_at`), firma del técnico en cada acta (`Signature`, con ubicación y hora de firma), respuestas del checklist, hallazgos reportados, lecturas de medidores, horas de ejecución |
| Fuente | El técnico desde la app (con o sin red) |
| Finalidad | Evidenciar la ejecución del mantenimiento, cumplir registros sanitarios, auditar y calcular horas y ejecutor reales |
| Base | Autorización y relación laboral; obligación legal de conservar registros de mantenimiento |
| Dónde | BD; S3 (fotos y firmas); Tel (SQLite con respuestas, fotos en cola y firmas hasta sincronizar; firma guardada) |
| Quién accede | Administradores y supervisores del alcance; el hospital ve las actas y hallazgos de su alcance; el técnico ve lo suyo |
| Retención | Actas, fotos y firmas: 5 años (Object Lock). Datos del teléfono: hasta sincronizar y hasta cerrar sesión o desinstalar |
| Supresión | Anonimización de la cuenta (nombre, correo, teléfono, código de empleado). Fotos, firmas en actas y auditoría no se borran ni se anonimizan por estar vinculadas a registros auditables |

## 3. Cuenta de hospital (cliente externo, solo lectura)

| Aspecto | Detalle |
|---|---|
| Datos | Nombre, correo, teléfono, hospital y nodo de alcance, contraseña (hash), IP y user agent de sus accesos |
| Fuente | El administrador, a solicitud del hospital |
| Finalidad | Consultar actas, hallazgos, historial y vigencia de contratos de su alcance |
| Base | Autorización del titular; ejecución del contrato con el hospital |
| Dónde | BD (`users_user`, `audit_auditlog`) |
| Quién accede | Administradores; el titular |
| Retención | Vigencia del contrato + 2 años; inactivos 2 años desde la desactivación |
| Supresión | Desactivar la cuenta (revocar) y anonimizar al pasar de 730 días de inactividad |

## 4. Receptor que firma el acta (personal del hospital)

| Aspecto | Detalle |
|---|---|
| Datos | Nombre (`signer_name`), cargo (`signer_role`), firma manuscrita digitalizada (imagen y hash), fecha y hora, ubicación aproximada del dispositivo al firmar |
| Fuente | El propio receptor, firmando en el teléfono del técnico |
| Finalidad | Constancia de recibido a conformidad del trabajo; prueba ante auditorías hospitalarias y de INVIMA |
| Base | Autorización expresa al firmar; obligación de conservar el registro de mantenimiento; la firma electrónica se rige por la Ley 527 de 1999 |
| Dónde | BD (`evidence_signature`, protegida por triggers de inmutabilidad); S3 (imagen); Tel (hasta sincronizar). La firma del receptor no se guarda como firma reutilizable |
| Quién accede | Administradores, supervisores, cuentas del hospital con alcance sobre la OT; aparece en el PDF del acta |
| Retención | 5 años mínimo (Object Lock en S3) |
| Supresión | No se anonimiza ni se borra mientras el acta sea un registro auditable. La tensión con Habeas Data se documenta en la política. Pasado el plazo, solo con decisión escrita del administrador y del responsable legal |

## 5. Contacto de hospital o de contrato

| Aspecto | Detalle |
|---|---|
| Datos | Nombre, teléfono y correo de contacto del hospital (`Hospital.contact_*`); destinatarios de reportes enviados por correo (`ReportSendLog.recipient_email`, `recipient_name`) |
| Fuente | El administrador, según información del hospital |
| Finalidad | Comunicación operativa, envío de actas y reportes consolidados, avisos de vencimiento de contratos y garantías, hallazgos críticos |
| Base | Autorización del titular o del hospital; ejecución del contrato |
| Dónde | BD; correo transaccional por AWS SES |
| Quién accede | Administradores; los PDF enviados llegan al destinatario |
| Retención | Vigencia del contrato + 2 años; registro de envíos: 5 años junto con el reporte |
| Supresión | Rectificar o vaciar el campo del contacto. El registro de envío conserva el correo como parte de la trazabilidad (anonimizar cuando proceda) |

## Datos transversales

| Dato | Dónde | Notas |
|---|---|---|
| Auditoría: usuario, IP, user agent, cambios (`changes` JSON) | BD (`audit_auditlog`, append-only) | 5 años. No se edita ni borra. Lo que guarda `changes`: en escrituras del API, solo método, código de estado y si falló (el cuerpo de la petición no se guarda, así que no hay contraseñas ni tokens); en intentos de inicio de sesión, el correo y el resultado; en exportaciones, los filtros y el rango; en exportaciones de datos personales, si la exportación era del propio usuario; en anonimizaciones, los nombres de los campos reemplazados (no sus valores) |
| Exportación CSV de auditoría | Descarga del administrador; queda registrada como acción `EXPORT` | Contiene IP y usuarios: tratar el archivo como confidencial. Rango máximo de 366 días por exportación |
| Exportación de datos personales (JSON) | Descarga del titular desde «Mi perfil» o del administrador desde la gestión de usuarios; la del administrador queda como `EXPORT` | No incluye la imagen de la firma |
| Notificaciones (push, correo, in-app) | BD (`notifications_notificationlog`) | El envío push (FCM) es hoy un marcador sin proveedor real; si se activa, FCM será encargado y se guardará un token de dispositivo (actualizar este inventario) |
| Logs de aplicación | CloudWatch Logs, retención configurable (`log_retencion_dias`, 30 por defecto) | Pueden contener IP y correos; evitar registrar datos personales |
| Sentry (errores) | Proveedor externo, solo si hay `SENTRY_DSN` | `send_default_pii=False`: no se envían usuarios, IP, cookies ni cabeceras |
| Backups RDS | AWS | 30 días rodantes (`backup_retention_dias`); dumps semanales 90 días según RNF-BAK-03 (A confirmar) |

## Datos de especial cuidado

El sistema no recopila datos sensibles en sentido estricto del artículo 5 de la Ley 1581 (salud, origen racial, datos biométricos, etc.): los hospitales y sus equipos no implican historias clínicas ni datos de pacientes. Aun así, estos datos merecen cuidado adicional:

- **Firma manuscrita digitalizada**: es un trazo personal que permite identificar a la persona y suplantarla si se filtra. No se usa como biometría de identificación automática, pero se protege como si lo fuera: acceso restringido, bucket cifrado, la firma guardada solo la usa su dueña y la del receptor no se reutiliza. El asesor legal debe confirmar la clasificación.
- **Ubicación (GPS)** de fotos y firmas: revela dónde estaba el técnico o el receptor. Se trata para probar que el trabajo se hizo en el sitio. Se debe informar al titular; no se recolecta de forma continua, solo al capturar la foto o la firma.
- **IP y user agent**: identifican dispositivo y conexión; se guardan solo por seguridad y trazabilidad.
- **Cédula o código de empleado**: dato de identificación; recopilarlo solo cuando sea necesario.

El sistema es de uso laboral; no se tratan datos de niños, niñas o adolescentes.

## A confirmar por el cliente

- Si guarda cédula en `employee_code` o solo un código interno.
- Plazos de retención definitivos y modo del Object Lock (`GOVERNANCE` por defecto en `object_lock_mode`; `COMPLIANCE` lo hace irrevocable).
- Región de AWS y proveedores efectivos (AWS, Sentry si se activa, FCM si se activa).
- Si la empresa actúa como responsable o como encargada frente a los datos de cada hospital, según el contrato con él.
