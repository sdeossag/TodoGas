# Catalogo de requisitos - TodoGas CMMS

Generado desde los issues de `sdeossag/TodoGas`. Un archivo por requisito.

- **RF / RNF:** requisitos funcionales y no funcionales del alcance original y los añadidos durante el desarrollo.
- **REV:** cambios que salieron de las revisiones con el cliente y del barrido de QA.
- **OPS:** tareas de operación y puesta en marcha.

Total: 152 · Abiertos: 47 · Cerrados: 105 (actualizado el 2026-10-27).

| ID | Issue | Titulo | Tipo | Prioridad | Modulo | Estado |
|---|---|---|---|---|---|---|
| RF-AC-01 | #1 | Estructura jerárquica de activos | functional | must-have | activos | CLOSED |
| RF-AC-02 | #2 | Ficha técnica de activo | functional | must-have | activos | CLOSED |
| RF-AC-03 | #3 | Creación, edición y baja de activos | functional | must-have | activos | CLOSED |
| RF-AC-04 | #4 | Código QR único por activo | functional | must-have | activos | CLOSED |
| RF-AC-05 | #5 | Búsqueda y filtrado de activos | functional | must-have | activos | CLOSED |
| RF-AC-06 | #6 | Historial consolidado del activo | functional | must-have | activos | CLOSED |
| RF-AC-07 | #7 | Vista de activos por hospital con indicadores de estado | functional | must-have | activos | CLOSED |
| RF-OT-01 | #8 | Tipos de órdenes de trabajo | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-02 | #9 | Creación manual de OT correctiva o predictiva | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-03 | #10 | Ciclo de vida y estados de la OT | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-04 | #11 | Vistas de OT filtradas por rol | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-05 | #12 | Ejecución de OT por el técnico (app Android) | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-06 | #13 | Asignación y reasignación de técnico | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-07 | #14 | Detalle completo de OT completada | functional | must-have | ordenes-trabajo | CLOSED |
| RF-OT-08 | #15 | OT generada automáticamente desde plan preventivo | functional | must-have | ordenes-trabajo | CLOSED |
| RF-PM-01 | #16 | Creación de plan de mantenimiento | functional | must-have | planes-pm | CLOSED |
| RF-PM-02 | #17 | Calendarización automática y detección de conflictos | functional | must-have | planes-pm | CLOSED |
| RF-PM-03 | #18 | Vista de cumplimiento de planes | functional | must-have | planes-pm | CLOSED |
| RF-PM-04 | #19 | Edición y desactivación de planes | functional | should-have | planes-pm | CLOSED |
| RF-CK-01 | #20 | Constructor visual de checklists (form builder) | functional | must-have | checklists | CLOSED |
| RF-CK-02 | #21 | Versionado de plantillas de checklist | functional | must-have | checklists | CLOSED |
| RF-CK-03 | #22 | Asociación de checklists a planes y tipos de activo | functional | must-have | checklists | CLOSED |
| RF-CK-04 | #23 | Ejecución del checklist en la app Android | functional | must-have | checklists | CLOSED |
| RF-EV-01 | #24 | Captura de fotos con geolocalización y timestamp inmutables | functional | must-have | evidencia | CLOSED |
| RF-EV-02 | #25 | Galería de evidencia en la OT | functional | must-have | evidencia | CLOSED |
| RF-FD-01 | #26 | Captura de firma del técnico | functional | must-have | firma-digital | CLOSED |
| RF-FD-02 | #27 | Captura de firma del cliente/receptor | functional | must-have | firma-digital | CLOSED |
| RF-FD-03 | #28 | Cumplimiento con Ley 527 de 1999 | functional | must-have | firma-digital | CLOSED |
| RF-PDF-01 | #29 | Generación automática del reporte de servicio | functional | must-have | pdf | CLOSED |
| RF-PDF-02 | #30 | Envío automático del reporte al cliente por correo | functional | must-have | pdf | CLOSED |
| RF-PDF-03 | #31 | Generación de reporte consolidado por período | functional | should-have | pdf | OPEN |
| RF-TR-01 | #32 | Log de auditoría inmutable y completo | functional | must-have | trazabilidad | CLOSED |
| RF-TR-02 | #33 | Historial de cambios por entidad (timeline) | functional | must-have | trazabilidad | CLOSED |
| RF-TR-03 | #34 | Integridad e inmutabilidad de OTs completadas | functional | must-have | trazabilidad | CLOSED |
| RF-US-01 | #35 | Gestión del ciclo de vida de usuarios | functional | must-have | usuarios-roles | CLOSED |
| RF-US-02 | #36 | Matriz de permisos por rol | functional | must-have | usuarios-roles | CLOSED |
| RF-US-03 | #37 | Autenticación segura y gestión de sesiones | functional | must-have | usuarios-roles | CLOSED |
| RF-US-04 | #38 | Onboarding y recuperación de acceso | functional | must-have | usuarios-roles | CLOSED |
| RF-BI-01 | #39 | Dashboard ejecutivo del ADMIN | functional | must-have | dashboard-bi | OPEN |
| RF-BI-02 | #40 | KPIs avanzados: MTBF y costos | functional | should-have | dashboard-bi | OPEN |
| RF-BI-03 | #41 | Reporte mensual automático de cumplimiento para clientes | functional | should-have | dashboard-bi | OPEN |
| RF-IN-01 | #42 | Catálogo de repuestos e insumos | functional | must-have | inventario | CLOSED |
| RF-IN-02 | #43 | Registro de entradas de stock | functional | must-have | inventario | CLOSED |
| RF-IN-03 | #44 | Registro de salidas de stock vinculadas a OTs | functional | must-have | inventario | CLOSED |
| RF-IN-04 | #45 | Alertas de stock mínimo | functional | must-have | inventario | CLOSED |
| RF-OF-01 | #46 | Sincronización inicial de datos al conectarse | functional | must-have | offline | OPEN |
| RF-OF-02 | #47 | Ejecución completa de OT en modo offline | functional | must-have | offline | OPEN |
| RF-OF-03 | #48 | Sincronización automática al recuperar conexión | functional | must-have | offline | OPEN |
| RF-CL-01 | #49 | Acceso seguro al portal del cliente | functional | must-have | portal-cliente | CLOSED |
| RF-CL-02 | #50 | Vista de activos y estado de mantenimiento del cliente | functional | must-have | portal-cliente | CLOSED |
| RF-CL-03 | #51 | Historial de OTs y descarga de reportes | functional | must-have | portal-cliente | CLOSED |
| RF-MI-01 | #52 | Migración de hospitales (clientes) | functional | must-have | migracion | OPEN |
| RF-MI-02 | #53 | Migración de activos | functional | must-have | migracion | CLOSED |
| RF-MI-03 | #54 | Migración de historial de OTs | functional | must-have | migracion | OPEN |
| RF-MI-04 | #55 | Validación y rollback de la migración | functional | must-have | migracion | OPEN |
| RF-NT-01 | #56 | Notificaciones push a técnicos (FCM) | functional | must-have | notificaciones | CLOSED |
| RF-NT-02 | #57 | Alertas por correo al ADMIN | functional | must-have | notificaciones | CLOSED |
| RF-NT-03 | #58 | Notificación de nueva OT al técnico por correo | functional | must-have | notificaciones | CLOSED |
| RF-CK-05 | #120 | Bloques repetibles en el checklist | functional | must-have | checklists | CLOSED |
| RF-CK-06 | #121 | Respuesta Sí/No/N/A en el checklist | functional | should-have | checklists | CLOSED |
| RF-CK-07 | #122 | Puntos pendientes con motivo y corrección del checklist con la OT en curso | functional | must-have | checklists | CLOSED |
| RF-HA-01 | #123 | Registro de hallazgos desde campo, también sin red | functional | must-have | hallazgos | CLOSED |
| RF-HA-02 | #124 | Bandeja del planificador y aviso al hospital por hallazgo crítico | functional | must-have | notificaciones, hallazgos | CLOSED |
| RF-CT-01 | #125 | Contratos de mantenimiento y garantías con vigencia y avisos | functional | should-have | contratos | CLOSED |
| RF-PM-05 | #126 | Catálogo configurable de tipos de tarea | functional | should-have | planes-pm | CLOSED |
| RF-PM-06 | #127 | Protocolo asignable a una ubicación | functional | must-have | planes-pm | CLOSED |
| RF-PM-07 | #128 | Fecha de inicio al asignar un protocolo | functional | must-have | planes-pm | CLOSED |
| RF-AC-08 | #129 | Dirección y mapa en activos y ubicaciones | functional | should-have | activos | CLOSED |
| RF-AC-09 | #130 | Baja y reactivación masiva de activos | functional | should-have | activos | CLOSED |
| RF-US-05 | #131 | Alcance de cada usuario por hospital y ubicación | functional | must-have | usuarios-roles, seguridad | CLOSED |
| RF-FD-04 | #132 | Firma guardada por usuario, usable sin red | functional | must-have | firma-digital | CLOSED |
| RF-FD-05 | #133 | Firma de validación del supervisor al aprobar | functional | must-have | firma-digital, pdf | CLOSED |
| RF-CL-04 | #134 | Portal del hospital: historial por equipo, próximos mantenimientos y cumplimiento | functional | must-have | portal-cliente | CLOSED |
| RF-PDF-04 | #135 | Reenvío de varias actas por correo con los PDF adjuntos | functional | should-have | pdf, notificaciones | CLOSED |
| RF-PDF-05 | #136 | Acta legible: un cuadro por activo y sin campos vacíos | functional | must-have | pdf | CLOSED |
| RF-OF-04 | #137 | Aprobación y cambios de estado sin red con la hora del teléfono | functional | must-have | offline | CLOSED |
| RF-EV-03 | #138 | Fotos sin límite y galería con carga diferida | functional | must-have | evidencia | CLOSED |
| RNF-REN-01 | #59 | Tiempos de respuesta del API (backend) | non-functional | must-have | rendimiento | OPEN |
| RNF-REN-02 | #60 | Tiempos de carga de la interfaz web | non-functional | must-have | rendimiento | OPEN |
| RNF-REN-03 | #61 | Rendimiento de la app Android en dispositivos de gama media | non-functional | must-have | rendimiento | CLOSED |
| RNF-REN-04 | #62 | Rendimiento de la sincronización offline | non-functional | should-have | rendimiento | CLOSED |
| RNF-DIS-01 | #63 | SLA de disponibilidad del sistema web | non-functional | must-have | disponibilidad | OPEN |
| RNF-DIS-02 | #64 | Recuperación ante fallos (RTO y RPO) | non-functional | must-have | disponibilidad | OPEN |
| RNF-DIS-03 | #65 | Manejo de errores y degradación elegante | non-functional | must-have | disponibilidad | OPEN |
| RNF-SEG-01 | #66 | Seguridad en el transporte de datos | non-functional | must-have | seguridad | CLOSED |
| RNF-SEG-02 | #67 | Cifrado de datos en reposo | non-functional | must-have | seguridad | OPEN |
| RNF-SEG-03 | #68 | Control de acceso y autorización a nivel de datos | non-functional | must-have | seguridad | CLOSED |
| RNF-SEG-04 | #69 | Protección contra vulnerabilidades OWASP Top 10 | non-functional | must-have | seguridad | OPEN |
| RNF-SEG-05 | #70 | Seguridad del APK de distribución fuera de Play Store | non-functional | must-have | seguridad | CLOSED |
| RNF-SEG-06 | #71 | Gestión de secretos y separación de entornos | non-functional | must-have | seguridad | CLOSED |
| RNF-ESC-01 | #72 | Capacidad de crecimiento sin rediseño arquitectural | non-functional | should-have | escalabilidad | OPEN |
| RNF-ESC-02 | #73 | Optimización de base de datos para el volumen proyectado | non-functional | must-have | escalabilidad | OPEN |
| RNF-USA-01 | #74 | Diseño para condiciones de campo adversas | non-functional | must-have | usabilidad | OPEN |
| RNF-USA-02 | #75 | Gestión de errores de conectividad en la app | non-functional | must-have | usabilidad | OPEN |
| RNF-USA-03 | #76 | Flujos optimizados para rapidez de uso | non-functional | should-have | usabilidad | OPEN |
| RNF-USA-04 | #77 | Usabilidad del portal web para ADMIN y SUP | non-functional | should-have | usabilidad | OPEN |
| RNF-COM-01 | #78 | Trazabilidad para auditorías GMP/BPM (INVIMA) | non-functional | must-have | cumplimiento-legal | OPEN |
| RNF-COM-02 | #79 | Cumplimiento Ley 1581 de 2012 (Protección de Datos Personales — Habeas Data) | non-functional | must-have | cumplimiento-legal | OPEN |
| RNF-COM-03 | #80 | Firma electrónica — Ley 527 de 1999 | non-functional | must-have | cumplimiento-legal | CLOSED |
| RNF-COM-04 | #81 | Retención y disponibilidad de registros para auditoría | non-functional | must-have | cumplimiento-legal | CLOSED |
| RNF-AND-01 | #82 | Versiones de Android soportadas | non-functional | must-have | android | OPEN |
| RNF-AND-02 | #83 | Tamaños de pantalla y resoluciones | non-functional | must-have | android | OPEN |
| RNF-AND-03 | #84 | Distribución del APK fuera de Play Store | non-functional | must-have | android | CLOSED |
| RNF-AND-04 | #85 | Almacenamiento local y permisos | non-functional | must-have | android | CLOSED |
| RNF-PDF-01 | #86 | Tiempos de generación de PDF | non-functional | must-have | pdf | OPEN |
| RNF-PDF-02 | #87 | Calidad y fidelidad de los PDFs | non-functional | must-have | pdf | OPEN |
| RNF-PDF-03 | #88 | Librería y tecnología de generación | non-functional | must-have | pdf | OPEN |
| RNF-BAK-01 | #89 | Política de backups de la base de datos | non-functional | must-have | backup-retencion | OPEN |
| RNF-BAK-02 | #90 | Política de respaldo de archivos (S3) | non-functional | must-have | backup-retencion | OPEN |
| RNF-BAK-03 | #91 | Retención de datos históricos | non-functional | must-have | backup-retencion | OPEN |
| RNF-MAN-01 | #92 | Estructura y calidad del código | non-functional | must-have | mantenibilidad | CLOSED |
| RNF-MAN-02 | #93 | Monitoreo y observabilidad en producción | non-functional | must-have | mantenibilidad | CLOSED |
| RNF-MAN-03 | #94 | Pipeline de CI/CD | non-functional | must-have | mantenibilidad | CLOSED |
| RNF-MAN-04 | #95 | Gestión de migraciones de base de datos | non-functional | must-have | mantenibilidad | CLOSED |
| REV-01 | #96 | Protocolo por activo: el checklist debe colgar del activo, no del plan | functional | must-have | planes-pm | CLOSED |
| REV-02 | #97 | Un protocolo debe poder contener varias checklists | functional | must-have | checklists | CLOSED |
| REV-03 | #98 | Una OT debe poder cubrir varios activos, cada uno con su protocolo | functional | must-have | ordenes-trabajo | CLOSED |
| REV-04 | #99 | La generación de preventivos debe poder ser manual, y hay que definir qué pasa con las no ejecutadas | functional | must-have | planes-pm | CLOSED |
| REV-05 | #100 | Interfaz para gestionar el árbol de ubicaciones dentro de cada hospital | functional | must-have | activos | CLOSED |
| REV-06 | #101 | Seleccionar activos filtrando por ubicación al crear una OT | functional | must-have | ordenes-trabajo | CLOSED |
| REV-07 | #102 | Historial de intervenciones por activo, con regeneración del acta | functional | must-have | trazabilidad | CLOSED |
| REV-08 | #103 | Las lecturas de medidor deben quedar asociadas al activo, no solo a la OT | functional | should-have | activos | CLOSED |
| REV-09 | #104 | Permisos por usuario, además de por rol | functional | must-have | usuarios-roles | CLOSED |
| REV-10 | #105 | El administrador debe poder iniciar y diligenciar checklists | functional | must-have | usuarios-roles | CLOSED |
| REV-19 | #106 | El administrador debe poder corregir checklist y evidencia mientras la OT está en revisión | functional | should-have | ordenes-trabajo | CLOSED |
| REV-11 | #107 | Configurar qué campos aparecen en el acta PDF | functional | should-have | pdf | CLOSED |
| REV-12 | #108 | La ubicación física debe ser obligatoria en el acta, no solo el GPS | functional | must-have | pdf | CLOSED |
| REV-13 | #109 | Poder añadir texto descriptivo a cada foto de evidencia | functional | should-have | evidencia | CLOSED |
| REV-14 | #110 | Comprimir las fotos preservando calidad suficiente para auditoría | functional | must-have | evidencia | CLOSED |
| REV-15 | #111 | Filtrar el inventario por ubicación e institución | functional | must-have | inventario | OPEN |
| REV-16 | #112 | Definir el comportamiento al desactivar activos, ubicaciones y planes | functional | must-have | trazabilidad | OPEN |
| REV-17 | #113 | Definir la gobernanza de códigos de activo y corregir el generador | functional | should-have | activos | CLOSED |
| REV-18 | #114 | Permitir editar la fecha de intervención de una OT | functional | could-have | ordenes-trabajo | CLOSED |
| REV-20 | #115 | Ampliar el dashboard con los indicadores que el cliente espera | functional | could-have | dashboard-bi | OPEN |
| REV-21 | #116 | Un usuario Cliente puede quedarse sin hospital y ver un portal vacío | bug | should-have | usuarios-roles | CLOSED |
| REV-22 | #117 | `restrict_to_hospital` de los planes PM no se aplica en ningún sitio | bug | should-have | planes-pm | CLOSED |
| REV-23 | #118 | El costo total de la OT siempre queda en $0 | bug | should-have | inventario | CLOSED |
| REV-24 | #119 | El aviso de requisitos para enviar a revisión no se recalcula | bug | could-have | ordenes-trabajo | CLOSED |
| REV-25 | #139 | Campo libre tipo «Otro» en el activo | functional | could-have | activos | OPEN |
| REV-26 | #140 | Campos obligatorios del activo configurables por el administrador | functional | could-have | activos | OPEN |
| REV-27 | #141 | Elegir qué fechas y horas salen en el acta | functional | must-have | pdf | OPEN |
| REV-28 | #142 | Numeración y nombre del acta para el empalme con Fracttal | functional | could-have | pdf | OPEN |
| REV-29 | #143 | Renombrar «Inventario» como «Almacén» | functional | could-have | inventario | OPEN |
| REV-30 | #144 | Quitar la columna «Costo unit.» de los repuestos de la OT | chore | could-have | ordenes-trabajo | CLOSED |
| REV-31 | #145 | El reporte consolidado anuncia un correo que nunca se envía | bug | should-have | pdf | CLOSED |
| OPS-01 | #146 | Desplegar la infraestructura en AWS y delegar el subdominio en el DNS | chore | must-have | disponibilidad | OPEN |
| OPS-02 | #147 | Importar el catálogo completo y los Planes de Tareas desde Fracttal | chore | must-have | migracion | OPEN |
| OPS-03 | #148 | Prueba en teléfono real: firma guardada, pendientes y aprobación sin red | chore | must-have | offline | OPEN |
| OPS-04 | #149 | Verificar el bloqueo por intentos fallidos de inicio de sesión | chore | should-have | seguridad | CLOSED |
| OPS-05 | #150 | Guía de mantenimiento no técnica para la entrega | chore | should-have | mantenibilidad | OPEN |
| OPS-06 | #151 | Manual de uso completo y detallado | chore | must-have | usabilidad | OPEN |
| OPS-07 | #152 | Manual de uso rápido | chore | must-have | usabilidad | OPEN |
