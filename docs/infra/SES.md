# Correo con Amazon SES

Producción manda los correos (actas, avisos de contratos y garantías,
hallazgos críticos, medidores, recuperación de contraseña) por SES.

## Variables

`EMAIL_BACKEND=django_ses.SESBackend`, `AWS_SES_REGION_NAME` (default
`us-east-1`), `DEFAULT_FROM_EMAIL="TodoGas CMMS <notificaciones@cmms.todogas.com.co>"`
y, opcional, `AWS_SES_CONFIGURATION_SET` (vacía = sin conjunto).

Sin claves: en ECS boto3 toma el rol de la tarea. El rol necesita
`ses:SendRawEmail` (y `ses:SendEmail` si algún día se usa SES v2); el limitador
de django-ses está apagado, así que no necesita `ses:GetSendQuota`. El
remitente de IAM debe permitir el identity del dominio.

Si se define `AWS_SES_CONFIGURATION_SET`, el rol también debe poder usarlo.

## Pasos manuales

1. **Identidad del dominio.** En SES (región de `AWS_SES_REGION_NAME`) crear la
   identidad `cmms.todogas.com.co` con Easy DKIM. Los 3 CNAME de DKIM los crea
   Terraform en Route 53; solo hay que esperar a que SES la marque
   "Verified".
2. **MAIL FROM personalizado.** En la identidad, activar "Custom MAIL FROM
   domain" con `mail.cmms.todogas.com.co`. Publicar en Route 53:
   - `MX mail.cmms.todogas.com.co` -> `10 feedback-smtp.<región>.amazonses.com`
   - `TXT mail.cmms.todogas.com.co` -> `"v=spf1 include:amazonses.com ~all"`
   Con esto el SPF queda alineado con el dominio y DMARC pasa por SPF y DKIM.
3. **DMARC.** `TXT _dmarc.cmms.todogas.com.co`. Empezar en observación:
   `"v=DMARC1; p=none; rua=mailto:dmarc@todogas.com.co; adkim=s; aspf=s"`.
   Tras 2-4 semanas sin fallos legítimos, subir a `p=quarantine` y luego
   `p=reject`.
4. **Salir del sandbox.** En el sandbox solo se envía a direcciones verificadas
   y hasta 200 correos al día. SES -> Account dashboard -> "Request production
   access" (misma región). Texto modelo:

   > Mail type: Transactional.
   > Website URL: https://cmms.todogas.com.co
   >
   > TodoGas CMMS is a maintenance management system for medical gas
   > installations in hospitals. We send transactional notifications only, to
   > hospital staff who are registered users of the system or contacts of the
   > hospital account: (1) service reports (PDF) when a maintenance work order
   > is approved, (2) contract and warranty expiry notices at 60 and 30 days,
   > (3) alerts when a critical finding is recorded, and (4) meter-threshold
   > and password-recovery messages. We expect about 3,000 emails per month, at
   > most a few hundred per day.
   >
   > Recipients are not purchased or imported lists: each address belongs to a
   > user or hospital contact created by an administrator. We do not send
   > marketing. Bounces and complaints are monitored through an SES
   > configuration set with SNS notifications; addresses that bounce are
   > removed from sending. Sending uses a verified domain with DKIM, a custom
   > MAIL FROM domain, SPF and DMARC.

   AWS suele responder en 24 horas. Si pide más detalle, contestar en el mismo
   caso.
5. **Probar.** Ya fuera del sandbox, enviar un acta de prueba a un correo del
   hospital y revisar en el cliente que SPF, DKIM y DMARC salgan "pass".
