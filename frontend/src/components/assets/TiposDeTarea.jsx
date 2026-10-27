import { CATEGORIAS, categoriaDe, contarPorCategoria } from '../../utils/tiposDeTarea'

/** Nombre del tipo de la tarea y, debajo, el badge de su categoria. */
export function CeldaTipo({ tarea }) {
  const categoria = CATEGORIAS.find((c) => c.clave === categoriaDe(tarea))
  const nombre = tarea.task_type_display || tarea.task_type
  // «Preventivo» con badge «Preventivo» se repite: basta el badge.
  const repetido = (nombre ?? '').trim().toLowerCase() === categoria.etiqueta.toLowerCase()
  return (
    <div className="space-y-1">
      {!repetido && <p className="text-gray-800">{nombre}</p>}
      <span className={`inline-block text-xs px-2 py-0.5 rounded-full ${categoria.cls}`}>{categoria.etiqueta}</span>
    </div>
  )
}

/** Botones de filtro tipo píldora; los que no tienen tareas quedan deshabilitados. */
export function FiltroTiposDeTarea({ tareas, valor, onChange }) {
  const cuentas = contarPorCategoria(tareas)
  const opciones = [{ clave: 'ALL', etiqueta: 'Todos' }, ...CATEGORIAS]

  return (
    <div role="group" aria-label="Filtrar por tipo" className="flex flex-wrap gap-2 mb-3">
      {opciones.map((o) => {
        const n = cuentas[o.clave]
        const seleccionado = valor === o.clave
        return (
          <button
            key={o.clave}
            type="button"
            disabled={n === 0}
            aria-pressed={seleccionado}
            onClick={() => onChange(o.clave)}
            className={`text-xs px-3 py-1 rounded-full border transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
              seleccionado
                ? 'bg-brand text-white border-brand'
                : 'bg-white text-gray-600 border-gray-200 hover:border-brand hover:text-brand'
            }`}
          >
            {o.etiqueta} ({n})
          </button>
        )
      })}
    </div>
  )
}
