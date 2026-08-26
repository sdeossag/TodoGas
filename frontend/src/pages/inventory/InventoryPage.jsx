import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import {
  useInventoryItems,
  useCreateInventoryItem,
  useUpdateInventoryItem,
} from '../../api/inventory'

const UNIT_OPTIONS = ['und', 'kg', 'g', 'l', 'ml', 'mt', 'cm', 'caja', 'rollo', 'par']

function Spinner({ small }) {
  return (
    <svg className={`animate-spin ${small ? 'h-4 w-4' : 'h-8 w-8'} text-brand`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

const EMPTY_FORM = {
  name: '',
  code: '',
  description: '',
  unit_of_measure: 'und',
  min_stock: '',
  unit_cost: '',
  is_active: true,
}

export default function InventoryPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'ADMIN'

  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState(
    searchParams.get('filtro') === 'stock-bajo' ? 'all' : 'all'
  )
  const [lowStockOnly] = useState(searchParams.get('filtro') === 'stock-bajo')
  const [showModal, setShowModal] = useState(false)
  const [editItem, setEditItem] = useState(null)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 400)
    return () => clearTimeout(t)
  }, [search])

  const filters = {}
  if (debouncedSearch) filters.search = debouncedSearch
  if (statusFilter !== 'all') filters.is_active = statusFilter === 'active'

  const { data: items = [], isLoading } = useInventoryItems(filters)

  const displayed = lowStockOnly
    ? items.filter((i) => parseFloat(i.current_stock) <= parseFloat(i.min_stock))
    : items

  function handleEdit(item) {
    setEditItem(item)
    setShowModal(true)
  }

  function handleCreate() {
    setEditItem(null)
    setShowModal(true)
  }

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Inventario</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {displayed.length} {displayed.length === 1 ? 'item' : 'items'}
            {lowStockOnly && <span className="ml-2 text-red-500 font-medium">— Solo stock bajo</span>}
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={handleCreate}
            className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light transition-colors"
          >
            Nuevo item
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex flex-wrap gap-3 items-center">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nombre o codigo..."
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 w-56"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none"
        >
          <option value="all">Todos</option>
          <option value="active">Solo activos</option>
          <option value="inactive">Solo inactivos</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : displayed.length === 0 ? (
          <div className="text-center py-16 text-gray-500 text-sm">No hay items de inventario.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-3">Nombre</th>
                  <th className="px-4 py-3">Codigo</th>
                  <th className="px-4 py-3">Unidad</th>
                  <th className="px-4 py-3">Stock actual</th>
                  <th className="px-4 py-3">Stock minimo</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {displayed.map((item) => {
                  const isLow = parseFloat(item.current_stock) <= parseFloat(item.min_stock)
                  return (
                    <tr key={item.id} className={isLow ? 'bg-yellow-50' : 'hover:bg-gray-50'}>
                      <td className="px-4 py-3 font-medium text-gray-800">
                        {item.name}
                        {isLow && (
                          <span className="ml-2 text-xs px-1.5 py-0.5 bg-red-100 text-red-600 rounded font-medium">
                            Stock bajo
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-600">{item.code}</td>
                      <td className="px-4 py-3 text-gray-500">{item.unit_of_measure}</td>
                      <td className={`px-4 py-3 font-semibold ${isLow ? 'text-red-600' : 'text-gray-800'}`}>
                        {parseFloat(item.current_stock).toLocaleString('es-CO')}
                      </td>
                      <td className="px-4 py-3 text-gray-500">{parseFloat(item.min_stock).toLocaleString('es-CO')}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 text-xs rounded-full font-medium ${
                          item.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                        }`}>
                          {item.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right flex items-center justify-end gap-2">
                        {isAdmin && (
                          <button
                            onClick={() => handleEdit(item)}
                            className="text-xs text-brand hover:underline"
                          >
                            Editar
                          </button>
                        )}
                        <button
                          onClick={() => navigate(`/inventario/${item.id}/movimientos`)}
                          className="text-xs text-gray-500 hover:text-gray-700 border border-gray-200 px-2 py-1 rounded hover:bg-gray-50"
                        >
                          Ver movimientos
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <ItemModal
          item={editItem}
          onClose={() => { setShowModal(false); setEditItem(null) }}
        />
      )}
    </div>
  )
}

function ItemModal({ item, onClose }) {
  const isEdit = !!item
  const createMut = useCreateInventoryItem()
  const updateMut = useUpdateInventoryItem(item?.id)
  const isPending = createMut.isPending || updateMut.isPending

  const [form, setForm] = useState(
    isEdit
      ? {
          name: item.name ?? '',
          code: item.code ?? '',
          description: item.description ?? '',
          unit_of_measure: item.unit_of_measure ?? 'und',
          min_stock: item.min_stock ?? '',
          unit_cost: item.unit_cost ?? '',
          is_active: item.is_active ?? true,
        }
      : { ...EMPTY_FORM }
  )
  const [error, setError] = useState('')

  function set(k, v) { setForm((f) => ({ ...f, [k]: v })) }

  async function handleSave() {
    setError('')
    if (!form.name.trim() || !form.code.trim()) {
      setError('Nombre y codigo son obligatorios.')
      return
    }
    try {
      if (isEdit) {
        await updateMut.mutateAsync(form)
      } else {
        await createMut.mutateAsync(form)
      }
      onClose()
    } catch (err) {
      const detail = err?.response?.data
      if (typeof detail === 'object') {
        setError(Object.values(detail).flat().join(' '))
      } else {
        setError('Error al guardar. Intenta de nuevo.')
      }
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold text-gray-800 mb-5">
          {isEdit ? 'Editar item' : 'Nuevo item de inventario'}
        </h3>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <F label="Nombre *">
              <input value={form.name} onChange={(e) => set('name', e.target.value)}
                className={inp} placeholder="Filtro HEPA" />
            </F>
            <F label="Codigo *">
              <input value={form.code} onChange={(e) => set('code', e.target.value)}
                disabled={isEdit}
                className={`${inp} ${isEdit ? 'bg-gray-50 text-gray-500' : ''}`}
                placeholder="FH-001" />
            </F>
          </div>

          <F label="Descripcion">
            <textarea rows={2} value={form.description}
              onChange={(e) => set('description', e.target.value)}
              className={`${inp} resize-none`} />
          </F>

          <div className="grid grid-cols-3 gap-4">
            <F label="Unidad de medida">
              <select value={form.unit_of_measure} onChange={(e) => set('unit_of_measure', e.target.value)}
                className={inp}>
                {UNIT_OPTIONS.map((u) => <option key={u} value={u}>{u}</option>)}
              </select>
            </F>
            <F label="Stock minimo">
              <input type="number" min="0" step="0.01" value={form.min_stock}
                onChange={(e) => set('min_stock', e.target.value)}
                className={inp} placeholder="0" />
            </F>
            <F label="Costo unitario">
              <input type="number" min="0" step="0.01" value={form.unit_cost}
                onChange={(e) => set('unit_cost', e.target.value)}
                className={inp} placeholder="0" />
            </F>
          </div>

          {isEdit && (
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input type="checkbox" checked={form.is_active}
                onChange={(e) => set('is_active', e.target.checked)}
                className="rounded border-gray-300 text-brand focus:ring-brand" />
              Activo
            </label>
          )}

          {error && <p className="text-sm text-red-500 bg-red-50 rounded px-3 py-2">{error}</p>}
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={isPending}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60"
          >
            {isPending && <Spinner small />}
            {isEdit ? 'Guardar cambios' : 'Crear item'}
          </button>
        </div>
      </div>
    </div>
  )
}

function F({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  )
}

const inp = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30'
