import { useState } from 'react'

import { COUNTS_AS, useDeleteTaskType, useSaveTaskType, useTaskTypes } from '../../api/taskTypes'
import Modal from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import { apiErrorMessage } from '../../utils/apiError'

/**
 * Catálogo de tipos de tarea (decisión del 2026-09-23). Arranca con los del
 * cliente en Fracttal. Cada tipo dice en qué indicador cuenta. Un tipo en uso
 * no se borra: se desactiva y deja de ofrecerse, pero lo que ya lo usa lo
 * conserva. Los cinco del sistema no se desactivan.
 */
export default function TaskTypesPage() {
  const { data: tipos = [], isLoading, isError } = useTaskTypes()
  const guardar = useSaveTaskType()
  const [nuevo, setNuevo] = useState({ name: '', counts_as: 'OTHER' })
  const [errorNuevo, setErrorNuevo] = useState('')
  const [errorFila, setErrorFila] = useState(null) // { id, mensaje }
  const [renombrando, setRenombrando] = useState(null)
  const [borrando, setBorrando] = useState(null)

  async function agregar(e) {
    e.preventDefault()
    if (!nuevo.name.trim()) { setErrorNuevo('Ponle un nombre'); return }
    try {
      await guardar.mutateAsync({ name: nuevo.name.trim(), counts_as: nuevo.counts_as })
      setNuevo({ name: '', counts_as: 'OTHER' })
      setErrorNuevo('')
    } catch (err) {
      setErrorNuevo(apiErrorMessage(err))
    }
  }

  function cambiar(tipo, datos) {
    setErrorFila(null)
    guardar.mutate({ id: tipo.id, ...datos }, {
      onError: (err) => setErrorFila({ id: tipo.id, mensaje: apiErrorMessage(err) }),
    })
  }

  return (
    <div className="space-y-5 max-w-5xl">
      <div>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Tipos de tarea</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Los que se eligen en las tareas de los protocolos y en las OTs. «Cuenta como» decide en qué indicador entra cada uno.
        </p>
      </div>

      <form onSubmit={agregar} className="bg-white rounded-xl border border-gray-200 shadow-card p-4 flex flex-wrap items-end gap-3">
        <label className="flex-1 min-w-[16rem]">
          <span className="block text-xs font-medium text-gray-600 mb-1">Nuevo tipo</span>
          <input value={nuevo.name} onChange={(e) => { setNuevo((n) => ({ ...n, name: e.target.value })); setErrorNuevo('') }}
            placeholder="Ej: Revisión de válvulas" className="input-field" />
        </label>
        <label>
          <span className="block text-xs font-medium text-gray-600 mb-1">Cuenta como</span>
          <select value={nuevo.counts_as} onChange={(e) => setNuevo((n) => ({ ...n, counts_as: e.target.value }))} className="input-field w-40">
            {COUNTS_AS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </label>
        <button type="submit" disabled={guardar.isPending} className="btn-primary">Agregar</button>
        {errorNuevo && <p className="w-full text-sm text-red-600">{errorNuevo}</p>}
      </form>

      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : isError ? (
          <p className="text-center py-16 text-sm text-red-600">No se pudo cargar el catálogo. Revisa tu conexión e intenta de nuevo.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[44rem]">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500">
                  <th className="px-4 py-3">Tipo</th>
                  <th className="px-4 py-3">Cuenta como</th>
                  <th className="px-4 py-3 text-right">En uso</th>
                  <th className="px-4 py-3 text-center">Activo</th>
                  <th className="px-4 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {tipos.map((t) => {
                  const fijo = ['PREVENTIVE', 'CORRECTIVE'].includes(t.code)
                  return (
                    <tr key={t.id} className={`align-top ${t.is_active ? '' : 'bg-gray-50/60'}`}>
                      <td className="px-4 py-3">
                        <p className={`font-medium ${t.is_active ? 'text-gray-800' : 'text-gray-500'}`}>{t.name}</p>
                        <p className="text-xs text-gray-500 font-mono">
                          {t.code}{t.is_system && <span className="font-sans"> · del sistema</span>}
                        </p>
                        {errorFila?.id === t.id && <p className="text-xs text-red-600 mt-1">{errorFila.mensaje}</p>}
                      </td>
                      <td className="px-4 py-3">
                        <select value={t.counts_as} disabled={fijo} aria-label={`Cuenta como, ${t.name}`}
                          title={fijo ? `${t.name} siempre cuenta así` : COUNTS_AS.find((c) => c.value === t.counts_as)?.hint}
                          onChange={(e) => cambiar(t, { counts_as: e.target.value })}
                          className="input-field w-36 py-1.5 disabled:bg-gray-50 disabled:text-gray-500">
                          {COUNTS_AS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                        </select>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-gray-600">{t.in_use ?? '—'}</td>
                      <td className="px-4 py-3 text-center">
                        <input type="checkbox" checked={t.is_active} disabled={t.is_system}
                          aria-label={`Activo, ${t.name}`}
                          title={t.is_system ? 'Los tipos del sistema no se desactivan' : undefined}
                          onChange={(e) => cambiar(t, { is_active: e.target.checked })} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <button type="button" onClick={() => setRenombrando(t)}
                            className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200">Renombrar</button>
                          {!t.is_system && t.in_use === 0 && (
                            <button type="button" onClick={() => setBorrando(t)}
                              className="text-xs px-2 py-1 rounded bg-red-50 text-red-700 hover:bg-red-100">Borrar</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <p className="text-xs text-gray-500">
        Un tipo en uso no se borra: desactívalo y deja de ofrecerse, pero las tareas y OTs que ya lo tienen lo conservan.
      </p>

      {renombrando && <RenombrarModal tipo={renombrando} onClose={() => setRenombrando(null)} />}
      {borrando && <BorrarModal tipo={borrando} onClose={() => setBorrando(null)} />}
    </div>
  )
}

function RenombrarModal({ tipo, onClose }) {
  const guardar = useSaveTaskType()
  const [name, setName] = useState(tipo.name)
  return (
    <Modal title="Renombrar tipo" subtitle="El código no cambia: las tareas y OTs que lo usan siguen igual." onClose={onClose}>
      <form className="space-y-4" onSubmit={(e) => {
        e.preventDefault()
        guardar.mutate({ id: tipo.id, name: name.trim() }, { onSuccess: onClose })
      }}>
        <input value={name} onChange={(e) => setName(e.target.value)} className="input-field" aria-label="Nombre" autoFocus />
        {guardar.isError && <p className="text-sm text-red-600">{apiErrorMessage(guardar.error)}</p>}
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
          <button type="submit" disabled={!name.trim() || guardar.isPending} className="btn-primary">Guardar</button>
        </div>
      </form>
    </Modal>
  )
}

function BorrarModal({ tipo, onClose }) {
  const borrar = useDeleteTaskType()
  return (
    <Modal title="Borrar tipo" onClose={onClose}>
      <p className="text-sm text-gray-700">¿Borrar <strong>{tipo.name}</strong>? Ninguna tarea ni OT lo usa.</p>
      {borrar.isError && <p className="text-sm text-red-600 mt-3">{apiErrorMessage(borrar.error)}</p>}
      <div className="flex justify-end gap-3 pt-5">
        <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
        <button type="button" disabled={borrar.isPending} onClick={() => borrar.mutate(tipo.id, { onSuccess: onClose })}
          className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-50">
          Borrar
        </button>
      </div>
    </Modal>
  )
}
