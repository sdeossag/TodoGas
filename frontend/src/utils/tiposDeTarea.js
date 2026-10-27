/**
 * Categoria de una tarea (si cuenta como preventivo, correctivo u otro), para
 * el badge de la columna Tipo y los filtros de la ficha del activo. Viene del
 * servidor en `task_type_counts_as`; si falta, cuenta como otro.
 */

export const CATEGORIAS = [
  { clave: 'PREVENTIVE', etiqueta: 'Preventivo', cls: 'bg-blue-50 text-blue-700' },
  { clave: 'CORRECTIVE', etiqueta: 'Correctivo', cls: 'bg-amber-100 text-amber-800' },
  { clave: 'OTHER', etiqueta: 'Otro', cls: 'bg-gray-100 text-gray-600' },
]

const CLAVES = new Set(CATEGORIAS.map((c) => c.clave))

/** Clave de la categoria de la tarea; lo desconocido cuenta como otro. */
export function categoriaDe(tarea) {
  const clave = tarea?.task_type_counts_as
  return CLAVES.has(clave) ? clave : 'OTHER'
}

/** Las tareas de esa categoria; 'ALL' devuelve todas. */
export function filtrarPorCategoria(tareas, categoria) {
  const lista = tareas ?? []
  if (categoria === 'ALL') return lista
  return lista.filter((t) => categoriaDe(t) === categoria)
}

/** Cuantas tareas hay por categoria, mas el total en ALL. */
export function contarPorCategoria(tareas) {
  const cuentas = { ALL: 0, PREVENTIVE: 0, CORRECTIVE: 0, OTHER: 0 }
  for (const t of tareas ?? []) {
    cuentas.ALL += 1
    cuentas[categoriaDe(t)] += 1
  }
  return cuentas
}
