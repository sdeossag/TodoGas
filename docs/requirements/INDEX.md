# Catalogo de requisitos - TodoGas CMMS

Generado desde los issues de `sdeossag/TodoGas`. Un archivo por requisito.

| ID | Titulo | Tipo | Prioridad | Modulo | Estado |
|---|---|---|---|---|---|
| RF-AC-01 | Estructura jerárquica de activos | functional | must-have | activos | CLOSED |
| RF-AC-02 | Ficha técnica de activo | functional | must-have | activos | CLOSED |
| RF-AC-03 | Creación, edición y baja de activos | functional | must-have | activos | CLOSED |
| RF-AC-04 | Código QR único por activo | functional | must-have | activos | CLOSED |
| RF-AC-05 | Búsqueda y filtrado de activos | functional | must-have | activos | CLOSED |
| RF-AC-06 | Historial consolidado del activo | functional | must-have | activos | CLOSED |
| RF-AC-07 | Vista de activos por hospital con indicadores de estado | functional | must-have | activos | CLOSED |
| RF-OT-01 | Tipos de órdenes de trabajo | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-02 | Creación manual de OT correctiva o predictiva | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-03 | Ciclo de vida y estados de la OT | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-04 | Vistas de OT filtradas por rol | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-05 | Ejecución de OT por el técnico (app Android) | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-06 | Asignación y reasignación de técnico | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-07 | Detalle completo de OT completada | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-08 | OT generada automáticamente desde plan preventivo | functional | must-have | ordenes-trabajo | OPEN |
| RF-PM-01 | Creación de plan de mantenimiento | functional | must-have | planes-pm | CLOSED |
| RF-PM-02 | Calendarización automática y detección de conflictos | functional | must-have | planes-pm | CLOSED |
| RF-PM-03 | Vista de cumplimiento de planes | functional | must-have | planes-pm | CLOSED |
| RF-PM-04 | Edición y desactivación de planes | functional | should-have | planes-pm | CLOSED |
| RF-CK-01 | Constructor visual de checklists (form builder) | functional | must-have | checklists | CLOSED |
| RF-CK-02 | Versionado de plantillas de checklist | functional | must-have | checklists | CLOSED |
| RF-CK-03 | Asociación de checklists a planes y tipos de activo | functional | must-have | checklists | CLOSED |
| RF-CK-04 | Ejecución del checklist en la app Android | functional | must-have | checklists | CLOSED |
| RF-EV-01 | Captura de fotos con geolocalización y timestamp inmutables | functional | must-have | evidencia | CLOSED |
| RF-EV-02 | Galería de evidencia en la OT | functional | must-have | evidencia | CLOSED |
| RF-FD-01 | Captura de firma del técnico | functional | must-have | firma-digital | CLOSED |
| RF-FD-02 | Captura de firma del cliente/receptor | functional | must-have | firma-digital | CLOSED |
| RF-FD-03 | Cumplimiento con Ley 527 de 1999 | functional | must-have | firma-digital | CLOSED |
| RF-PDF-01 | Generación automática del reporte de servicio | functional | must-have | pdf | CLOSED |
| RF-PDF-02 | Envío automático del reporte al cliente por correo | functional | must-have | pdf | CLOSED |
| RF-PDF-03 | Generación de reporte consolidado por período | functional | should-have | pdf | OPEN |
| RF-TR-01 | Log de auditoría inmutable y completo | functional | must-have | trazabilidad | CLOSED |
| RF-TR-02 | Historial de cambios por entidad (timeline) | functional | must-have | trazabilidad | CLOSED |
| RF-TR-03 | Integridad e inmutabilidad de OTs completadas | functional | must-have | trazabilidad | CLOSED |
| RF-US-01 | Gestión del ciclo de vida de usuarios | functional | must-have | usuarios-roles | CLOSED |
| RF-US-02 | Matriz de permisos por rol | functional | must-have | usuarios-roles | CLOSED |
| RF-US-03 | Autenticación segura y gestión de sesiones | functional | must-have | usuarios-roles | CLOSED |
| RF-US-04 | Onboarding y recuperación de acceso | functional | must-have | usuarios-roles | CLOSED |
| RF-BI-01 | Dashboard ejecutivo del ADMIN | functional | must-have | dashboard-bi | OPEN |
| RF-BI-02 | KPIs avanzados: MTBF y costos | functional | should-have | dashboard-bi | OPEN |
| RF-BI-03 | Reporte mensual automático de cumplimiento para clientes | functional | should-have | dashboard-bi | OPEN |
| RF-IN-01 | Catálogo de repuestos e insumos | functional | must-have | inventario | CLOSED |
| RF-IN-02 | Registro de entradas de stock | functional | must-have | inventario | CLOSED |
| RF-IN-03 | Registro de salidas de stock vinculadas a OTs | functional | must-have | inventario | CLOSED |
| RF-IN-04 | Alertas de stock mínimo | functional | must-have | inventario | CLOSED |
| RF-OF-01 | Sincronización inicial de datos al conectarse | functional | must-have | offline | OPEN |
| RF-OF-02 | Ejecución completa de OT en modo offline | functional | must-have | offline | OPEN |
| RF-OF-03 | Sincronización automática al recuperar conexión | functional | must-have | offline | OPEN |
| RF-CL-01 | Acceso seguro al portal del cliente | functional | must-have | portal-cliente | CLOSED |
| RF-CL-02 | Vista de activos y estado de mantenimiento del cliente | functional | must-have | portal-cliente | CLOSED |
| RF-CL-03 | Historial de OTs y descarga de reportes | functional | must-have | portal-cliente | CLOSED |
| RF-MI-01 | Migración de hospitales (clientes) | functional | must-have | migracion | OPEN |
| RF-MI-02 | Migración de activos | functional | must-have | migracion | OPEN |
| RF-MI-03 | Migración de historial de OTs | functional | must-have | migracion | OPEN |
| RF-MI-04 | Validación y rollback de la migración | functional | must-have | migracion | OPEN |
| RF-NT-01 | Notificaciones push a técnicos (FCM) | functional | must-have | notificaciones | CLOSED |
| RF-NT-02 | Alertas por correo al ADMIN | functional | must-have | notificaciones | CLOSED |
| RF-NT-03 | Notificación de nueva OT al técnico por correo | functional | must-have | notificaciones | CLOSED |
| RNF-REN-01 | Tiempos de respuesta del API (backend) | non-functional | must-have | rendimiento | OPEN |
| RNF-REN-02 | Tiempos de carga de la interfaz web | non-functional | must-have | rendimiento | OPEN |
| RNF-REN-03 | Rendimiento de la app Android en dispositivos de gama media | non-functional | must-have | rendimiento | CLOSED |
| RNF-REN-04 | Rendimiento de la sincronización offline | non-functional | should-have | rendimiento | CLOSED |
| RNF-DIS-01 | SLA de disponibilidad del sistema web | non-functional | must-have | disponibilidad | OPEN |
| RNF-DIS-02 | Recuperación ante fallos (RTO y RPO) | non-functional | must-have | disponibilidad | OPEN |
| RNF-DIS-03 | Manejo de errores y degradación elegante | non-functional | must-have | disponibilidad | OPEN |
| RNF-SEG-01 | Seguridad en el transporte de datos | non-functional | must-have | seguridad | CLOSED |
| RNF-SEG-02 | Cifrado de datos en reposo | non-functional | must-have | seguridad | OPEN |
| RNF-SEG-03 | Control de acceso y autorización a nivel de datos | non-functional | must-have | seguridad | CLOSED |
| RNF-SEG-04 | Protección contra vulnerabilidades OWASP Top 10 | non-functional | must-have | seguridad | OPEN |
| RNF-SEG-05 | Seguridad del APK de distribución fuera de Play Store | non-functional | must-have | seguridad | CLOSED |
| RNF-SEG-06 | Gestión de secretos y separación de entornos | non-functional | must-have | seguridad | CLOSED |
| RNF-ESC-01 | Capacidad de crecimiento sin rediseño arquitectural | non-functional | should-have | escalabilidad | OPEN |
| RNF-ESC-02 | Optimización de base de datos para el volumen proyectado | non-functional | must-have | escalabilidad | OPEN |
| RNF-USA-01 | Diseño para condiciones de campo adversas | non-functional | must-have | usabilidad | OPEN |
| RNF-USA-02 | Gestión de errores de conectividad en la app | non-functional | must-have | usabilidad | OPEN |
| RNF-USA-03 | Flujos optimizados para rapidez de uso | non-functional | should-have | usabilidad | OPEN |
| RNF-USA-04 | Usabilidad del portal web para ADMIN y SUP | non-functional | should-have | usabilidad | OPEN |
| RNF-COM-01 | Trazabilidad para auditorías GMP/BPM (INVIMA) | non-functional | must-have | cumplimiento-legal | OPEN |
| RNF-COM-02 | Cumplimiento Ley 1581 de 2012 (Protección de Datos Personales — Habeas Data) | non-functional | must-have | cumplimiento-legal | OPEN |
| RNF-COM-03 | Firma electrónica — Ley 527 de 1999 | non-functional | must-have | cumplimiento-legal | OPEN |
| RNF-COM-04 | Retención y disponibilidad de registros para auditoría | non-functional | must-have | cumplimiento-legal | OPEN |
| RNF-AND-01 | Versiones de Android soportadas | non-functional | must-have | android | OPEN |
| RNF-AND-02 | Tamaños de pantalla y resoluciones | non-functional | must-have | android | OPEN |
| RNF-AND-03 | Distribución del APK fuera de Play Store | non-functional | must-have | android | CLOSED |
| RNF-AND-04 | Almacenamiento local y permisos | non-functional | must-have | android | CLOSED |
| RNF-PDF-01 | Tiempos de generación de PDF | non-functional | must-have | pdf | OPEN |
| RNF-PDF-02 | Calidad y fidelidad de los PDFs | non-functional | must-have | pdf | OPEN |
| RNF-PDF-03 | Librería y tecnología de generación | non-functional | must-have | pdf | OPEN |
| RNF-BAK-01 | Política de backups de la base de datos | non-functional | must-have | backup-retencion | OPEN |
| RNF-BAK-02 | Política de respaldo de archivos (S3) | non-functional | must-have | backup-retencion | OPEN |
| RNF-BAK-03 | Retención de datos históricos | non-functional | must-have | backup-retencion | OPEN |
| RNF-MAN-01 | Estructura y calidad del código | non-functional | must-have | mantenibilidad | CLOSED |
| RNF-MAN-02 | Monitoreo y observabilidad en producción | non-functional | must-have | mantenibilidad | CLOSED |
| RNF-MAN-03 | Pipeline de CI/CD | non-functional | must-have | mantenibilidad | CLOSED |
| RNF-MAN-04 | Gestión de migraciones de base de datos | non-functional | must-have | mantenibilidad | CLOSED |
