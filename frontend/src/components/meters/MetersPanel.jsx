import { useState } from 'react'
import { Link } from 'react-router-dom'

import {
  formatReading,
  useCreateMeter,
  useCreateReading,
  useDeleteReading,
  useMeterReadings,
  useMeterUnits,
  useMeters,
} from '../../api/meters'
import useAuthStore from '../../store/authStore'
import { apiErrorMessage } from '../../utils/apiError'
import EmptyState from '../ui/EmptyState'
import Modal from '../ui/Modal'
import Spinner from '../ui/Spinner'

const fechaHora = (iso) => new Date(iso).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })

/**
 * Medidores del equipo (decisión del 2026-09-24): la última lectura de cada
 * uno, cómo van las tareas del plan que se activan por uso o por umbral, y el
 * historial. Las lecturas llegan del checklist; el supervisor también las
 * registra a mano.
 */
export default function MetersPanel({ assetId }) {
  const puedeRegistrar = useAuthStore((s) => ['ADMIN', 'SUP'].includes(s.user?.role))
  const { data: medidores = [], isLoading } = useMeters(assetId)
  const [registrando, setRegistrando] = useState(null)
  const [abierto, setAbierto] = useState(null)
  const [agregando, setAgregando] = useState(false)

  if (isLoading) return <div className="flex justify-center py-10"><Spinner /></div>

  return (
    <div className="space-y-4">
      {medidores.length === 0 ? (
        <EmptyState compact icon="gauge" title="Sin medidores"
          description="Aparecen solos con la primera lectura del checklist (campo «Lectura de medidor» con unidad). También puedes agregar uno para registrar a mano." />
      ) : (
        <ul className="space-y-3">
          {medidores.map((m) => (
            <li key={m.id} className="border border-gray-200 rounded-xl">
              <div className="p-4 flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0 space-y-1">
                  <p className="text-sm font-medium text-gray-800">
                    {m.unit_info.label}
                    {m.unit_info.is_counter && <span className="ml-2 text-xs text-gray-500 font-normal">contador</span>}
                  </p>
                  {m.last_reading ? (
                    <p className="text-sm text-gray-700">
                      <span className="text-lg font-semibold tabular-nums">{formatReading(m.last_reading.value)}</span>{' '}
                      {m.unit_info.symbol}
                      <span className="text-xs text-gray-500"> · {fechaHora(m.last_reading.read_at)}</span>
                    </p>
                  ) : (
                    <p className="text-sm text-gray-500">Sin lecturas</p>
                  )}
                  {m.triggers.map((t) => <Activador key={t.plan_task} t={t} symbol={m.unit_info.symbol} />)}
                </div>
                <div className="flex gap-2">
                  <button type="button" onClick={() => setAbierto(abierto === m.id ? null : m.id)}
                    className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200">
                    {abierto === m.id ? 'Ocultar historial' : 'Historial'}
                  </button>
                  {puedeRegistrar && (
                    <button type="button" onClick={() => setRegistrando(m)}
                      className="text-xs px-2 py-1 rounded bg-brand/10 text-brand hover:bg-brand/20">
                      Registrar lectura
                    </button>
                  )}
                </div>
              </div>
              {abierto === m.id && <Historial meter={m} puedeBorrar={puedeRegistrar} />}
            </li>
          ))}
        </ul>
      )}

      {puedeRegistrar && (
        <button type="button" onClick={() => setAgregando(true)} className="btn-secondary text-sm">
          + Agregar medidor
        </button>
      )}
      {registrando && <LecturaModal meter={registrando} onClose={() => setRegistrando(null)} />}
      {agregando && (
        <AgregarModal assetId={assetId} yaTiene={medidores.map((m) => m.unit)} onClose={() => setAgregando(false)} />
      )}
    </div>
  )
}

function Activador({ t, symbol }) {
  if (t.trigger === 'WHEN') {
    return (
      <p className="text-xs text-gray-600">
        «{t.name}» se abre cuando la lectura sea {t.comparator_display.toLowerCase()} {formatReading(t.threshold)} {symbol}
      </p>
    )
  }
  if (t.next_due === null) {
    return <p className="text-xs text-gray-600">«{t.name}» cada {formatReading(t.interval)} {symbol}: empieza a contar con la primera lectura</p>
  }
  const vencida = t.remaining !== null && t.remaining <= 0
  return (
    <p className={`text-xs ${vencida ? 'text-amber-800' : 'text-gray-600'}`}>
      «{t.name}» cada {formatReading(t.interval)} {symbol}: vence a los {formatReading(t.next_due)} {symbol} de uso
      {t.remaining !== null && (vencida ? ' · alcanzado' : ` · faltan ${formatReading(t.remaining)} ${symbol}`)}
    </p>
  )
}

function Historial({ meter, puedeBorrar }) {
  const { data: lecturas = [], isLoading } = useMeterReadings(meter.id)
  const borrar = useDeleteReading()
  const contador = meter.unit_info.is_counter
  if (isLoading) return <div className="flex justify-center py-6 border-t"><Spinner /></div>
  return (
    <div className="border-t border-gray-100 overflow-x-auto">
      {borrar.isError && <p className="text-xs text-red-600 px-4 pt-3">{apiErrorMessage(borrar.error)}</p>}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 bg-gray-50">
            <th className="px-4 py-2">Fecha</th>
            <th className="px-4 py-2 text-right">Lectura</th>
            {contador && <th className="px-4 py-2 text-right">Uso acumulado</th>}
            <th className="px-4 py-2">Origen</th>
            <th className="px-4 py-2" />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {lecturas.map((r) => (
            <tr key={r.id}>
              <td className="px-4 py-2 whitespace-nowrap text-gray-700">{fechaHora(r.read_at)}</td>
              <td className="px-4 py-2 text-right tabular-nums">
                {formatReading(r.value)} {meter.unit_info.symbol}
                {r.is_reset && <span className="ml-1 text-xs text-amber-700">reinicio</span>}
              </td>
              {contador && <td className="px-4 py-2 text-right tabular-nums text-gray-600">{formatReading(r.accumulated)}</td>}
              <td className="px-4 py-2 text-xs text-gray-600">
                {r.task_info?.work_order ? (
                  <Link to={`/ordenes/${r.task_info.work_order.id}`} className="text-brand hover:underline">{r.task_info.work_order.wo_code}</Link>
                ) : (
                  <>A mano{r.recorded_by_name ? ` · ${r.recorded_by_name}` : ''}</>
                )}
                {r.note && <span className="block text-gray-500">{r.note}</span>}
              </td>
              <td className="px-4 py-2 text-right">
                {puedeBorrar && r.source === 'MANUAL' && !r.opened_task && (
                  <button type="button" onClick={() => borrar.mutate(r.id)} disabled={borrar.isPending}
                    className="text-xs text-red-600 hover:underline">Borrar</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ahoraLocal() {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

function LecturaModal({ meter, onClose }) {
  const crear = useCreateReading()
  const [form, setForm] = useState({ value: '', read_at: ahoraLocal(), is_reset: false, note: '' })
  const contador = meter.unit_info.is_counter
  const ultima = meter.last_reading?.value
  const baja = contador && ultima !== undefined && form.value !== '' && Number(form.value) < ultima

  function guardar(e) {
    e.preventDefault()
    crear.mutate({
      meter: meter.id,
      value: form.value,
      read_at: new Date(form.read_at).toISOString(),
      is_reset: form.is_reset,
      note: form.note.trim(),
    }, { onSuccess: onClose })
  }

  return (
    <Modal title={`Registrar lectura · ${meter.unit_info.label}`} onClose={onClose}>
      <form onSubmit={guardar} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="block text-xs font-medium text-gray-600 mb-1">Lectura ({meter.unit_info.symbol})</span>
            <input type="number" step="any" min="0" required autoFocus value={form.value}
              onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))} className="input-field" />
          </label>
          <label className="block">
            <span className="block text-xs font-medium text-gray-600 mb-1">Fecha y hora</span>
            <input type="datetime-local" required value={form.read_at}
              onChange={(e) => setForm((f) => ({ ...f, read_at: e.target.value }))} className="input-field" />
          </label>
        </div>
        {contador && (
          <label className="flex items-start gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={form.is_reset} className="mt-0.5"
              onChange={(e) => setForm((f) => ({ ...f, is_reset: e.target.checked }))} />
            <span>
              El contador se reinició o se cambió
              <span className="block text-xs text-gray-500">
                {baja && !form.is_reset
                  ? `Es menor que la última (${formatReading(ultima)}): se tomará como un contador que arrancó de cero.`
                  : 'El uso acumulado sigue contando desde esta lectura, sin restar.'}
              </span>
            </span>
          </label>
        )}
        <label className="block">
          <span className="block text-xs font-medium text-gray-600 mb-1">Nota</span>
          <input value={form.note} maxLength={255} onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))}
            placeholder="Opcional" className="input-field" />
        </label>
        {crear.isError && <p className="text-sm text-red-600">{apiErrorMessage(crear.error)}</p>}
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
          <button type="submit" disabled={crear.isPending} className="btn-primary">Guardar</button>
        </div>
      </form>
    </Modal>
  )
}

function AgregarModal({ assetId, yaTiene, onClose }) {
  const { data: unidades = [] } = useMeterUnits({ active: true })
  const crear = useCreateMeter()
  const libres = unidades.filter((u) => !yaTiene.includes(u.id))
  const [unit, setUnit] = useState('')
  return (
    <Modal title="Agregar medidor" onClose={onClose}>
      <form className="space-y-4" onSubmit={(e) => {
        e.preventDefault()
        crear.mutate({ asset: assetId, unit }, { onSuccess: onClose })
      }}>
        <select value={unit} onChange={(e) => setUnit(e.target.value)} required className="input-field" aria-label="Unidad">
          <option value="">Elige la unidad</option>
          {libres.map((u) => <option key={u.id} value={u.id}>{u.label}</option>)}
        </select>
        {crear.isError && <p className="text-sm text-red-600">{apiErrorMessage(crear.error)}</p>}
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
          <button type="submit" disabled={!unit || crear.isPending} className="btn-primary">Agregar</button>
        </div>
      </form>
    </Modal>
  )
}
