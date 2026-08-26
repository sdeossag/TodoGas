/**
 * Driver SQLite para navegador, sobre sql.js (SQLite compilado a wasm).
 *
 * Se usa sql.js directamente en vez de la implementacion web del plugin porque
 * asi el glue de JS y el .wasm salen del mismo paquete y no puede haber
 * desajuste de ABI. Vite resuelve el wasm con `?url`.
 *
 * sql.js vive en memoria: la persistencia entre recargas la damos nosotros
 * volcando `db.export()` a IndexedDB.
 */

import initSqlJs from 'sql.js'
import wasmUrl from 'sql.js/dist/sql-wasm.wasm?url'

const IDB_NAME = 'todogas_sqlite_store'
const IDB_STORE = 'databases'

// ── Persistencia en IndexedDB ────────────────────────────────────────────────

function openIDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(IDB_NAME, 1)
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(IDB_STORE)) {
        request.result.createObjectStore(IDB_STORE)
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function idbGet(key) {
  const idb = await openIDB()
  return new Promise((resolve, reject) => {
    const tx = idb.transaction(IDB_STORE, 'readonly')
    const req = tx.objectStore(IDB_STORE).get(key)
    req.onsuccess = () => resolve(req.result ?? null)
    req.onerror = () => reject(req.error)
  })
}

async function idbPut(key, value) {
  const idb = await openIDB()
  return new Promise((resolve, reject) => {
    const tx = idb.transaction(IDB_STORE, 'readwrite')
    tx.objectStore(IDB_STORE).put(value, key)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

// ── Driver ───────────────────────────────────────────────────────────────────

export async function createDriver(dbName) {
  const SQL = await initSqlJs({ locateFile: () => wasmUrl })

  const saved = await idbGet(dbName)
  const db = saved ? new SQL.Database(new Uint8Array(saved)) : new SQL.Database()

  // Volcar en cada escritura seria caro; se agrupan en un microtimer.
  let flushTimer = null
  let flushing = null

  async function flush() {
    flushing = idbPut(dbName, db.export())
    try {
      await flushing
    } finally {
      flushing = null
    }
  }

  return {
    async execute(statement) {
      db.run(statement)
    },

    async run(statement, values = []) {
      db.run(statement, values)
      return { changes: { changes: db.getRowsModified() } }
    },

    async query(statement, values = []) {
      const stmt = db.prepare(statement)
      try {
        if (values.length) stmt.bind(values)
        const rows = []
        while (stmt.step()) rows.push(stmt.getAsObject())
        return rows
      } finally {
        stmt.free()
      }
    },

    async persist() {
      if (flushTimer) clearTimeout(flushTimer)
      await new Promise((resolve) => {
        flushTimer = setTimeout(() => flush().then(resolve, resolve), 150)
      })
    },

    async close() {
      if (flushing) await flushing
      await flush()
      db.close()
    },
  }
}
