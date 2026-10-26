import { useDecommissionPreview } from '../../api/assets'

// Lo que va a pasar al dar de baja un equipo, con los numeros de hoy y en
// lenguaje sencillo. Se muestra antes de confirmar, en el boton y en el formulario.
export default function DecommissionPreview({ assetId, enabled = true }) {
  const { data, isLoading, isError } = useDecommissionPreview(assetId, enabled)

  if (isLoading) return <p className="text-sm text-gray-500">Calculando qué pasará…</p>
  if (isError || !data) {
    return <p className="text-sm text-gray-600">No se pudo calcular el efecto. Al dar de baja, sus tareas pendientes se anulan.</p>
  }

  const n = data.will_cancel
  const m = data.tasks_in_work_orders
  return (
    <ul className="text-sm text-gray-700 space-y-2" aria-live="polite">
      <li className="flex gap-2">
        <span className="font-semibold text-red-600 tabular-nums">{n}</span>
        <span>
          {n === 0
            ? 'No tiene tareas pendientes que anular.'
            : n === 1
              ? 'Se anulará 1 tarea pendiente. Queda en el historial como cancelada; nada se borra.'
              : `Se anularán ${n} tareas pendientes. Quedan en el historial como canceladas; nada se borra.`}
        </span>
      </li>
      {m > 0 && (
        <li className="flex gap-2 text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          <span className="font-semibold tabular-nums">{m}</span>
          <span>
            {m === 1 ? 'tarea sigue' : 'tareas siguen'} en OT abiertas ({data.in_work_orders.join(', ')}) y no se
            tocan. Al cerrarse esas OT no se programa la siguiente.
          </span>
        </li>
      )}
      <li className="text-gray-500">Si lo reactivas, sus tareas del protocolo se reabren.</li>
    </ul>
  )
}
