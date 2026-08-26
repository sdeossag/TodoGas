import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import { useInventoryItem, useStockMovements, useCreateStockMovement } from '../../api/inventory'

const MOVEMENT_LABELS = {
  IN: 'Entrada',
  OUT: 'Salida',
  ADJUSTMENT: 'Ajuste',
}
const MOVEMENT_COLORS = {
  IN: 'bg-green-100 text-green-700',
  OUT: 'bg-red-100 text-red-600',
  ADJUSTMENT: 'bg-gray-100 text-gray-600',
}

const PAGE_SIZE = 50

function Spinner({ small }) {
  return (
    <svg className={`animate-spin ${small ? 'h-4 w-4' : 'h-8 w-8'} text-brand`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

export default function ItemMovementsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'ADMIN'

  const [page, setPage] = useState(1)
  const [showModal, setShowModal] = useState(false)

  const { data: item, isLoading: itemLoading } = useInventoryItem(id)
  const { data: movements = [], isLoading: movLoading } = useStockMovements({ item_id: id })

  const totalPages = Math.max(1, Math.ceil(movements.length / PAGE_SIZE))
  const paginated = movements.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  if (itemLoading) return <div className="flex justify-center py-20"><Spinner /></div>
  if (!item) return <p className="text-gray-500 text-center py-20">Item no encontrado.</p>

  return (
    <div className="space-y-6 max-w-5xl">
      <nav className="text-sm text-gray-500 flex gap-1">
        <button onClick={() => navigate('/inventario')} className="hover:text-brand">
          Inventario
        </button>
        <span>/</span>
        <span className="text-gray-600">{item.name}</span>
      </nav>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs font-mono text-gray-500 mb-1">{item.code}</p>
          <h1 className="text-xl font-bold text-gray-800">{item.name}</h1>
          <p className="text-sm text-gray-500 mt-1">{item.unit_of_measure}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Stock actual</p>
          <p className={`text-4xl font-bold ${item.is_low_stock ? 'text-red-600' : 'text-brand'}`}>
            {parseFloat(item.current_stock).toLocaleString('es-CO')}
          </p>
          <p className="text-xs text-gray-500">Min: {parseFloat(item.min_stock).toLocaleString('es-CO')}</p>
          {item.is_low_stock && (
            <span className="inline-flex mt-1 text-xs px-2 py-0.5 bg-red-100 text-red-600 rounded-full font-medium">
              Stock bajo
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Movimientos</h2>
        {isAdmin && (
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light transition-colors"
          >
            Registrar movimiento
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        {movLoading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : movements.length === 0 ? (
          <div className="text-center py-12 text-gray-500 text-sm">Sin movimientos registrados.</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-4 py-3">Fecha</th>
                    <th className="px-4 py-3">Tipo</th>
                    <th className="px-4 py-3">Cantidad</th>
                    <th className="px-4 py-3">OT relacionada</th>
                    <th className="px-4 py-3">Referencia</th>
                    <th className="px-4 py-3">Registrado por</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {paginated.map((mov) => (
                    <tr key={mov.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {new Date(mov.performed_at).toLocaleString('es-CO')}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 text-xs rounded-full font-medium ${MOVEMENT_COLORS[mov.movement_type] ?? 'bg-gray-100 text-gray-500'}`}>
                          {MOVEMENT_LABELS[mov.movement_type] ?? mov.movement_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-semibold text-gray-800">
                        {parseFloat(mov.quantity).toLocaleString('es-CO')}
                      </td>
                      <td className="px-4 py-3">
                        {mov.work_order ? (
                          <button
                            onClick={() => navigate(`/ordenes/${mov.work_order.id}`)}
                            className="text-xs text-brand hover:underline font-mono"
                          >
                            OT-{mov.work_order.wo_number}
                          </button>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs truncate max-w-[120px]">
                        {mov.reference || '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {mov.performed_by?.full_name || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
                <span className="text-xs text-gray-500">
                  Pagina {page} de {totalPages} ({movements.length} movimientos)
                </span>
                <div className="flex gap-1">
                  <button disabled={page === 1} onClick={() => setPage((p) => p - 1)}
                    className="px-3 py-1.5 text-xs rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50">
                    Anterior
                  </button>
                  <button disabled={page === totalPages} onClick={() => setPage((p) => p + 1)}
                    className="px-3 py-1.5 text-xs rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50">
                    Siguiente
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {showModal && (
        <MovementModal
          item={item}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}

function MovementModal({ item, onClose }) {
  const createMut = useCreateStockMovement()
  const [form, setForm] = useState({
    movement_type: 'IN',
    quantity: '',
    reference: '',
    notes: '',
  })
  const [error, setError] = useState('')
  const [errorTimer, setErrorTimer] = useState(null)

  function set(k, v) { setForm((f) => ({ ...f, [k]: v })) }

  function showError(msg) {
    if (errorTimer) clearTimeout(errorTimer)
    setError(msg)
    const t = setTimeout(() => setError(''), 4000)
    setErrorTimer(t)
  }

  async function handleSave() {
    setError('')
    const qty = parseFloat(form.quantity)
    if (!form.quantity || isNaN(qty) || qty <= 0) {
      showError('Ingresa una cantidad valida mayor que cero.')
      return
    }
    try {
      await createMut.mutateAsync({
        item: item.id,
        movement_type: form.movement_type,
        quantity: form.quantity,
        reference: form.reference,
        notes: form.notes,
      })
      onClose()
    } catch (err) {
      const detail = err?.response?.data
      if (typeof detail === 'string') {
        showError(detail)
      } else if (typeof detail === 'object') {
        const msgs = Object.values(detail).flat()
        showError(msgs.join(' '))
      } else {
        showError('Error al registrar el movimiento.')
      }
    }
  }

  const inp = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
        <h3 className="text-lg font-semibold text-gray-800 mb-1">Registrar movimiento</h3>
        <p className="text-xs text-gray-500 mb-5">
          {item.code} — {item.name} | Stock: {parseFloat(item.current_stock).toLocaleString('es-CO')} {item.unit_of_measure}
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tipo de movimiento</label>
            <select value={form.movement_type} onChange={(e) => set('movement_type', e.target.value)} className={inp}>
              <option value="IN">Entrada</option>
              <option value="OUT">Salida</option>
              <option value="ADJUSTMENT">Ajuste (establece cantidad exacta)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Cantidad *</label>
            <input
              type="number" min="0" step="0.01"
              value={form.quantity}
              onChange={(e) => set('quantity', e.target.value)}
              className={inp}
              placeholder="0"
            />
            {error && (
              <p className="mt-1.5 text-xs text-red-500 bg-red-50 rounded px-2 py-1">{error}</p>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Referencia</label>
            <input value={form.reference} onChange={(e) => set('reference', e.target.value)}
              className={inp} placeholder="N° factura, solicitud..." />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notas</label>
            <textarea rows={2} value={form.notes}
              onChange={(e) => set('notes', e.target.value)}
              className={`${inp} resize-none`} />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={createMut.isPending}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60"
          >
            {createMut.isPending && (
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            )}
            Registrar
          </button>
        </div>
      </div>
    </div>
  )
}
