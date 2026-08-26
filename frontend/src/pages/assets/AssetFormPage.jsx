import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useHospitals, useAsset, useAssetTree, useCreateAsset, useUpdateAsset } from '../../api/assets'
import Icon from '../../components/ui/Icon'

const EMPTY = {
  hospital: '',
  node: '',
  name: '',
  code: '',
  asset_type: '',
  status: 'ACTIVE',
  priority: 'MEDIUM',
  manufacturer: '',
  model: '',
  serial_number: '',
  purchase_date: '',
  installation_date: '',
  warranty_expiry: '',
  supplier: '',
  avg_daily_usage_hours: '',
  notes: '',
}

function flattenTree(nodes, depth = 0) {
  const result = []
  for (const node of nodes) {
    result.push({ ...node, depth })
    if (node.children?.length) {
      result.push(...flattenTree(node.children, depth + 1))
    }
  }
  return result
}

function generateCode(hospitalCode, assetType) {
  const base = [
    hospitalCode?.slice(0, 3).toUpperCase() ?? 'XXX',
    assetType?.slice(0, 3).toUpperCase() ?? 'EQP',
    String(Date.now()).slice(-4),
  ].join('-')
  return base
}

export default function AssetFormPage() {
  const { id } = useParams()
  const isEdit = !!id
  const navigate = useNavigate()

  const [step, setStep] = useState(1)
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})

  const { data: hospitals = [] } = useHospitals({ is_active: true })
  const { data: tree = [] } = useAssetTree(form.hospital || null)
  const { data: existing, isLoading: loadingExisting } = useAsset(id)

  const createMut = useCreateAsset()
  const updateMut = useUpdateAsset(id)
  const mut = isEdit ? updateMut : createMut
  const saving = mut.isPending

  const flatNodes = flattenTree(tree)
  const selectedHospital = hospitals.find((h) => h.id === form.hospital)

  useEffect(() => {
    if (isEdit && existing) {
      setForm({
        hospital: existing.hospital?.id ?? '',
        node: existing.node?.id ?? '',
        name: existing.name ?? '',
        code: existing.code ?? '',
        asset_type: existing.asset_type ?? '',
        status: existing.status ?? 'ACTIVE',
        priority: existing.priority ?? 'MEDIUM',
        manufacturer: existing.manufacturer ?? '',
        model: existing.model ?? '',
        serial_number: existing.serial_number ?? '',
        purchase_date: existing.purchase_date ?? '',
        installation_date: existing.installation_date ?? '',
        warranty_expiry: existing.warranty_expiry ?? '',
        supplier: existing.supplier ?? '',
        avg_daily_usage_hours: existing.avg_daily_usage_hours ?? '',
        notes: existing.notes ?? '',
      })
    }
  }, [isEdit, existing])

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
    setErrors((e) => ({ ...e, [field]: undefined }))
  }

  function validateStep1() {
    const errs = {}
    if (!form.hospital) errs.hospital = 'Selecciona un hospital'
    if (!form.name.trim()) errs.name = 'El nombre es obligatorio'
    if (!form.code.trim()) errs.code = 'El código es obligatorio'
    if (!form.status) errs.status = 'El estado es obligatorio'
    if (!form.priority) errs.priority = 'La prioridad es obligatoria'
    return errs
  }

  function handleNext() {
    const errs = validateStep1()
    if (Object.keys(errs).length) { setErrors(errs); return }
    setStep(2)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const payload = { ...form }
    if (!payload.node) delete payload.node
    if (!payload.avg_daily_usage_hours) delete payload.avg_daily_usage_hours
    if (!payload.purchase_date) delete payload.purchase_date
    if (!payload.installation_date) delete payload.installation_date
    if (!payload.warranty_expiry) delete payload.warranty_expiry

    try {
      const result = await mut.mutateAsync(payload)
      navigate(`/activos/${result.id ?? id}`)
    } catch (err) {
      const data = err?.response?.data ?? {}
      const serverErrors = {}
      Object.entries(data).forEach(([k, v]) => {
        serverErrors[k] = Array.isArray(v) ? v.join(' ') : String(v)
      })
      setErrors(serverErrors)
      // Si el error es del paso 1, volver atrás
      const step1Fields = ['hospital', 'node', 'name', 'code', 'asset_type', 'status', 'priority']
      if (step1Fields.some((f) => serverErrors[f])) setStep(1)
    }
  }

  if (isEdit && loadingExisting) {
    return <div className="flex justify-center py-20"><Spinner className="w-10 h-10 text-brand" /></div>
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <nav className="text-sm text-gray-500 flex gap-1 mb-2">
          <button onClick={() => navigate('/activos')} className="hover:text-brand">Activos</button>
          <span>/</span>
          <span className="text-gray-600">{isEdit ? 'Editar activo' : 'Nuevo activo'}</span>
        </nav>
        <h1 className="text-2xl font-bold text-gray-800">{isEdit ? 'Editar activo' : 'Registrar activo'}</h1>
      </div>

      {/* Indicador de pasos */}
      <div className="flex items-center gap-3">
        {[1, 2].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-semibold
              ${step === s ? 'bg-brand text-white' : step > s ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'}`}>
              {step > s ? <Icon name="check" className="w-4 h-4" /> : s}
            </div>
            <span className={`text-sm ${step === s ? 'text-brand font-medium' : 'text-gray-500'}`}>
              {s === 1 ? 'Identificación' : 'Ficha técnica'}
            </span>
            {s < 2 && <Icon name="arrowNarrowRight" className="w-4 h-4 text-gray-400 mx-1" />}
          </div>
        ))}
      </div>

      {/* Formulario */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <form onSubmit={handleSubmit}>
          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-gray-700 mb-4">Identificación del activo</h2>

              <Field label="Hospital *" error={errors.hospital}>
                <select value={form.hospital} onChange={(e) => { set('hospital', e.target.value); set('node', '') }}
                  className={sel(errors.hospital)}>
                  <option value="">Selecciona un hospital</option>
                  {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
                </select>
              </Field>

              <Field label="Ubicación" error={errors.node}>
                <select value={form.node} onChange={(e) => set('node', e.target.value)}
                  disabled={!form.hospital} className={sel(errors.node)}>
                  <option value="">Sin ubicación específica</option>
                  {flatNodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {'  '.repeat(n.depth)}{n.name}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="Nombre del activo *" error={errors.name}>
                <input value={form.name} onChange={(e) => set('name', e.target.value)}
                  className={inp(errors.name)} placeholder="Ventilador mecánico" />
              </Field>

              <div className="grid grid-cols-2 gap-4">
                <Field label="Código interno *" error={errors.code}>
                  <div className="flex gap-1">
                    <input value={form.code} onChange={(e) => set('code', e.target.value)}
                      className={`${inp(errors.code)} flex-1`} placeholder="VEN-001" />
                    <button type="button"
                      onClick={() => set('code', generateCode(selectedHospital?.code, form.asset_type))}
                      className="px-2.5 py-2 text-xs bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 whitespace-nowrap flex-shrink-0">
                      Generar
                    </button>
                  </div>
                </Field>
                <Field label="Tipo de activo" error={errors.asset_type}>
                  <input value={form.asset_type} onChange={(e) => set('asset_type', e.target.value)}
                    className={inp()} placeholder="Ventilador, Monitor, etc." />
                </Field>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Field label="Estado *" error={errors.status}>
                  <select value={form.status} onChange={(e) => set('status', e.target.value)}
                    className={sel(errors.status)}>
                    <option value="ACTIVE">Activo</option>
                    <option value="OUT_OF_SERVICE">Fuera de servicio</option>
                    <option value="DECOMMISSIONED">Dado de baja</option>
                  </select>
                </Field>
                <Field label="Prioridad *" error={errors.priority}>
                  <select value={form.priority} onChange={(e) => set('priority', e.target.value)}
                    className={sel(errors.priority)}>
                    <option value="HIGH">Alta</option>
                    <option value="MEDIUM">Media</option>
                    <option value="LOW">Baja</option>
                  </select>
                </Field>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-gray-700 mb-4">Ficha técnica</h2>

              <div className="grid grid-cols-2 gap-4">
                <Field label="Fabricante" error={errors.manufacturer}>
                  <input value={form.manufacturer} onChange={(e) => set('manufacturer', e.target.value)}
                    className={inp()} placeholder="Philips" />
                </Field>
                <Field label="Modelo" error={errors.model}>
                  <input value={form.model} onChange={(e) => set('model', e.target.value)}
                    className={inp()} placeholder="V60" />
                </Field>
                <Field label="Número de serie" error={errors.serial_number}>
                  <input value={form.serial_number} onChange={(e) => set('serial_number', e.target.value)}
                    className={inp()} placeholder="SN-ABC-12345" />
                </Field>
                <Field label="Proveedor" error={errors.supplier}>
                  <input value={form.supplier} onChange={(e) => set('supplier', e.target.value)}
                    className={inp()} />
                </Field>
                <Field label="Fecha de compra" error={errors.purchase_date}>
                  <input type="date" value={form.purchase_date}
                    onChange={(e) => set('purchase_date', e.target.value)} className={inp()} />
                </Field>
                <Field label="Fecha de instalación" error={errors.installation_date}>
                  <input type="date" value={form.installation_date}
                    onChange={(e) => set('installation_date', e.target.value)} className={inp()} />
                </Field>
                <Field label="Garantía hasta" error={errors.warranty_expiry}>
                  <input type="date" value={form.warranty_expiry}
                    onChange={(e) => set('warranty_expiry', e.target.value)} className={inp()} />
                </Field>
                <Field label="Horas de uso promedio/día" error={errors.avg_daily_usage_hours}>
                  <input type="number" step="0.1" min="0" max="24"
                    value={form.avg_daily_usage_hours}
                    onChange={(e) => set('avg_daily_usage_hours', e.target.value)}
                    className={inp()} placeholder="8" />
                </Field>
              </div>

              <Field label="Notas" error={errors.notes}>
                <textarea value={form.notes} onChange={(e) => set('notes', e.target.value)}
                  rows={3} className={inp()} placeholder="Observaciones adicionales..." />
              </Field>

              {errors.non_field_errors && (
                <p className="text-sm text-red-600">{errors.non_field_errors}</p>
              )}
            </div>
          )}

          {/* Botones */}
          <div className="flex justify-between items-center mt-8 pt-4 border-t">
            <button type="button" onClick={() => navigate('/activos')}
              className="text-sm text-gray-500 hover:text-gray-700">
              Cancelar
            </button>
            <div className="flex gap-3">
              {step === 2 && (
                <button type="button" onClick={() => setStep(1)} className="btn-secondary">
                  <Icon name="chevronLeft" className="w-4 h-4" />
                  Anterior
                </button>
              )}
              {step === 1 ? (
                <button type="button" onClick={handleNext} className="btn-primary">
                  Siguiente
                  <Icon name="chevronRight" className="w-4 h-4" />
                </button>
              ) : (
                <button type="submit" disabled={saving}
                  className="btn-primary">
                  {saving && <Spinner />}
                  {isEdit ? 'Guardar cambios' : 'Crear activo'}
                </button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

function Field({ label, error, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
      {error && <p className="text-xs text-red-500 mt-0.5">{error}</p>}
    </div>
  )
}

const BASE = 'input-field disabled:bg-gray-50 disabled:text-gray-500'
const inp = (hasError) => `${BASE} ${hasError ? 'border-red-400' : ''}`
const sel = (hasError) => `${BASE} bg-white ${hasError ? 'border-red-400' : ''}`

function Spinner({ className = 'w-4 h-4 text-white' }) {
  return (
    <svg className={`animate-spin ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}
