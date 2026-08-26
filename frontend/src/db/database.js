/**
 * Punto de entrada unico a la base offline.
 *
 * El driver se elige por plataforma y se carga dinamicamente, para que el
 * codigo nativo no viaje en el bundle web ni el wasm en el APK:
 *
 *   Android    -> @capacitor-community/sqlite
 *   Navegador  -> sql.js (wasm) persistido en IndexedDB
 *
 * Si el arranque falla, `isAvailable()` queda en false y los repositorios
 * degradan a no-op: la app sigue sirviendo online, solo se pierde el offline.
 */

import { Capacitor } from '@capacitor/core'
import { CREATE_TABLES, DB_NAME } from './schema'

let driver = null
let initPromise = null
let available = false
let initFailed = false

export const isNativePlatform = () => Capacitor.isNativePlatform()

/** true cuando hay una base utilizable. */
export function isAvailable() {
  return available
}

async function loadDriver() {
  if (isNativePlatform()) {
    const { createDriver } = await import('./nativeDriver')
    return createDriver(DB_NAME)
  }
  const { createDriver } = await import('./webDriver')
  return createDriver(DB_NAME)
}

async function doInit() {
  driver = await loadDriver()
  for (const statement of CREATE_TABLES) {
    await driver.execute(statement)
  }
  await driver.persist()
  available = true
  return driver
}

/** Abre la base y crea las tablas. Idempotente y seguro ante llamadas paralelas. */
export async function initDB() {
  if (driver && available) return driver
  if (initFailed) return null
  if (initPromise) return initPromise

  initPromise = doInit().catch((error) => {
    initFailed = true
    available = false
    driver = null
    console.warn(
      '[db] SQLite no disponible, el modo offline queda desactivado:',
      error?.message ?? error
    )
    return null
  })

  return initPromise
}

export async function getDB() {
  if (!driver || !available) await initDB()
  return driver
}

/**
 * Espera a que la base este lista. Los repositorios lo usan en vez de
 * `isAvailable()`, que es sincrono y devuelve false mientras initDB() aun
 * esta en vuelo — lo que hacia que las primeras escrituras se perdieran.
 */
export async function ready() {
  return Boolean(await getDB())
}

/** Ejecuta una escritura y persiste. */
export async function run(statement, values = []) {
  const conn = await getDB()
  if (!conn) return null
  const result = await conn.run(statement, values)
  await conn.persist()
  return result
}

/** Ejecuta un SELECT. Devuelve siempre un array de filas. */
export async function query(statement, values = []) {
  const conn = await getDB()
  if (!conn) return []
  return conn.query(statement, values)
}

export async function persist() {
  if (!available || !driver) return
  await driver.persist()
}

export async function closeDB() {
  if (!driver) return
  try {
    await driver.close()
  } catch (error) {
    console.warn('[db] error al cerrar:', error?.message ?? error)
  } finally {
    driver = null
    available = false
    initPromise = null
  }
}
