/**
 * Esquema de la base SQLite local que respalda el modo offline.
 *
 * Todo lo que el tecnico necesita para ejecutar una OT sin red vive aqui.
 * Las tablas de evidencia llevan `synced` para que el motor de sincronizacion
 * sepa que falta por subir; las OT llevan `local_status_changed` para las
 * transiciones hechas sin conexion.
 */

export const DB_NAME = 'todogas_offline'
export const DB_VERSION = 1

export const CREATE_TABLES = [
  `CREATE TABLE IF NOT EXISTS offline_work_orders (
    id TEXT PRIMARY KEY,
    wo_number INTEGER,
    title TEXT,
    description TEXT,
    task_type TEXT,
    status TEXT,
    priority TEXT,
    scheduled_date TEXT,
    asset_id TEXT,
    asset_name TEXT,
    asset_code TEXT,
    hospital_name TEXT,
    hospital_id TEXT,
    assigned_to_id TEXT,
    checklist_version_id TEXT,
    checklist_response_id TEXT,
    notes TEXT,
    synced_at TEXT,
    offline_uuid TEXT UNIQUE,
    raw_json TEXT,
    local_status_changed INTEGER DEFAULT 0,
    local_status_comment TEXT
  )`,

  `CREATE TABLE IF NOT EXISTS offline_checklist_responses (
    id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    version_id TEXT,
    started_at TEXT,
    completed_at TEXT,
    version_fields_json TEXT,
    FOREIGN KEY (work_order_id)
      REFERENCES offline_work_orders(id)
  )`,

  `CREATE TABLE IF NOT EXISTS offline_field_responses (
    id TEXT PRIMARY KEY,
    response_id TEXT NOT NULL,
    field_id TEXT NOT NULL,
    value TEXT,
    notes TEXT,
    answered_at TEXT,
    synced INTEGER DEFAULT 0,
    FOREIGN KEY (response_id)
      REFERENCES offline_checklist_responses(id)
  )`,

  `CREATE TABLE IF NOT EXISTS offline_photos (
    id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    file_path TEXT,
    latitude REAL,
    longitude REAL,
    taken_at TEXT,
    caption TEXT,
    file_hash TEXT,
    synced INTEGER DEFAULT 0,
    offline_uuid TEXT UNIQUE
  )`,

  `CREATE TABLE IF NOT EXISTS offline_signatures (
    id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    signature_type TEXT,
    image_base64 TEXT,
    signer_name TEXT,
    signer_role TEXT,
    latitude REAL,
    longitude REAL,
    signed_at TEXT,
    synced INTEGER DEFAULT 0
  )`,

  `CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT,
    entity_id TEXT,
    action TEXT,
    status TEXT,
    error_message TEXT,
    attempted_at TEXT
  )`,

  // Un solo par (response_id, field_id) por campo: al reescribir una respuesta
  // se reemplaza la anterior en vez de acumular filas sin sincronizar.
  `CREATE UNIQUE INDEX IF NOT EXISTS idx_field_responses_unique
    ON offline_field_responses (response_id, field_id)`,

  `CREATE INDEX IF NOT EXISTS idx_work_orders_assigned
    ON offline_work_orders (assigned_to_id, status)`,

  `CREATE INDEX IF NOT EXISTS idx_photos_pending
    ON offline_photos (work_order_id, synced)`,

  `CREATE INDEX IF NOT EXISTS idx_signatures_pending
    ON offline_signatures (work_order_id, synced)`,
]

/**
 * SQLite ordena texto alfabeticamente, asi que `ORDER BY priority DESC` daria
 * MEDIUM > LOW > HIGH. Hay que mapear a un peso numerico.
 */
export const PRIORITY_RANK_SQL = `CASE priority
  WHEN 'HIGH' THEN 0
  WHEN 'MEDIUM' THEN 1
  WHEN 'LOW' THEN 2
  ELSE 3
END`
