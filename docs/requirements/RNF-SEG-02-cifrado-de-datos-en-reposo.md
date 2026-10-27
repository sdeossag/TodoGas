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

---

---

**Metadatos de importacion**
- Tipo: `Requisito no funcional`
- Fase: `2`
- Repositorio destino: `sdeossag/TodoGas`
- Categoria: `SEG - Seguridad`
- Prioridad: `M`
- Fuente: `CMMS Gases Medicinales - Fase 2: Requisitos No Funcionales`

**Implementación (revisión del 2026-10-27):**
- [x] RDS cifrado — storage_encrypted = true (clave por defecto de AWS)
- [x] S3 con SSE-S3 — AES256 en los buckets
- [ ] ~~Volúmenes EBS cifrados~~ (ya no aplica: Se usa ECS Fargate, sin EC2 ni EBS propios)
- [x] Secretos en Parameter Store — SecureString en ssm.tf; sin .env versionado
- [ ] Contraseñas con PBKDF2/bcrypt y 12 rondas — Se usa el PBKDF2 por defecto de Django; no se fijó PASSWORD_HASHERS

Commits: 45090aa
Archivos: `infra/terraform/rds.tf`, `infra/terraform/s3.tf`, `infra/terraform/ssm.tf`, `backend/config/settings/base.py`
