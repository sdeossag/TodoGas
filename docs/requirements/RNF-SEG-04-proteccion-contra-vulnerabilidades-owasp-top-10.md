---
id: RNF-SEG-04
issue: 69
titulo: "Protección contra vulnerabilidades OWASP Top 10"
tipo: non-functional
prioridad: must-have
modulo: seguridad
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: seguridad']
---

# RNF-SEG-04 - Protección contra vulnerabilidades OWASP Top 10

### RNF-SEG-04: Protección contra vulnerabilidades OWASP Top 10
**Prioridad:** M

**Descripción:**
El sistema implementa contramedidas contra las vulnerabilidades más comunes en aplicaciones web según el estándar OWASP Top 10 (versión 2021).

**Criterios de aceptación:**
- **A01 - Broken Access Control:** cubierto por RNF-SEG-03. Los tests automatizados de autorización son la evidencia.
- **A02 - Cryptographic Failures:** cubierto por RNF-SEG-01 y RNF-SEG-02.
- **A03 - Injection (SQL):** el ORM de Django usa consultas parametrizadas por defecto. Está prohibido el uso de `.raw()` o `cursor.execute()` con interpolación de strings sin parametrización. Revisión manual de cualquier query raw en code reviews.
- **A04 - Insecure Design:** los flujos de negocio críticos (completar OT, cambiar estado, generar PDF) son revisados en code review por al menos un revisor adicional antes de merge.
- **A05 - Security Misconfiguration:** Django en producción tiene `DEBUG=False`, `ALLOWED_HOSTS` configurado explícitamente, y las cabeceras de seguridad HTTP habilitadas: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security: max-age=31536000`, `Content-Security-Policy` configurado para el dominio.
- **A07 - Identification and Authentication Failures:** cubierto por RF-US-03 (bloqueo por intentos fallidos, JWT, política de contraseñas).
- **A08 - Software and Data Integrity Failures:** las dependencias de Python y JavaScript se gestionan con versiones fijas en `requirements.txt` y `package-lock.json`. Se usa `pip audit` y `npm audit` en el pipeline de CI para detectar dependencias con vulnerabilidades conocidas.
- **A09 - Security Logging and Monitoring Failures:** cubierto por RF-TR-01 y RNF-MAN-02.
- **A10 - Server-Side Request Forgery (SSRF):** el sistema no realiza peticiones HTTP a URLs proporcionadas por usuarios. Las únicas URLs externas son endpoints fijos configurados en variables de entorno.
