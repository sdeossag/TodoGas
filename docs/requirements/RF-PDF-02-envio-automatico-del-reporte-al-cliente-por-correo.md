---
id: RF-PDF-02
issue: 30
titulo: "Envío automático del reporte al cliente por correo"
tipo: functional
prioridad: must-have
modulo: pdf
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: pdf']
---

# RF-PDF-02 - Envío automático del reporte al cliente por correo

### RF-PDF-02: Envío automático del reporte al cliente por correo
**Prioridad:** M

**Descripción:**
Al completarse una OT y generarse el PDF, el sistema envía automáticamente el reporte al correo del hospital correspondiente.

**Criterios de aceptación:**
- El correo electrónico principal del hospital está configurado en su perfil. El `ADMIN` puede configurar hasta 3 correos adicionales de copia (CC) por hospital.
- El envío automático ocurre dentro de los **5 minutos** posteriores a la generación exitosa del PDF.
- **Contenido del correo:**
  - Asunto: `[Empresa] Reporte de servicio — OT-{número} | {Nombre del activo} | {Nombre del hospital}`
  - Cuerpo: saludo personalizado al hospital, resumen de la intervención (tipo, fecha, técnico, activo intervenido, descripción breve), indicación de que el informe completo se adjunta.
  - Adjunto: el PDF del reporte de servicio.
- Si el envío falla (correo inválido, timeout SMTP, etc.): el sistema reintenta automáticamente 3 veces con backoff exponencial (5 min, 15 min, 45 min). Si falla definitivamente, el `ADMIN` recibe una notificación de fallo con el detalle del error y puede reenviar manualmente.
- El `ADMIN` puede reenviar manualmente el PDF a cualquier correo desde la interfaz web en cualquier momento posterior.
- El sistema registra por cada envío: fecha/hora, destinatario(s), estado (enviado / fallido / reenviado manualmente), número de intento si fue reintento.
