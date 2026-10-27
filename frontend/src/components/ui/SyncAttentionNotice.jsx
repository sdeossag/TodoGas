import { useEffect, useRef, useState } from 'react'

import useNetworkStore from '../../store/networkStore'
import { itemLabel } from '../../sync/retryPolicy'
import Icon from './Icon'

const itemId = (i) => `${i.entity_type}:${i.entity_key}`
const FEEDBACK_MS = 5000

/** "OT 7 · Alarma de oxigeno", o nada si la OT ya no esta en el telefono. */
function ordenDe(item) {
  if (!item.wo_number && !item.wo_title) return ''
  return [item.wo_number ? `OT ${item.wo_number}` : null, item.wo_title].filter(Boolean).join(' · ')
}

/**
 * Aviso permanente de lo que el servidor rechazo y no se manda solo.
 *
 * Sin boton de cerrar ni de descartar: son datos del trabajo (fotos, firmas,
 * respuestas) con valor de evidencia. La unica salida es "Reintentar", que los
 * vuelve a poner en la cola. Se guarda en la base: sigue ahi al reabrir la app.
 */
export default function SyncAttentionNotice() {
  const items = useNetworkStore((s) => s.attentionItems)
  const retryAttention = useNetworkStore((s) => s.retryAttention)
  const dismissAttention = useNetworkStore((s) => s.dismissAttention)

  // Lo que se esta reintentando ahora: el boton responde al toque, no al resultado.
  const [busy, setBusy] = useState(() => new Set())
  const [feedback, setFeedback] = useState('')
  const timer = useRef(null)

  useEffect(() => () => clearTimeout(timer.current), [])

  if (items.length === 0 && !feedback) return null

  function say(message) {
    setFeedback(message)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setFeedback(''), FEEDBACK_MS)
  }

  async function retry(targets) {
    const ids = targets.map(itemId)
    setBusy((prev) => new Set([...prev, ...ids]))
    setFeedback('')
    try {
      const result = await retryAttention(targets)
      if (result.offline) say('Sin conexión. Se enviará cuando vuelva la señal.')
      else if (result.failed === 0) say(result.sent === 1 ? 'Listo, se envió.' : `Listo, se enviaron ${result.sent}.`)
      else say(`${result.failed === 1 ? 'Sigue' : 'Siguen'} sin enviarse: ${result.failed}. Revisa el mensaje del servidor.`)
    } finally {
      setBusy((prev) => {
        const next = new Set(prev)
        ids.forEach((id) => next.delete(id))
        return next
      })
    }
  }

  const anyBusy = busy.size > 0

  return (
    <section
      aria-label="Elementos que requieren atención"
      className="px-4 sm:px-6 py-3 bg-red-50 border-b border-red-200 text-red-900"
    >
      {items.length > 0 && (
        <>
          <div className="flex items-start gap-3">
            <Icon name="warning" className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-600" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">
                {items.length === 1
                  ? 'Hay 1 elemento que no se pudo enviar'
                  : `Hay ${items.length} elementos que no se pudieron enviar`}
              </p>
              <p className="text-xs text-red-800 mt-0.5">
                Siguen guardados en este teléfono; no se pierde nada.
              </p>
            </div>
            {items.length > 1 && (
              <button
                type="button"
                onClick={() => retry(items)}
                disabled={anyBusy}
                className="flex-shrink-0 min-h-[44px] px-3 rounded-lg text-sm font-medium text-red-800 border border-red-300 bg-white active:scale-[0.97] active:bg-red-100 transition-transform disabled:opacity-60 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-red-500/25"
              >
                Reintentar todo
              </button>
            )}
          </div>

          <ul className="mt-2 space-y-2 max-h-56 overflow-y-auto">
            {items.map((item) => {
              const working = busy.has(itemId(item))
              const orden = ordenDe(item)
              return (
                <li
                  key={itemId(item)}
                  className="flex items-center gap-3 rounded-lg bg-white/70 border border-red-200 px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">
                      {itemLabel(item.entity_type)}
                      {orden && <span className="font-normal text-red-800"> · {orden}</span>}
                    </p>
                    {item.error_message && (
                      <p className="text-xs text-red-800 break-words">
                        El servidor dice: {item.error_message}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => (item.entity_type === 'work_order' ? dismissAttention([item]) : retry([item]))}
                    disabled={working}
                    className="flex-shrink-0 min-h-[44px] min-w-[96px] inline-flex items-center justify-center gap-1.5 px-3 rounded-lg text-sm font-medium text-white bg-red-600 active:scale-[0.97] active:bg-red-700 transition-transform disabled:opacity-70 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-red-500/25"
                  >
                    {working && (
                      <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
                    )}
                    {item.entity_type === 'work_order' ? 'Entendido' : working ? 'Reintentando…' : 'Reintentar'}
                  </button>
                </li>
              )
            })}
          </ul>
        </>
      )}

      <p role="status" aria-live="polite" className={feedback ? 'mt-2 text-sm font-medium text-red-900' : 'sr-only'}>
        {feedback}
      </p>
    </section>
  )
}
