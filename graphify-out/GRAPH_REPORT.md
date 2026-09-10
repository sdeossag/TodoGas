# Graph Report - TodoGas-develop  (2026-09-01)

## Corpus Check
- 366 files · ~121,468 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2386 nodes · 4606 edges · 220 communities (123 shown, 46 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 325 edges (avg confidence: 0.91)
- Token cost: 503,110 input · 0 output

## Community Hubs (Navigation)
- Evidencia: Fotos y Firmas
- Cumplimiento Legal y Atributos de Calidad
- Cliente API: Checklists y OTs
- Generacion de Reportes PDF
- CI/CD y Plantillas de Reporte
- Frontend de Activos
- Tests de Vistas de OT
- Sistema de Diseno y Layouts
- Modelo de Inventario
- Frontend de Planes de Mantenimiento
- Frontend de Usuarios y Auditoria
- Frontend de Reportes y Portal Cliente
- Frontend de Dashboard y KPIs
- Tests de Usuarios y Contrasenas
- Frontend de Inventario
- Modelo de Orden de Trabajo
- Correos y Serializers de Usuario
- Tests de Inventario
- Notificaciones Push y Correo
- Tests de Autenticacion
- Requisitos de PDF y Notificaciones
- Modelo de Checklists
- Modelo de Activos y Jerarquia
- Calculo de KPIs y Hash de Integridad
- Tests de Dashboard
- Backend users
- Backend checklists
- Frontend db
- Tests de maintenance
- Backend users
- Tests de work
- Backend audit
- Tests de checklists
- Frontend pages
- Requisitos IN
- Requisitos MI
- Backend maintenance
- Backend work
- Tests de maintenance
- Tests de users
- Frontend app
- Varios
- Varios
- Backend assets
- Tests de audit
- Frontend components
- Frontend components
- Frontend components
- Tests de assets
- Tests de work
- Frontend pages
- Tests de checklists
- Requisitos CL
- Requisitos OT
- Frontend components
- Frontend db
- Backend maintenance
- Backend users
- Varios
- Backend assets
- Tests de work
- Varios
- Varios
- Requisitos BI
- Frontend components
- Backend checklists
- Tests de checklists
- Requisitos OT
- Tests de assets
- Tests de assets
- Tests de inventory
- Backend reports
- Varios
- Requisitos OT
- Varios
- Varios
- Varios
- Requisitos OT
- Frontend components
- Frontend sync
- Varios
- Varios
- Build Android
- Backend assets
- Backend assets
- Backend maintenance
- Tests de users
- Tests de work
- Varios
- Requisitos FD
- Requisitos OF
- Requisitos OT
- Requisitos OT
- Varios
- Frontend api
- Tests de users
- Backend users
- Requisitos CK
- Requisitos PM
- Tests de assets
- Tests de assets
- Backend audit
- Tests de users
- Requisitos EV
- Requisitos OF
- Requisitos OT
- Requisitos PM
- Requisitos PM
- Frontend pages
- Varios
- Varios
- Backend assets
- Backend checklists
- Backend maintenance
- Backend reports
- Requisitos OT
- Requisitos PM
- Frontend db
- Varios
- Backend users
- Requisitos OF
- Varios
- Varios
- Conceptos de Dominio
- Varios
- Varios
- Varios
- Varios
- Varios
- Backend assets
- Backend audit
- Backend checklists
- Backend evidence
- Backend inventory
- Backend maintenance
- Backend notifications
- Backend reports
- Backend users
- Backend work
- Build Android
- Varios
- Varios
- Varios
- Varios
- Varios
- Migraciones de assets
- Migraciones de audit
- Migraciones de checklists
- Migraciones de checklists
- Migraciones de checklists
- Migraciones de evidence
- Migraciones de inventory
- Migraciones de maintenance
- Migraciones de notifications
- Migraciones de reports
- Migraciones de users
- Migraciones de users
- Migraciones de work
- Migraciones de work
- Varios
- Varios
- Varios
- Varios
- Varios
- Varios
- Varios
- Varios
- Varios
- Varios

## God Nodes (most connected - your core abstractions)
1. `WorkOrder` - 60 edges
2. `Asset` - 54 edges
3. `useAuthStore` - 52 edges
4. `Hospital` - 49 edges
5. `User` - 49 edges
6. `IsAdmin` - 29 edges
7. `IsAdminOrSup` - 29 edges
8. `useModalDismiss()` - 28 edges
9. `auth_client()` - 26 edges
10. `Icon()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `Campo offline_uuid para deduplicacion` --semantically_similar_to--> `Reglas de modelado Django (UUID PK, PROTECT, FK por string)`  [INFERRED] [semantically similar]
  docs/adr/ADR-002-offline-storage.md → claude.md
- `Logo TodoGas S.A.` --conceptually_related_to--> `TodoGas CMMS`  [INFERRED]
  backend/apps/reports/static/reports/logo.png → claude.md
- `Baja logica de activos (soft delete)` --semantically_similar_to--> `Reglas de modelado Django (UUID PK, PROTECT, FK por string)`  [INFERRED] [semantically similar]
  docs/requirements/RF-AC-03-creacion-edicion-y-baja-de-activos.md → claude.md
- `Job test (pytest + Postgres + Redis)` --semantically_similar_to--> `Servicio db (PostgreSQL 16)`  [INFERRED] [semantically similar]
  .github/workflows/ci.yml → docker-compose.yml
- `Hash de integridad en pie de pagina` --semantically_similar_to--> `App audit aislada para log inmutable`  [INFERRED] [semantically similar]
  backend/apps/reports/templates/reports/service_report.html → docs/adr/ADR-004-django-structure.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Pipeline de generacion del reporte de servicio en PDF** — docs_adr_adr_001_pdf_library_weasyprint, docs_adr_adr_001_pdf_library_celery_pdf_worker, docker_compose_celery, backend_apps_reports_templates_reports_service_report_acta_de_servicio, backend_apps_reports_templates_reports_email_report_email_de_reporte, backend_apps_reports_static_reports_logo_logo_todogas [INFERRED 0.85]
- **Pipeline de compilacion y distribucion del APK Android** — docs_release_android_build_apk, docs_release_android_keystore, docs_release_android_google_services_json, docs_release_android_network_security_config, docs_release_android_r8_proguard, docs_release_android_upload_apk [EXTRACTED 1.00]
- **Pipeline de CI del backend (lint, migraciones, tests, cobertura)** — _github_workflows_ci_lint, _github_workflows_ci_test, _github_workflows_ci_makemigrations_check, _github_workflows_ci_weasyprint_system_deps, _github_workflows_ci_coverage_threshold, backend_requirements_dev_dependencias_dev [EXTRACTED 1.00]
- **Cadena de Evidencia Probatoria de la OT** — docs_requirements_rf_ev_01_captura_de_fotos_con_geolocalizacion_y_timestamp_inmutables_foto_de_evidencia, docs_requirements_rf_ev_01_captura_de_fotos_con_geolocalizacion_y_timestamp_inmutables_geolocalizacion_y_timestamp_inmutables, docs_requirements_rf_fd_01_captura_de_firma_del_tecnico_firma_del_tecnico, docs_requirements_rf_fd_01_captura_de_firma_del_tecnico_hash_sha_256_del_contenido_de_la_ot, docs_requirements_rf_fd_03_cumplimiento_con_ley_527_de_1999_ley_527_de_1999 [INFERRED 0.85]
- **Ciclo de Vida del Stock** — docs_requirements_rf_in_01_catalogo_de_repuestos_e_insumos_catalogo_de_repuestos, docs_requirements_rf_in_02_registro_de_entradas_de_stock_movimiento_de_entrada, docs_requirements_rf_in_03_registro_de_salidas_de_stock_vinculadas_a_ots_movimiento_de_salida, docs_requirements_rf_in_03_registro_de_salidas_de_stock_vinculadas_a_ots_descuento_diferido_al_completar_la_ot, docs_requirements_rf_in_04_alertas_de_stock_minimo_alerta_de_stock_minimo, docs_requirements_rf_in_01_catalogo_de_repuestos_e_insumos_stock_calculado_por_movimientos [EXTRACTED 1.00]
- **Trazabilidad de Version de Checklist** — docs_requirements_rf_ck_01_constructor_visual_de_checklists_form_builder_plantilla_de_checklist, docs_requirements_rf_ck_02_versionado_de_plantillas_de_checklist_version_inmutable_de_plantilla, docs_requirements_rf_ck_04_ejecucion_del_checklist_en_la_app_android_ejecucion_de_checklist_en_app_android, docs_requirements_rf_ac_06_historial_consolidado_del_activo_orden_de_trabajo [EXTRACTED 1.00]
- **Flujo de sincronizacion offline (inicial, ejecucion, recuperacion)** — docs_requirements_rf_of_01_sincronizacion_inicial_de_datos_al_conectarse_rf_of_01, docs_requirements_rf_of_02_ejecucion_completa_de_ot_en_modo_offline_rf_of_02, docs_requirements_rf_of_03_sincronizacion_automatica_al_recuperar_conexion_rf_of_03 [INFERRED 0.90]
- **Maquina de estados del ciclo de vida de la OT** — docs_requirements_rf_ot_03_ciclo_de_vida_y_estados_de_la_ot_pendiente, docs_requirements_rf_ot_03_ciclo_de_vida_y_estados_de_la_ot_en_progreso, docs_requirements_rf_ot_03_ciclo_de_vida_y_estados_de_la_ot_en_revision, docs_requirements_rf_ot_03_ciclo_de_vida_y_estados_de_la_ot_completada, docs_requirements_rf_ot_03_ciclo_de_vida_y_estados_de_la_ot_cancelada [EXTRACTED 1.00]
- **Flujo de generacion automatica de OTs preventivas desde plan de mantenimiento** — docs_requirements_rf_pm_01_creacion_de_plan_de_mantenimiento_rf_pm_01, docs_requirements_rf_pm_02_calendarizacion_automatica_y_deteccion_de_conflictos_rf_pm_02, docs_requirements_rf_ot_08_ot_generada_automaticamente_desde_plan_preventivo_rf_ot_08 [INFERRED 0.85]
- **Postura de recuperacion ante desastres (RTO/RPO + backups + Multi-AZ)** — docs_requirements_rnf_dis_02_recuperacion_ante_fallos_rto_y_rpo, docs_requirements_rnf_bak_01_politica_de_backups_de_la_base_de_datos, concepts_aws_rds_multi_az [INFERRED 0.80]
- **Cadena de evidencia para auditorias INVIMA (log + hash de integridad + trazabilidad GMP)** — docs_requirements_rf_tr_01_log_de_auditoria_inmutable_y_completo, docs_requirements_rf_tr_03_integridad_e_inmutabilidad_de_ots_completadas, docs_requirements_rnf_com_01_trazabilidad_para_auditorias_gmp_bpm_invima [INFERRED 0.85]
- **Tension entre Habeas Data (supresion) y retencion GMP de registros auditables** — docs_requirements_rnf_com_02_cumplimiento_ley_1581_de_2012_proteccion_de_datos_personales_habeas_da, docs_requirements_rnf_bak_03_retencion_de_datos_historicos, docs_requirements_rnf_com_01_trazabilidad_para_auditorias_gmp_bpm_invima [INFERRED 0.80]
- **CI/CD Pipeline: Lint, Test, Deploy** — docs_requirements_rnf_man_03_pipeline_de_ci_cd_rnf_man_03, concept_github_actions, concept_ruff, concept_pytest [INFERRED 0.85]
- **Field Usability Posture of the Android App** — docs_requirements_rnf_usa_01_diseno_para_condiciones_de_campo_adversas_rnf_usa_01, docs_requirements_rnf_usa_02_gestion_de_errores_de_conectividad_en_la_app_rnf_usa_02, docs_requirements_rnf_usa_03_flujos_optimizados_para_rapidez_de_uso_rnf_usa_03, concept_app_android [INFERRED 0.85]
- **PDF Generation Pipeline: Speed, Quality, Worker Isolation** — docs_requirements_rnf_pdf_01_tiempos_de_generacion_de_pdf_rnf_pdf_01, docs_requirements_rnf_pdf_02_calidad_y_fidelidad_de_los_pdfs_rnf_pdf_02, docs_requirements_rnf_pdf_03_libreria_y_tecnologia_de_generacion_rnf_pdf_03, concept_celery [INFERRED 0.75]

## Communities (220 total, 46 thin omitted)

### Community 0 - "Evidencia: Fotos y Firmas"
Cohesion: 0.05
Nodes (54): Meta, Photo, Firma digital vinculada a una OT. Inmutable. Certifica que el técnico completó…, Evidencia fotográfica vinculada a una OT, con metadatos GPS. Fracttal: tab…, Signature, SignatureType, Meta, PhotoCreateSerializer (+46 more)

### Community 1 - "Cumplimiento Legal y Atributos de Calidad"
Cohesion: 0.06
Nodes (60): 15000 activos, 5000 OTs por mes, Anonimizacion de datos personales, AWS RDS Multi-AZ, Cumplimiento legal, Decreto 1377 de 2013, Decreto 2364 de 2012, Decreto 4725 de 2005 (+52 more)

### Community 2 - "Cliente API: Checklists y OTs"
Cohesion: 0.06
Nodes (38): useChecklistResponse(), useChecklistTemplates(), useCompleteChecklist(), useCreateChecklistResponse(), useCreateChecklistTemplate(), useSubmitField(), useIntegrityCheck(), useUsers() (+30 more)

### Community 3 - "Generacion de Reportes PDF"
Cohesion: 0.07
Nodes (46): generate_service_report_pdf(), Devuelve la URL publica o pre-firmada de una clave de storage., Genera el PDF del acta de servicio para una OT y lo sube al storage. Devuelve…, _resolve_url(), GeneratedReport, Meta, Registro de envío de reportes por correo electrónico., PDF generado automáticamente al completar una OT. Incluye: datos del activo,… (+38 more)

### Community 4 - "CI/CD y Plantillas de Reporte"
Cohesion: 0.06
Nodes (55): Skill graphify (/graphify), Umbral de cobertura (--fail-under), Job lint (Ruff), Chequeo de migraciones pendientes, Job test (pytest + Postgres + Redis), Dependencias de sistema de WeasyPrint en CI, Job deploy a produccion (placeholder AWS), Logo TodoGas invertido (blanco) (+47 more)

### Community 5 - "Frontend de Activos"
Cohesion: 0.06
Nodes (34): useAsset(), useAssetTree(), useCreateAsset(), useDecommissionAsset(), useHospitals(), useUpdateAsset(), AssetDetailPage(), formatDate() (+26 more)

### Community 6 - "Tests de Vistas de OT"
Cohesion: 0.09
Nodes (23): admin(), asset(), asset_b(), auth_client(), cli_user(), hospital(), hospital_b(), make_asset() (+15 more)

### Community 7 - "Sistema de Diseno y Layouts"
Cohesion: 0.09
Nodes (31): useStockAlerts(), Avatar(), initials(), SIZES, TONES, Icon(), ICON_NAMES, PATHS (+23 more)

### Community 8 - "Modelo de Inventario"
Cohesion: 0.07
Nodes (18): InventoryItem, Meta, MovementType, Movimiento de inventario (entrada o salida). Las salidas se vinculan a una OT., Repuesto o insumo del inventario. Fracttal: módulo Almacenes (vacío en la…, StockMovement, InventoryItemCreateUpdateSerializer, InventoryItemSerializer (+10 more)

### Community 9 - "Frontend de Planes de Mantenimiento"
Cohesion: 0.08
Nodes (28): useComplianceData(), useCreateMaintenancePlan(), useMaintenancePlan(), useMaintenancePlans(), usePausePlan(), useResumePlan(), useTriggerPlan(), useUpdateMaintenancePlan() (+20 more)

### Community 10 - "Frontend de Usuarios y Auditoria"
Cohesion: 0.08
Nodes (34): useAuditLog(), resolveId(), useCreateUser(), useDeactivateUser(), useResetPassword(), useUpdateUser(), ENTITY_TYPE_LABELS, entityTypeLabel() (+26 more)

### Community 11 - "Frontend de Reportes y Portal Cliente"
Cohesion: 0.09
Nodes (27): useAssets(), useClientPortalSummary(), useGenerateConsolidatedReport(), REPORT_POLL_ATTEMPTS, useRegenerateReport(), useReportDownload(), useReports(), useResendReportEmail() (+19 more)

### Community 12 - "Frontend de Dashboard y KPIs"
Cohesion: 0.07
Nodes (20): dom, main(), RO, useAssetsStatus(), useComplianceHistory(), useDashboard(), ComplianceBar(), SIZES (+12 more)

### Community 13 - "Tests de Usuarios y Contrasenas"
Cohesion: 0.07
Nodes (13): deactivate_url(), Tests de gestión de usuarios: CRUD, deactivate, reset_password, permisos., Tests directos del validador de contraseñas., reset_url(), TestStrongPasswordValidator, TestUserCreate, TestUserDeactivate, TestUserList (+5 more)

### Community 14 - "Frontend de Inventario"
Cohesion: 0.09
Nodes (22): useCreateInventoryItem(), useCreateStockMovement(), useInventoryItem(), useInventoryItems(), useStockMovements(), useUpdateInventoryItem(), useModalDismiss(), EMPTY_FORM (+14 more)

### Community 15 - "Modelo de Orden de Trabajo"
Cohesion: 0.10
Nodes (17): Meta, Priority, ProgressMeasure, Log de cambios de estado de una OT. Append-only. Cada cambio de estado se…, Orden de Trabajo. 1 OT = 1 Asset (simplificación para offline). Fracttal: OT…, Status, TaskType, WorkOrder (+9 more)

### Community 16 - "Correos y Serializers de Usuario"
Cohesion: 0.09
Nodes (17): Envía la nueva contraseña temporal tras un reset forzado por ADMIN., Envía las credenciales iniciales a un usuario recién creado., send_password_reset_email(), send_welcome_email(), ChangePasswordSerializer, Meta, Solicitud de reset de contraseña (no requiere autenticación)., Crea un usuario nuevo. Solo ADMIN puede usar este serializer. (+9 more)

### Community 17 - "Tests de Inventario"
Cohesion: 0.29
Nodes (27): auth_client(), make_asset(), make_hospital(), make_item(), make_user(), make_wo(), django_db, test_admin_can_create_inventory_item() (+19 more)

### Community 18 - "Notificaciones Push y Correo"
Cohesion: 0.14
Nodes (22): Channel, Meta, NotificationLog, NotificationType, Registro de notificaciones enviadas. Fracttal: panel de notificaciones en el…, Placeholder FCM. Crea un NotificationLog y escribe en consola. En Sprint 11 se…, send_assignment_notification(), send_overdue_alert() (+14 more)

### Community 19 - "Tests de Autenticacion"
Cohesion: 0.07
Nodes (8): clear_cache(), fixture, Tests de autenticación: login, logout, refresh, cambio de contraseña, rate…, TestChangePassword, TestLogin, TestLoginRateLimit, TestLogout, TestMeView

### Community 20 - "Requisitos de PDF y Notificaciones"
Cohesion: 0.07
Nodes (27): ADMIN, En Revision, Notificacion por Correo, Orden de Trabajo, Reporte PDF, RF-NT-02, Activo, Checklist (+19 more)

### Community 21 - "Modelo de Checklists"
Cohesion: 0.16
Nodes (15): ChecklistField, ChecklistFieldResponse, ChecklistResponse, ChecklistTemplate, ChecklistTemplateVersion, FieldType, Meta, Respuestas de un checklist asociadas a una OT. Una por OT. (+7 more)

### Community 22 - "Modelo de Activos y Jerarquia"
Cohesion: 0.13
Nodes (15): AssetCustomField, AssetCustomFieldValue, AssetNode, FieldType, Hospital, Meta, NodeType, Definición de un campo personalizado por tipo de activo (patrón EAV). Fracttal:… (+7 more)

### Community 23 - "Calculo de KPIs y Hash de Integridad"
Cohesion: 0.14
Nodes (18): calculate_assets_without_maintenance(), calculate_compliance_percentage(), calculate_mttr(), calculate_ots_by_status(), calculate_ots_by_technician(), calculate_overdue_count(), compute_wo_integrity_hash(), Same algorithm used in reports/generator.py when a WO is completed. (+10 more)

### Community 24 - "Tests de Dashboard"
Cohesion: 0.18
Nodes (24): admin(), asset(), asset_b(), auth_client(), clear_cache(), cli(), hospital(), hospital_b() (+16 more)

### Community 25 - "Backend users"
Cohesion: 0.12
Nodes (10): AssetCustomFieldViewSet, HospitalViewSet, IsAdmin, IsAdminOrSup, ADMIN o SUP (supervisor)., Solo usuarios con rol ADMIN., action, CRUD de usuarios. - list / retrieve: ADMIN o SUP - create / update / destroy:… (+2 more)

### Community 26 - "Backend checklists"
Cohesion: 0.11
Nodes (7): ChecklistFieldResponseCreateSerializer, ChecklistFieldResponseSerializer, ChecklistFieldSerializer, ChecklistResponseCreateSerializer, ChecklistResponseSerializer, Meta, ChecklistResponseViewSet

### Community 27 - "Frontend db"
Cohesion: 0.23
Nodes (23): getDB(), query(), ready(), run(), getChecklistResponse(), getOfflineWorkOrder(), getOfflineWorkOrders(), getSyncLog() (+15 more)

### Community 28 - "Tests de maintenance"
Cohesion: 0.15
Nodes (22): calculate_next_due_date(), generate_work_orders_for_plan(), get_plans_due_today(), Returns the next due date for a plan based on its frequency., Returns active plans whose next_due_date <= today and that have at least one…, Creates one WorkOrder per asset in the plan (skips assets with active OTs).…, admin_user(), asset() (+14 more)

### Community 29 - "Backend users"
Cohesion: 0.11
Nodes (15): UserAdmin, Meta, AbstractBaseUser, PermissionsMixin, Usuario del sistema. Usa email como login. Mapea a Fracttal: Recursos Humanos +…, Role, User, IsClient (+7 more)

### Community 30 - "Tests de work"
Cohesion: 0.16
Nodes (5): django_db, TestApplyTransition, TestValidateTransition, apply_transition(), validate_transition()

### Community 31 - "Backend audit"
Cohesion: 0.14
Nodes (10): Action, AuditLog, Meta, Prohibir updates: solo INSERT., Log de auditoría inmutable (append-only). Registra cualquier cambio en…, AuditLogSerializer, Meta, AuditLogViewSet (+2 more)

### Community 32 - "Tests de checklists"
Cohesion: 0.17
Nodes (20): admin(), asset(), client_admin(), client_tec(), hospital(), django_db, fixture, tec() (+12 more)

### Community 33 - "Frontend pages"
Cohesion: 0.14
Nodes (12): useChecklistTemplate(), usePublishVersion(), ChecklistPreview(), FieldPreview(), groupFields(), FieldCard(), FIELD_TYPES, getFieldType() (+4 more)

### Community 34 - "Requisitos IN"
Cohesion: 0.16
Nodes (20): ADMIN, Orden de Trabajo, KPI MTTR, MTBF por Activo, Registro de Costos por OT, RF-BI-02, RF-CK-02, Version Inmutable de Plantilla (+12 more)

### Community 35 - "Requisitos MI"
Cohesion: 0.12
Nodes (20): Migracion desde Fracttal, Reporte de Resultados de Migracion, RF-MI-01, Jerarquia de Activos, RF-MI-02, Activo, Completada, Migracion Fracttal (+12 more)

### Community 36 - "Backend maintenance"
Cohesion: 0.16
Nodes (9): FrequencyUnit, MaintenancePlan, MaintenancePlanExecution, Meta, Priority, Plan de mantenimiento. Genera OTs automáticamente según frecuencia. Fracttal:…, Registro de cada ejecución del plan (cada vez que se generan OTs)., TaskType (+1 more)

### Community 37 - "Backend work"
Cohesion: 0.16
Nodes (5): WorkOrderDetailSerializer, _get_client_ip(), action, Vuelve a lanzar la generacion del PDF de una OT ya completada. El unico…, WorkOrderViewSet

### Community 38 - "Tests de maintenance"
Cohesion: 0.20
Nodes (17): admin_user(), asset(), auth_client(), hospital(), plan(), fixture, sup_user(), tec_user() (+9 more)

### Community 39 - "Tests de users"
Cohesion: 0.12
Nodes (9): hospital(), fixture, Contrato que consume la gestion de usuarios del frontend (/usuarios,…, PASO 4: el modal de edicion guarda los campos editables., PASOS 6 y 7 del flujo: la pagina de auditoria y sus filtros., PASO 1 del flujo: la tabla se llena., TestAuditoria, TestEdicion (+1 more)

### Community 40 - "Frontend app"
Cohesion: 0.19
Nodes (11): fetchWorkOrders(), App(), AppBootstrap(), queryClient, countPendingSync(), useOfflineWorkOrders(), useWorkOrdersWithPendingSync(), initFCM() (+3 more)

### Community 41 - "Varios"
Cohesion: 0.12
Nodes (17): autoprefixer, devDependencies, autoprefixer, postcss, tailwindcss, @types/react, @types/react-dom, typescript (+9 more)

### Community 42 - "Varios"
Cohesion: 0.12
Nodes (17): axios, @capacitor-community/sqlite, @capacitor/core, @capacitor/geolocation, @capacitor/network, @capacitor/push-notifications, dependencies, axios (+9 more)

### Community 43 - "Backend assets"
Cohesion: 0.17
Nodes (8): AssetCreateUpdateSerializer, AssetCustomFieldSerializer, AssetNodeSerializer, HospitalListSerializer, HospitalSerializer, Meta, generate_asset_qr(), get_or_create_qr_url()

### Community 44 - "Tests de audit"
Cohesion: 0.29
Nodes (16): auth_client(), make_asset(), make_hospital(), make_user(), django_db, AuditMiddleware ignora rutas que no empiezan con /api/., AuditMiddleware crea un AuditLog cuando hay un POST exitoso a /api/., AuditMiddleware no registra peticiones GET. (+8 more)

### Community 45 - "Frontend components"
Cohesion: 0.20
Nodes (9): useWorkOrderPhotos(), useWorkOrderSignatures(), EvidenceGallery(), formatDateTime(), formatDateCO(), PhotoGallery(), CopyButton(), formatDateCO() (+1 more)

### Community 46 - "Frontend components"
Cohesion: 0.21
Nodes (15): useUploadPhoto(), dataUrlToFile(), extractError(), getPosition(), isNative, PhotoCapture(), flashSuccess(), handleCancel() (+7 more)

### Community 47 - "Frontend components"
Cohesion: 0.20
Nodes (10): Badge(), TONES, PRIORITY_CONFIG, PriorityBadge(), STATUS_CONFIG, StatusBadge(), taskTypeLabel(), TABS (+2 more)

### Community 48 - "Tests de assets"
Cohesion: 0.21
Nodes (9): admin_user(), api_client(), auth_client(), cli_user(), django_db, fixture, sup_user(), tec_user() (+1 more)

### Community 49 - "Tests de work"
Cohesion: 0.28
Nodes (4): WorkOrderCreateSerializer, make_create_context(), django_db, TestWorkOrderCreateSerializer

### Community 50 - "Frontend pages"
Cohesion: 0.17
Nodes (10): useCreateHospital(), useToggleHospitalActive(), useUpdateHospital(), EMPTY_FORM, HospitalModal(), handleSubmit(), validate(), HospitalRow() (+2 more)

### Community 51 - "Tests de checklists"
Cohesion: 0.23
Nodes (14): admin(), client_admin(), client_tec(), django_db, fixture, tec(), template(), test_create_template_as_admin() (+6 more)

### Community 52 - "Requisitos CL"
Cohesion: 0.19
Nodes (15): Activo, Historial Consolidado del Activo, RF-AC-06, SUP, CLI, Hospital, RF-AC-07, Aislamiento por Hospital (+7 more)

### Community 53 - "Requisitos OT"
Cohesion: 0.13
Nodes (15): ADMIN, Notificacion Push, Orden de Trabajo, RF-NT-01, TEC, ADMIN, Checklist, Correctiva (+7 more)

### Community 54 - "Frontend components"
Cohesion: 0.23
Nodes (14): useCreateSignature(), extractError(), SignaturePad(), clearCanvas(), draw(), getPos(), handleSubmit(), handleTouchMove() (+6 more)

### Community 55 - "Frontend db"
Cohesion: 0.22
Nodes (9): doInit(), initDB(), isNativePlatform(), loadDriver(), persist(), CREATE_TABLES, DB_NAME, DB_VERSION (+1 more)

### Community 56 - "Backend maintenance"
Cohesion: 0.16
Nodes (4): MaintenancePlanDetailSerializer, MaintenancePlanExecutionSerializer, MaintenancePlanListSerializer, Meta

### Community 57 - "Backend users"
Cohesion: 0.20
Nodes (9): Lectura pública de un usuario. No expone datos sensibles., UserSerializer, LoginView, LogoutView, MeView, APIView, GET /api/auth/me/ — datos del usuario autenticado., POST /api/auth/login/ Body: {email, password} Devuelve: {access, refresh, user} (+1 more)

### Community 58 - "Varios"
Cohesion: 0.19
Nodes (14): App Android, Area de toque 48dp, Capacitor, Contraste 4.5:1 WCAG AA, Fuente 16sp, Rendimiento, Sincronizacion offline, Usabilidad (+6 more)

### Community 59 - "Backend assets"
Cohesion: 0.18
Nodes (3): AssetSerializer, AssetViewSet, action

### Community 60 - "Tests de work"
Cohesion: 0.35
Nodes (12): admin(), asset(), hospital(), make_user(), make_work_order(), fixture, sup(), tec() (+4 more)

### Community 61 - "Varios"
Cohesion: 0.18
Nodes (13): 150 DPI, 15MB, Celery, Etiqueta QR 5s, Generacion de PDF, PDF/A-2b, PDF consolidado 60s, PDF individual 30s (+5 more)

### Community 62 - "Varios"
Cohesion: 0.17
Nodes (13): API backend, Content-Security-Policy, A01 Broken Access Control, A04 Insecure Design, A05 Security Misconfiguration, A07 Identification and Authentication Failures, A08 Software and Data Integrity Failures, A10 SSRF (+5 more)

### Community 63 - "Requisitos BI"
Cohesion: 0.15
Nodes (13): Semaforo de Estado de Mantenimiento, Dashboard Ejecutivo, KPI Activos sin Mantenimiento Reciente, KPI Cumplimiento de Planes Preventivos, KPI OTs por Tecnico, KPI OTs Vencidas, RF-BI-01, Reporte Mensual de Cumplimiento (+5 more)

### Community 64 - "Frontend components"
Cohesion: 0.23
Nodes (10): useHospital(), getStrength(), PasswordStrength(), STRENGTH_COLORS, STRENGTH_LABELS, STRENGTH_TEXT, ProfilePage(), handleSubmit() (+2 more)

### Community 65 - "Backend checklists"
Cohesion: 0.21
Nodes (3): ChecklistTemplateVersionSerializer, ChecklistTemplateViewSet, action

### Community 66 - "Tests de checklists"
Cohesion: 0.41
Nodes (11): make_field(), test_boolean_invalid_raises(), test_date_invalid_format_raises(), test_meter_in_range(), test_number_non_numeric_raises(), test_number_out_of_range_detected(), test_number_valid_returns_not_out_of_range(), test_select_invalid_option_raises() (+3 more)

### Community 67 - "Requisitos OT"
Cohesion: 0.17
Nodes (12): Activo, ADMIN, Checklist, En Progreso, En Revision, generacion automatica por Celery, Orden de Trabajo, Pendiente (+4 more)

### Community 68 - "Tests de assets"
Cohesion: 0.31
Nodes (3): auth_client(), django_db, TestAssetCRUD

### Community 69 - "Tests de assets"
Cohesion: 0.31
Nodes (10): admin_user(), asset(), auth_client(), hospital(), fixture, test_last_maintenance_date_from_completed_wo(), test_maintenance_status_due_soon(), test_maintenance_status_no_plan() (+2 more)

### Community 70 - "Tests de inventory"
Cohesion: 0.49
Nodes (10): auth_client(), make_hospital(), make_item(), make_user(), django_db, test_alerts_items_are_only_low_stock(), test_alerts_returns_correct_low_stock_count(), test_cli_cannot_access_alerts() (+2 more)

### Community 71 - "Backend reports"
Cohesion: 0.24
Nodes (5): ConsolidatedReportView, GeneratedReportViewSet, action, APIView, POST /api/reports/consolidated/ — genera PDF consolidado vía Celery.

### Community 72 - "Varios"
Cohesion: 0.22
Nodes (11): AWS CloudWatch, GitHub Actions, Mantenibilidad, A09 Security Logging and Monitoring Failures, pytest, Redis, Ruff, Sentry (+3 more)

### Community 73 - "Requisitos OT"
Cohesion: 0.18
Nodes (11): ADMIN, Cancelada, CLI, Completada, En Progreso, En Revision, Hospital, Orden de Trabajo (+3 more)

### Community 74 - "Varios"
Cohesion: 0.18
Nodes (7): ChecklistFieldResponse, ChecklistTemplate, InventoryItem, ===========================================================================…, Repuesto o insumo del inventario. Fracttal: Módulo "Almacenes" — VACÍO (0…, Plantilla de checklist reutilizable. Fracttal: Las "SubTareas" dentro de una…, Respuesta a un campo específico del checklist. Inmutable una vez que la OT se…

### Community 75 - "Varios"
Cohesion: 0.27
Nodes (10): AWS Secrets Manager, AWS Systems Manager Parameter Store, bcrypt, JWT, A02 Cryptographic Failures, Seguridad, TLS, RNF-SEG-01 (+2 more)

### Community 76 - "Varios"
Cohesion: 0.22
Nodes (10): Bundle 400KB gzip, CloudFront, FCP 1.5s, Interfaz web, LCP 3s, Lighthouse, TTI 4s, RNF-REN-02 (+2 more)

### Community 77 - "Requisitos OT"
Cohesion: 0.20
Nodes (10): ADMIN, Checklist, CLI, Completada, Hospital, Orden de Trabajo, Reporte PDF, RF-OT-07 (+2 more)

### Community 78 - "Frontend components"
Cohesion: 0.24
Nodes (7): FormBuilder(), addField(), handleMouseDown(), onMouseMove(), onMouseUp(), normalizeOptionsJson(), uid()

### Community 79 - "Frontend sync"
Cohesion: 0.51
Nodes (9): logSync(), markPhotoSynced(), dataUrlToFile(), errorText(), syncFieldResponses(), syncOfflineData(), syncPhotos(), syncSignatures() (+1 more)

### Community 80 - "Varios"
Cohesion: 0.20
Nodes (8): Asset, Priority, ProgressMeasure, Equipo específico con ficha técnica. Hoja del árbol. Fracttal: Nodo tipo…, Orden de Trabajo. Fracttal: Entidad "Orden de Trabajo" con número auto-…, Status, TaskType, WorkOrder

### Community 81 - "Varios"
Cohesion: 0.20
Nodes (7): AssetCustomFieldValue, ChecklistResponse, Hospital, Meta, Cliente / Hospital. Entidad de primer nivel. En Fracttal: NO existe como…, Valor de un campo personalizado para un activo específico. Fracttal: datos…, Respuestas de un checklist asociadas a una OT. Una por OT. Contiene metadatos…

### Community 82 - "Build Android"
Cohesion: 0.33
Nodes (5): androidx.test.ext.junit.runners.AndroidJUnit4, ExampleInstrumentedTest, ExampleUnitTest, org.junit.runner.RunWith, org.junit.Test

### Community 83 - "Backend assets"
Cohesion: 0.22
Nodes (7): Asset, Priority, Equipo específico con ficha técnica. Hoja del árbol. Fracttal: nodo tipo Equipo…, Status, ClientPortalView, APIView, GET /api/client-portal/summary/ Resumen del hospital del usuario CLI.

### Community 86 - "Tests de users"
Cohesion: 0.36
Nodes (8): admin_client(), admin_user(), api_client(), fixture, Reemplaza Redis por LocMemCache en todos los tests (Redis no necesario)., tech_client(), tech_user(), use_locmem_cache()

### Community 87 - "Tests de work"
Cohesion: 0.44
Nodes (8): active_asset(), admin(), hospital(), inactive_asset(), make_user(), fixture, sup(), tec()

### Community 88 - "Varios"
Cohesion: 0.25
Nodes (9): Django ORM, k6, Locust, A03 Injection, P95 500ms, P99 1500ms, PostgreSQL, RNF-MAN-04 (+1 more)

### Community 89 - "Requisitos FD"
Cohesion: 0.33
Nodes (9): TEC, Firma del Tecnico, Hash SHA-256 del Contenido de la OT, RF-FD-01, Firma del Receptor, RF-FD-02, Firma Electronica Simple, Ley 527 de 1999 (+1 more)

### Community 90 - "Requisitos OF"
Cohesion: 0.22
Nodes (9): Activo, Checklist, En Progreso, Orden de Trabajo, Pendiente, RF-OF-01, Sincronizacion Offline, TEC (+1 more)

### Community 91 - "Requisitos OT"
Cohesion: 0.39
Nodes (9): ADMIN, Cancelada, Completada, En Progreso, En Revision, Pendiente, RF-OT-03, SUP (+1 more)

### Community 92 - "Requisitos OT"
Cohesion: 0.22
Nodes (9): ADMIN, En Progreso, En Revision, Notificacion por Correo, Notificacion Push, Orden de Trabajo, Pendiente, RF-OT-06 (+1 more)

### Community 93 - "Varios"
Cohesion: 0.22
Nodes (8): name, private, scripts, build, dev, preview, type, version

### Community 94 - "Frontend api"
Cohesion: 0.28
Nodes (5): client, failedQueue, SESSION_EXPIRED_KEY, NotificationBell(), useNotifications()

### Community 95 - "Tests de users"
Cohesion: 0.36
Nodes (4): create_payload(), Payload identico al que arma CreateUserModal., PASOS 2 y 3 del flujo: crear tecnico y crear cliente., TestCrearUsuario

### Community 97 - "Requisitos CK"
Cohesion: 0.32
Nodes (8): Campo Firma, Campo Foto Requerida, Campo Rango Numerico, Constructor Visual de Checklists, RF-CK-01, Autoguardado en SQLite, Ejecucion de Checklist en App Android, RF-CK-04

### Community 98 - "Requisitos PM"
Cohesion: 0.25
Nodes (8): Activo, ADMIN, Checklist, Hospital, Plan de Mantenimiento, Preventiva, RF-PM-01, Tecnico

### Community 99 - "Tests de assets"
Cohesion: 0.48
Nodes (6): admin_user(), cli_user(), hospital_a(), hospital_b(), fixture, tec_user()

### Community 100 - "Tests de assets"
Cohesion: 0.33
Nodes (3): auth_client(), django_db, TestAssetNodeTree

### Community 101 - "Backend audit"
Cohesion: 0.43
Nodes (5): AuditMiddleware, _entity_id_from_body(), _entity_id_from_path(), _entity_type_from_path(), MiddlewareMixin

### Community 103 - "Requisitos EV"
Cohesion: 0.43
Nodes (7): Captura Solo desde Camara Nativa, Foto de Evidencia, Geolocalizacion y Timestamp Inmutables, RF-EV-01, URL Prefirmada S3 24h, Galeria de Evidencia, RF-EV-02

### Community 104 - "Requisitos OF"
Cohesion: 0.29
Nodes (7): ADMIN, Cancelada, idempotencia de sincronizacion, RF-OF-03, Sincronizacion Offline, TEC, proteccion anti-duplicados

### Community 105 - "Requisitos OT"
Cohesion: 0.33
Nodes (7): ADMIN, Correctiva, Orden de Trabajo, Plan de Mantenimiento, Predictiva, Preventiva, RF-OT-01

### Community 106 - "Requisitos PM"
Cohesion: 0.29
Nodes (7): ADMIN, Completada, Orden de Trabajo, Plan de Mantenimiento, RF-PM-03, SUP, Tecnico

### Community 107 - "Requisitos PM"
Cohesion: 0.29
Nodes (7): ADMIN, Checklist, Orden de Trabajo, Pendiente, Plan de Mantenimiento, RF-PM-04, Tecnico

### Community 108 - "Frontend pages"
Cohesion: 0.57
Nodes (7): markFieldResponseSynced(), newId(), saveFieldResponse(), ActiveChecklistForm(), handleBlur(), handleComplete(), pendingFieldIds()

### Community 109 - "Varios"
Cohesion: 0.29
Nodes (4): Action, AuditLog, Log de auditoría inmutable (append-only). Registra cualquier cambio en…, Prohibir updates: solo INSERT.

### Community 110 - "Varios"
Cohesion: 0.29
Nodes (5): AssetCustomField, ChecklistField, FieldType, Definición de un campo personalizado por tipo de activo. Fracttal: Tab…, Campo individual dentro de una versión de checklist. Fracttal: Cada subtarea…

### Community 113 - "Backend maintenance"
Cohesion: 0.40
Nodes (5): Processes all due maintenance plans and logs each execution to AuditLog.…, run_daily_generation(), generate_preventive_work_orders(), shared_task, test_run_daily_generation()

### Community 114 - "Backend reports"
Cohesion: 0.33
Nodes (3): Command, Sube el APK compilado al storage y devuelve la URL de descarga. python…, BaseCommand

### Community 115 - "Requisitos OT"
Cohesion: 0.33
Nodes (6): Activo, Checklist, En Progreso, Orden de Trabajo, RF-OT-05, TEC

### Community 116 - "Requisitos PM"
Cohesion: 0.33
Nodes (6): ADMIN, deteccion de conflictos de calendarizacion, generacion automatica por Celery, Plan de Mantenimiento, RF-PM-02, Tecnico

### Community 117 - "Frontend db"
Cohesion: 0.60
Nodes (5): createDriver(), flush(), idbGet(), idbPut(), openIDB()

### Community 118 - "Varios"
Cohesion: 0.33
Nodes (5): AbstractBaseUser, PermissionsMixin, Usuario del sistema. Extiende AbstractBaseUser para usar email como login (no…, Role, User

### Community 119 - "Backend users"
Cohesion: 0.50
Nodes (3): BaseUserManager, Manager personalizado que usa email como identificador único., UserManager

### Community 120 - "Requisitos OF"
Cohesion: 0.40
Nodes (5): Checklist, En Progreso, RF-OF-02, Sincronizacion Offline, TEC

### Community 121 - "Varios"
Cohesion: 0.40
Nodes (4): Channel, NotificationLog, NotificationType, Registro de notificaciones enviadas. Fracttal: Tiene un panel de notificaciones…

### Community 122 - "Varios"
Cohesion: 0.50
Nodes (3): BaseUserManager, Manager personalizado que usa email como identificador único., UserManager

### Community 123 - "Conceptos de Dominio"
Cohesion: 0.50
Nodes (4): Android API 26, Android API 34, RNF-AND-01, RNF-AND-02

### Community 124 - "Varios"
Cohesion: 0.50
Nodes (3): AssetNode, NodeType, Nodo de la jerarquía interna del hospital (pisos, áreas, servicios).…

### Community 125 - "Varios"
Cohesion: 0.50
Nodes (3): FrequencyUnit, MaintenancePlan, Plan de mantenimiento. Genera OTs automáticamente según frecuencia. Fracttal:…

### Community 126 - "Varios"
Cohesion: 0.50
Nodes (3): GeneratedReport, PDF generado automáticamente al completar una OT. Incluye: datos del activo,…, ReportType

### Community 127 - "Varios"
Cohesion: 0.50
Nodes (3): MovementType, Movimiento de inventario (entrada o salida). Las salidas se vinculan a una OT., StockMovement

### Community 128 - "Varios"
Cohesion: 0.50
Nodes (3): Firma digital vinculada a una OT. Inmutable. No existe en Fracttal como…, Signature, SignatureType

## Ambiguous Edges - Review These
- `Template email de reporte al cliente` → `Logo TodoGas invertido (blanco)`  [AMBIGUOUS]
  backend/apps/reports/templates/reports/email_report.html · relation: conceptually_related_to
- `RF-BI-02` → `RF-IN-01`  [AMBIGUOUS]
  docs/requirements/RF-BI-02-kpis-avanzados-mtbf-y-costos.md · relation: references
- `RNF-COM-01` → `RNF-COM-02`  [AMBIGUOUS]
  docs/requirements/RNF-COM-02-cumplimiento-ley-1581-de-2012-proteccion-de-datos-personales-habeas-da.md · relation: conceptually_related_to

## Knowledge Gaps
- **363 isolated node(s):** `Migration`, `NodeType`, `Priority`, `Status`, `FieldType` (+358 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 938 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **46 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Template email de reporte al cliente` and `Logo TodoGas invertido (blanco)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `RF-BI-02` and `RF-IN-01`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `RNF-COM-01` and `RNF-COM-02`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `User` connect `Backend users` to `Evidencia: Fotos y Firmas`, `Generacion de Reportes PDF`, `Tests de Vistas de OT`, `Modelo de Inventario`, `Modelo de Orden de Trabajo`, `Correos y Serializers de Usuario`, `Tests de Inventario`, `Notificaciones Push y Correo`, `Modelo de Activos y Jerarquia`, `Calculo de KPIs y Hash de Integridad`, `Tests de Dashboard`, `Backend users`, `Tests de maintenance`, `Tests de checklists`, `Backend maintenance`, `Tests de maintenance`, `Backend assets`, `Tests de audit`, `Tests de assets`, `Tests de checklists`, `Backend users`, `Tests de work`, `Tests de assets`, `Tests de inventory`, `Backend reports`, `Tests de work`, `Tests de assets`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `WorkOrder` connect `Modelo de Orden de Trabajo` to `Evidencia: Fotos y Firmas`, `Generacion de Reportes PDF`, `Tests de Vistas de OT`, `Modelo de Inventario`, `Tests de Inventario`, `Notificaciones Push y Correo`, `Modelo de Activos y Jerarquia`, `Calculo de KPIs y Hash de Integridad`, `Tests de Dashboard`, `Tests de maintenance`, `Backend users`, `Tests de work`, `Tests de checklists`, `Backend maintenance`, `Backend work`, `Tests de maintenance`, `Backend assets`, `Tests de work`, `Tests de work`, `Tests de assets`, `Tests de work`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `Hospital` connect `Modelo de Activos y Jerarquia` to `Evidencia: Fotos y Firmas`, `Generacion de Reportes PDF`, `Tests de Vistas de OT`, `Tests de Inventario`, `Notificaciones Push y Correo`, `Tests de Dashboard`, `Backend users`, `Tests de maintenance`, `Tests de checklists`, `Tests de maintenance`, `Tests de users`, `Backend assets`, `Tests de audit`, `Tests de assets`, `Tests de work`, `Tests de assets`, `Tests de inventory`, `Tests de work`, `Tests de assets`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `WorkOrder` (e.g. with `calculate_assets_without_maintenance()` and `calculate_compliance_percentage()`) actually correct?**
  _`WorkOrder` has 15 INFERRED edges - model-reasoned connections that need verification._