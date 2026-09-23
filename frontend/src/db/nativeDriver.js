/**
 * Driver SQLite para Android, sobre @capacitor-community/sqlite.
 *
 * Se importa dinamicamente desde database.js para que su codigo no entre en
 * el bundle del navegador.
 */

import { CapacitorSQLite, SQLiteConnection } from '@capacitor-community/sqlite'
import { LATEST_VERSION } from './migrations'

export async function createDriver(dbName) {
  const sqlite = new SQLiteConnection(CapacitorSQLite)

  // Si el WebView se recarga sin cerrar la app (tocar una notificacion, sesion
  // vencida), la conexion nativa sigue abierta pero el lado JS la olvido:
  // createConnection fallaria con "already exists" y el offline quedaria
  // apagado hasta reiniciar la app. Esto cierra las nativas huerfanas.
  await sqlite.checkConnectionsConsistency().catch(() => {})

  // Una conexion puede sobrevivir a un hot reload durante el desarrollo.
  const existing = await sqlite.isConnection(dbName, false)
  const db = existing?.result
    ? await sqlite.retrieveConnection(dbName, false)
    // Sin sentencias de upgrade registradas el plugin no toca user_version:
    // el esquema lo migra migrations.js.
    : await sqlite.createConnection(dbName, false, 'no-encryption', LATEST_VERSION, false)

  await db.open()

  return {
    async execute(statement) {
      await db.execute(statement)
    },

    async run(statement, values = []) {
      return db.run(statement, values)
    },

    async query(statement, values = []) {
      const result = await db.query(statement, values)
      return result?.values ?? []
    },

    async persist() {
      // En nativo el motor escribe directamente en disco.
    },

    async close() {
      await sqlite.closeConnection(dbName, false)
    },
  }
}
