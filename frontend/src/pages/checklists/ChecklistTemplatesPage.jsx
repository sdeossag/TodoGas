import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'
import { useChecklistTemplates, useCreateChecklistTemplate } from '../../api/checklists'
import Icon from '../../components/ui/Icon'

function Spinner() {
  return (
    <svg className="animate-spin h-8 w-8 text-brand" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

const FILTERS = [
  { value: '', label: 'Todas' },
  { value: 'active', label: 'Activas' },
  { value: 'inactive', label: 'Inactivas' },
]

export default function ChecklistTemplatesPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'ADMIN'

  const [showModal, setShowModal] = useState(false)
  const [filter, setFilter] = useState('')

  const params =
    filter === 'active' ? { is_active: true } : filter === 'inactive' ? { is_active: false } : {}
  const { data: templates = [], isLoading } = useChecklistTemplates(params)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Checklists</h1>
          <p className="text-sm text-gray-500 mt-0.5">{templates.length} plantillas</p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light transition-colors"
          >
            + Nueva plantilla
          </button>
        )}
      </div>

      {/* Filtros */}
      <div className="flex gap-2">
        {FILTERS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setFilter(value)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              filter === value
                ? 'bg-brand text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Spinner />
          </div>
        ) : templates.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <Icon name="checklist" className="w-10 h-10 mx-auto mb-3 text-gray-400" />
            <p className="font-medium">No hay plantillas de checklist</p>
            {isAdmin && (
              <button
                onClick={() => setShowModal(true)}
                className="mt-3 text-sm text-brand hover:underline"
              >
                + Crear la primera plantilla
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-3">Nombre</th>
                  <th className="px-4 py-3">Versión actual</th>
                  <th className="px-4 py-3">Campos</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {templates.map((t) => (
                  <tr key={t.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-800">{t.name}</p>
                      {t.description && (
                        <p className="text-xs text-gray-500 mt-0.5 truncate max-w-xs">
                          {t.description}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {t.current_version_number ? `v${t.current_version_number}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{t.fields_count ?? 0}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          t.is_active
                            ? 'bg-green-50 text-green-700'
                            : 'bg-gray-100 text-gray-500'
                        }`}
                      >
                        {t.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {isAdmin && (
                        <button
                          onClick={() => navigate(`/checklists/${t.id}/editar`)}
                          className="text-xs px-3 py-1.5 rounded-lg bg-brand/10 text-brand hover:bg-brand/20 transition-colors"
                        >
                          Editar
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <CreateTemplateModal
          onClose={() => setShowModal(false)}
          onCreated={(id) => {
            setShowModal(false)
            navigate(`/checklists/${id}/editar`)
          }}
        />
      )}
    </div>
  )
}

// ── Modal de creación ────────────────────────────────────────────────────────

function CreateTemplateModal({ onClose, onCreated }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const createMut = useCreateChecklistTemplate()

  async function handleCreate() {
    if (!name.trim()) {
      setError('El nombre es requerido')
      return
    }
    try {
      const t = await createMut.mutateAsync({ name: name.trim(), description: description.trim() })
      onCreated(t.id)
    } catch (err) {
      const detail = err?.response?.data
      if (detail && typeof detail === 'object') {
        setError(Object.values(detail).flat().join(' '))
      } else {
        setError('Error al crear la plantilla')
      }
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4 space-y-4">
        <h3 className="text-lg font-semibold text-gray-800">Nueva plantilla de checklist</h3>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Nombre <span className="text-red-500">*</span>
          </label>
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            placeholder="Ej: Verificación de cilindros de O₂"
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
          <textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Descripción opcional..."
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 resize-none"
          />
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <div className="flex justify-end gap-3 pt-1">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancelar
          </button>
          <button
            onClick={handleCreate}
            disabled={createMut.isPending}
            className="px-5 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-60 transition-colors"
          >
            {createMut.isPending ? 'Creando...' : 'Crear y editar'}
          </button>
        </div>
      </div>
    </div>
  )
}
