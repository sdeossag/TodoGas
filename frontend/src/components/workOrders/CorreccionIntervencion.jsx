import { useState } from 'react'
import { useCorrectIntervention } from '../../api/workOrders'
import { aInputLocal, cuando, validarIntervencion } from '../../utils/intervencion'

function mensajeDelServidor(err) {
  const d = err?.response?.data
  if (!d) return 'No se pudo guardar. Revisa la conexión e intenta de nuevo.'
  const partes = ['detail', 'start', 'end'].map((k) => d[k]).filter(Boolean)
  return partes.length ? partes.join(' ') : 'No se pudo guardar.'
}

/**
 * Fecha de intervención de una OT en revisión: admin y supervisor la corrigen
 * cuando el reloj del teléfono estaba mal o la visita se cargó después. El acta
 * y el correo usan la fecha corregida; lo que registró el técnico no se pierde.
 */
export default function CorreccionIntervencion({ wo, puedeCorregir }) {
  const mut = useCorrectIntervention(wo.id)
  const [editando, setEditando] = useState(false)
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [tocado, setTocado] = useState({})
  const [errorServidor, setErrorServidor] = useState('')

  const corregida = Boolean(wo.intervention_start_override && wo.intervention_end_override)
  const errores = validarIntervencion(start, end, wo.created_at)
  const valido = Object.keys(errores).length === 0

  function abrir() {
    setStart(aInputLocal(wo.intervention_start_override || wo.started_at))
    setEnd(aInputLocal(wo.intervention_end_override || wo.started_at))
    setTocado({})
    setErrorServidor('')
    setEditando(true)
  }

  async function enviar(datos) {
    setErrorServidor('')
    try {
      await mut.mutateAsync(datos)
      setEditando(false)
    } catch (err) {
      setErrorServidor(mensajeDelServidor(err))
    }
  }

  const guardar = (e) => {
    e.preventDefault()
    setTocado({ start: true, end: true })
    if (!valido) return
    enviar({ start: new Date(start).toISOString(), end: new Date(end).toISOString() })
  }

  const campo = (clave, etiqueta, valor, set) => {
    const mensaje = tocado[clave] || tocado.end ? errores[clave] : undefined
    return (
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1" htmlFor={`interv-${clave}`}>
          {etiqueta}
        </label>
        <input
          id={`interv-${clave}`}
          type="datetime-local"
          value={valor}
          onChange={(e) => { set(e.target.value); setTocado((t) => ({ ...t, [clave]: true })) }}
          aria-invalid={Boolean(mensaje)}
          aria-describedby={mensaje ? `interv-${clave}-error` : undefined}
          className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 ${
            mensaje ? 'border-red-400 focus:ring-red-200' : 'border-gray-300 focus:ring-brand/30'
          }`}
        />
        <p id={`interv-${clave}-error`} className="mt-1 min-h-[1rem] text-xs text-red-600" role="alert">
          {mensaje || ''}
        </p>
      </div>
    )
  }

  return (
    <div className="col-span-2 rounded-lg bg-gray-50 border border-gray-100 p-3" data-testid="intervencion">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-medium text-gray-500 mb-0.5">Fecha de intervención</div>
          {corregida ? (
            <div className="text-sm text-gray-800">
              {cuando(wo.intervention_start_override)} &ndash; {cuando(wo.intervention_end_override)}
              <div className="text-xs text-gray-500 mt-0.5">
                Corregido por {wo.intervention_corrected_by_name}
                {wo.intervention_corrected_at ? `, ${cuando(wo.intervention_corrected_at)}` : ''}
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-600">
              Según lo que el técnico registró en campo (primera a última respuesta, foto o firma).
            </div>
          )}
        </div>
        {puedeCorregir && !editando && (
          <button type="button" onClick={abrir} className="text-xs font-medium text-brand hover:underline shrink-0">
            {corregida ? 'Cambiar' : 'Corregir'}
          </button>
        )}
      </div>

      {puedeCorregir && editando && (
        <form onSubmit={guardar} className="mt-3 space-y-2" noValidate>
          <p className="text-xs text-gray-500">
            El acta y el correo mostrarán estas horas. Lo que registró el técnico no se borra y el cambio queda en la auditoría.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {campo('start', 'Inicio', start, setStart)}
            {campo('end', 'Fin', end, setEnd)}
          </div>
          {errorServidor && <p className="text-xs text-red-600" role="alert">{errorServidor}</p>}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="submit"
              disabled={!valido || mut.isPending}
              className="px-3 py-1.5 rounded-lg bg-brand text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {mut.isPending ? 'Guardando…' : 'Guardar fecha'}
            </button>
            <button type="button" onClick={() => setEditando(false)} className="px-3 py-1.5 rounded-lg text-sm text-gray-600 hover:bg-gray-100">
              Cancelar
            </button>
            {corregida && (
              <button
                type="button"
                disabled={mut.isPending}
                onClick={() => enviar({ start: null, end: null })}
                className="ml-auto text-xs text-gray-500 hover:text-red-600 hover:underline"
              >
                Quitar la corrección
              </button>
            )}
          </div>
        </form>
      )}
    </div>
  )
}
