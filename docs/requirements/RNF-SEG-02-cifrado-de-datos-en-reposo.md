---
id: RNF-SEG-02
issue: 67
titulo: "Cifrado de datos en reposo"
tipo: non-functional
prioridad: must-have
modulo: seguridad
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: seguridad']
---

# RNF-SEG-02 - Cifrado de datos en reposo

### RNF-SEG-02: Cifrado de datos en reposo
**Prioridad:** M

**Descripción:**
Los datos sensibles almacenados en la infraestructura AWS deben estar cifrados en reposo para protegerlos ante accesos físicos no autorizados a los medios de almacenamiento.

**Criterios de aceptación:**
- La instancia de **AWS RDS** tiene cifrado en reposo habilitado (AES-256 mediante AWS KMS). Esto cubre la base de datos principal y todos sus backups automáticos.
- El bucket de **AWS S3** donde se almacenan fotos, PDFs y firmas tiene **SSE-S3** (Server-Side Encryption) habilitado por defecto en todos los objetos.
- Los volúmenes **EBS** de las instancias EC2/ECS tienen cifrado habilitado.
- Las **variables de entorno** con secretos (DATABASE_URL, SECRET_KEY de Django, credenciales SMTP, claves AWS) se gestionan mediante **AWS Systems Manager Parameter Store** (tipo SecureString) o **AWS Secrets Manager**, nunca en archivos `.env` commiteados al repositorio ni en texto claro en el código.
- No se almacenan contraseñas de usuarios en texto claro ni en formato reversible. Se usa **bcrypt** (mediante Django's `PBKDF2PasswordHasher` o `BCryptSHA256PasswordHasher`) con un factor de costo mínimo de 12 rondas.
