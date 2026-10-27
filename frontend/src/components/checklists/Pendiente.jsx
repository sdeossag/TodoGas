import { useState } from 'react'

import Icon from '../ui/Icon'

/**
 * "Pendiente — no se pudo revisar": el tecnico deja un campo o un bloque
 * repetible completo (p. ej. "Cubiculo 7", aislado por aerosoles) para volver
 * despues, con un motivo corto obligatorio.
 */

/** La franja de un pendiente ya marcado, con su motivo y la salida. */
export function PendienteMarcado({ pendiente, onQuitar = null, className = '' }) {
  return (
    <div className={`flex items-start justify-between gap-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 ${className}`}>
      <span className="min-w-0">
        <span className="font-semibold">Pendiente — no se pudo revisar.</span>{' '}
        <span className="break-words">{pendiente.reason}</span>
      </span>
      {onQuitar && (
        <button type="button" onClick={onQuitar}
          className="flex-shrink-0 text-xs px-2 py-1 rounded-lg bg-white border border-amber-300 hover:bg-amber-100">
          Quitar
        </button>
      )}
    </div>
  )
}

/** La insignia corta, para encabezados de tarjeta. */
export function InsigniaPendiente({ className = '' }) {
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 ${className}`}>
      <Icon name="warning" className="w-3 h-3" /> Pendiente
    </span>
  )
}

/**
 * El enlace "Marcar pendiente" que abre el motivo. `onGuardar(motivo)` puede
 * lanzar o devolver un texto de error.
 */
export default function MarcarPendiente({ etiqueta = 'Marcar pendiente', onGuardar, className = '' }) {
  const [abierto, setAbierto] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)

  async function guardar() {
    const limpio = motivo.trim()
    if (!limpio) {
      setError('Di por qué no se pudo revisar.')
      return
    }
    setGuardando(true)
    setError('')
    try {
      await onGuardar(limpio)
      setAbierto(false)
      setMotivo('')
    } catch (err) {
      setError(err?.message || 'No se pudo marcar como pendiente.')
    } finally {
      setGuardando(false)
    }
  }

  if (!abierto) {
    return (
      <button type="button" onClick={() => setAbierto(true)}
        className={`text-xs text-amber-700 hover:text-amber-900 hover:underline ${className}`}>
        {etiqueta}
      </button>
    )
  }

  return (
    <div className={`space-y-2 rounded-lg border border-amber-200 bg-amber-50/60 p-3 ${className}`}>
      <label className="block text-xs font-medium text-amber-900">
        ¿Por qué no se pudo revisar?
        <input
          type="text"
          value={motivo}
          maxLength={200}
          autoFocus
          onChange={(e) => setMotivo(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); guardar() } }}
          placeholder="Ej.: aislado por aerosoles"
          className="mt-1 w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-amber-300"
        />
      </label>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex items-center gap-2">
        <button type="button" onClick={guardar} disabled={guardando}
          className="px-3 py-1.5 text-sm font-medium rounded-lg bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-60">
          {guardando ? 'Guardando...' : 'Dejar pendiente'}
        </button>
        <button type="button" onClick={() => { setAbierto(false); setError('') }}
          className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800">
          Cancelar
        </button>
      </div>
    </div>
  )
}
