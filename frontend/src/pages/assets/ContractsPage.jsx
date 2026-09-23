import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { useAssets, useAssetTree, useHospitals } from '../../api/assets'
import {
  CONTRACT_KINDS,
  useContracts,
  useContractsSummary,
  useDeleteContract,
  useSaveContract,
} from '../../api/contracts'
import { EstadoDocumento } from '../../components/contracts/ContractStatus'
import EmptyState from '../../components/ui/EmptyState'
import Icon from '../../components/ui/Icon'
import Modal from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import useAuthStore from '../../store/authStore'
import { apiErrorMessage } from '../../utils/apiError'
import { flattenTree, indentedLabel } from '../../utils/locationTree'
import { formatDate } from '../../utils/maintenance'
import { mediaUrl } from '../../api/client'

const VISTAS = [
  { value: 'ACTIVE', label: 'Vigentes' },
  { value: 'EXPIRING', label: 'Por vencer' },
  { value: 'EXPIRED', label: 'Vencidos' },
  { value: 'UPCOMING', label: 'Próximos' },
  { value: '', label: 'Todos' },
]

/**
 * Contratos de mantenimiento con los hospitales y garantías de los equipos
 * (Gestión Documental de Fracttal). El contrato cubre un hospital o una parte
 * de su árbol; la garantía, una lista de equipos. Vencer solo avisa: el
 * hospital queda "sin contrato vigente" y el planificador decide.
 */
export default function ContractsPage() {
  const isAdmin = useAuthStore((s) => s.user?.role === 'ADMIN')
  const [searchParams] = useSearchParams()
  const [vista, setVista] = useState('ACTIVE')
  const [tipo, setTipo] = useState('')
  const [hospital, setHospital] = useState(searchParams.get('hospital_id') ?? '')
  const [buscar, setBuscar] = useState('')
  const [editando, setEditando] = useState(null) // {} nuevo, o el documento
  const [borrando, setBorrando] = useState(null)

  const { data: hospitales = [] } = useHospitals({ is_active: true })
  const { data: resumen } = useContractsSummary()
  const params = {
    ...(vista && { status: vista }),
    ...(tipo && { kind: tipo }),
    ...(hospital && { hospital_id: hospital }),
    ...(buscar.trim() && { search: buscar.trim() }),
  }
  const { data: documentos = [], isLoading, isError } = useContracts(params)
  const sinContrato = resumen?.hospitals_without_contract ?? []

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Contratos y garantías</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Vigencia de los contratos de mantenimiento y de las garantías de equipos.
          </p>
        </div>
        {isAdmin && (
          <button type="button" onClick={() => setEditando({})} className="btn-primary">
            + Nuevo documento
          </button>
        )}
      </div>

      {(resumen?.expiring?.length > 0 || sinContrato.length > 0) && (
        <div className="grid gap-3 sm:grid-cols-2">
          {resumen.expiring.length > 0 && (
            <button type="button" onClick={() => setVista('EXPIRING')}
              className="text-left rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 hover:bg-amber-100/60">
              <p className="text-sm font-medium text-amber-900">
                {resumen.expiring.length} por vencer en 60 días
              </p>
              <p className="text-xs text-amber-800 mt-0.5 truncate">
                {resumen.expiring.slice(0, 3).map((c) => c.name).join(' · ')}
                {resumen.expiring.length > 3 && ' …'}
              </p>
            </button>
          )}
          {sinContrato.length > 0 && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
              <p className="text-sm font-medium text-red-800">
                {sinContrato.length} hospital{sinContrato.length > 1 ? 'es' : ''} sin contrato vigente
              </p>
              <p className="text-xs text-red-700 mt-0.5">
                {sinContrato.slice(0, 4).map((h) => h.name).join(' · ')}
                {sinContrato.length > 4 && ` y ${sinContrato.length - 4} más`}
              </p>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-xl">
          {VISTAS.map((v) => (
            <button key={v.value || 'todos'} type="button" onClick={() => setVista(v.value)}
              className={`px-3 py-1.5 rounded-lg text-sm ${vista === v.value ? 'bg-white shadow-sm font-medium text-gray-900' : 'text-gray-500'}`}>
              {v.label}
            </button>
          ))}
        </div>
        <select value={tipo} onChange={(e) => setTipo(e.target.value)} className="input-field w-56" aria-label="Tipo">
          <option value="">Contratos y garantías</option>
          {CONTRACT_KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
        </select>
        <select value={hospital} onChange={(e) => setHospital(e.target.value)} className="input-field w-56" aria-label="Hospital">
          <option value="">Todos los hospitales</option>
          {hospitales.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
        <input value={buscar} onChange={(e) => setBuscar(e.target.value)} placeholder="Buscar por nombre…"
          aria-label="Buscar" className="input-field w-56" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : isError ? (
          <p className="text-center py-16 text-sm text-red-600">No se pudo cargar el listado. Revisa tu conexión e intenta de nuevo.</p>
        ) : documentos.length === 0 ? (
          <EmptyState icon="document" title="Nada por aquí"
            description={isAdmin ? 'No hay documentos con estos filtros. Carga uno con "Nuevo documento".' : 'No hay documentos con estos filtros.'} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[52rem]">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500">
                  <th className="px-4 py-3">Documento</th>
                  <th className="px-4 py-3">Cubre</th>
                  <th className="px-4 py-3">Vigencia</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {documentos.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50 align-top">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-800">{c.name}</p>
                      <p className="text-xs text-gray-500">{c.kind_display}</p>
                      {c.description && <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{c.description}</p>}
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-gray-800">{c.hospital_name}</p>
                      <p className="text-xs text-gray-500">
                        {c.kind === 'WARRANTY'
                          ? `${c.assets_info.length} equipo${c.assets_info.length !== 1 ? 's' : ''}: ${c.assets_info.slice(0, 3).map((a) => a.code).join(', ')}${c.assets_info.length > 3 ? '…' : ''}`
                          : c.node_path || 'Todo el hospital'}
                      </p>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-gray-700">
                      {formatDate(c.start_date)} → {formatDate(c.end_date)}
                    </td>
                    <td className="px-4 py-3">
                      <EstadoDocumento doc={c} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        {c.file_url && (
                          <a href={mediaUrl(c.file_url)} target="_blank" rel="noreferrer"
                            className="text-xs px-2 py-1 rounded bg-brand/10 text-brand hover:bg-brand/20 inline-flex items-center gap-1">
                            <Icon name="download" className="w-3.5 h-3.5" /> Documento
                          </a>
                        )}
                        {isAdmin && (
                          <>
                            <button type="button" onClick={() => setEditando(c)}
                              className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200">Editar</button>
                            <button type="button" onClick={() => setBorrando(c)}
                              className="text-xs px-2 py-1 rounded bg-red-50 text-red-700 hover:bg-red-100">Eliminar</button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editando && <ContractModal doc={editando.id ? editando : null} hospitalInicial={hospital} onClose={() => setEditando(null)} />}
      {borrando && <DeleteModal doc={borrando} onClose={() => setBorrando(null)} />}
    </div>
  )
}

/** Un año de vigencia menos un día, como los contratos del cliente (2025-04-28 → 2026-04-27). */
function unAnio(inicio) {
  const [y, m, d] = inicio.split('-').map(Number)
  const fin = new Date(y + 1, m - 1, d - 1)
  const pad = (n) => String(n).padStart(2, '0')
  return `${fin.getFullYear()}-${pad(fin.getMonth() + 1)}-${pad(fin.getDate())}`
}

function ContractModal({ doc, hospitalInicial, onClose }) {
  const esNuevo = !doc
  const [form, setForm] = useState(() => ({
    kind: doc?.kind ?? 'MAINTENANCE',
    name: doc?.name ?? '',
    description: doc?.description ?? '',
    hospital: doc?.hospital ?? hospitalInicial ?? '',
    node: doc?.node ?? '',
    start_date: doc?.start_date ?? '',
    end_date: doc?.end_date ?? '',
  }))
  const [equipos, setEquipos] = useState(() => new Map((doc?.assets_info ?? []).map((a) => [a.id, a])))
  const [archivo, setArchivo] = useState(null)
  const [quitarArchivo, setQuitarArchivo] = useState(false)
  const [errores, setErrores] = useState({})
  const guardar = useSaveContract()
  const { data: hospitales = [] } = useHospitals({ is_active: true })
  const { data: tree = [] } = useAssetTree(form.kind === 'MAINTENANCE' ? form.hospital : null)
  const nodos = useMemo(() => flattenTree(tree), [tree])
  const garantia = form.kind === 'WARRANTY'

  function set(campo, valor) {
    setForm((f) => ({ ...f, [campo]: valor }))
    setErrores((e) => ({ ...e, [campo]: undefined }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const errs = {}
    if (!form.name.trim()) errs.name = 'Ponle un nombre'
    if (!form.hospital) errs.hospital = 'Elige el hospital'
    if (!form.start_date) errs.start_date = 'Falta el inicio'
    if (!form.end_date) errs.end_date = 'Falta el fin'
    if (garantia && equipos.size === 0) errs.asset_ids = 'Elige los equipos que cubre la garantía'
    if (Object.keys(errs).length) { setErrores(errs); return }

    const datos = {
      ...(doc && { id: doc.id }),
      ...(esNuevo && { kind: form.kind }),
      name: form.name.trim(),
      description: form.description,
      hospital: form.hospital,
      start_date: form.start_date,
      end_date: form.end_date,
      ...(garantia ? { asset_ids: [...equipos.keys()] } : { node: form.node || null }),
      ...(archivo && { file: archivo }),
      ...(quitarArchivo && !archivo && { remove_file: true }),
    }
    try {
      await guardar.mutateAsync(datos)
      onClose()
    } catch (err) {
      const data = err?.response?.data
      if (data && typeof data === 'object' && !data.detail) {
        setErrores(Object.fromEntries(
          Object.entries(data).map(([k, v]) => [k, Array.isArray(v) ? v.join(' ') : String(v)])
        ))
      } else {
        setErrores({ general: apiErrorMessage(err) })
      }
    }
  }

  return (
    <Modal title={esNuevo ? 'Nuevo documento' : `Editar «${doc.name}»`} onClose={onClose} width="max-w-2xl">
      <form onSubmit={handleSubmit} className="space-y-4">
        {esNuevo && (
          <div className="flex gap-2" role="radiogroup" aria-label="Tipo de documento">
            {CONTRACT_KINDS.map((k) => (
              <button key={k.value} type="button" role="radio" aria-checked={form.kind === k.value}
                onClick={() => { set('kind', k.value); set('node', '') }}
                className={`flex-1 px-3 py-2 rounded-lg border text-sm ${form.kind === k.value ? 'border-brand bg-brand/5 text-brand font-medium' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
                {k.label}
              </button>
            ))}
          </div>
        )}

        <Campo label="Nombre" error={errores.name}>
          <input value={form.name} onChange={(e) => set('name', e.target.value)} className="input-field"
            placeholder={garantia ? 'GARANTIA COMPRESOR VALMIG' : 'CONTRATO 2026-2027 CLINICA NOEL'} />
        </Campo>
        <Campo label="Descripción" error={errores.description}>
          <textarea value={form.description} onChange={(e) => set('description', e.target.value)}
            rows={2} className="input-field" placeholder="Opcional: alcance, número de visitas, condiciones…" />
        </Campo>

        <div className="grid gap-4 sm:grid-cols-2">
          <Campo label="Hospital" error={errores.hospital}>
            <select value={form.hospital} className="input-field"
              onChange={(e) => { set('hospital', e.target.value); set('node', ''); setEquipos(new Map()) }}>
              <option value="">Elige un hospital</option>
              {hospitales.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
            </select>
          </Campo>
          {!garantia && (
            <Campo label="Cubre" error={errores.node}>
              <select value={form.node} onChange={(e) => set('node', e.target.value)} disabled={!form.hospital} className="input-field">
                <option value="">Todo el hospital</option>
                {nodos.map((n) => <option key={n.id} value={n.id}>{indentedLabel(n.name, n.depth)}</option>)}
              </select>
            </Campo>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Campo label="Inicio de la vigencia" error={errores.start_date}>
            <input type="date" value={form.start_date} className="input-field"
              onChange={(e) => {
                set('start_date', e.target.value)
                if (e.target.value && !form.end_date) set('end_date', unAnio(e.target.value))
              }} />
          </Campo>
          <Campo label="Fin de la vigencia" error={errores.end_date}>
            <input type="date" value={form.end_date} onChange={(e) => set('end_date', e.target.value)} className="input-field" />
            {form.start_date && (
              <button type="button" onClick={() => set('end_date', unAnio(form.start_date))}
                className="text-xs text-brand hover:underline mt-1">Un año desde el inicio</button>
            )}
          </Campo>
        </div>

        {garantia && (
          <SelectorEquipos hospital={form.hospital} equipos={equipos} setEquipos={(m) => { setEquipos(m); setErrores((e) => ({ ...e, asset_ids: undefined })) }}
            error={errores.asset_ids} />
        )}

        <Campo label="Documento (PDF, Word o imagen, hasta 20 MB)" error={errores.file}>
          {doc?.file_url && !quitarArchivo && !archivo && (
            <p className="text-sm text-gray-700 mb-1.5 flex items-center gap-2">
              <a href={mediaUrl(doc.file_url)} target="_blank" rel="noreferrer" className="text-brand hover:underline truncate">{doc.file_name}</a>
              <button type="button" onClick={() => setQuitarArchivo(true)} className="text-xs text-red-600 hover:underline">Quitar</button>
            </p>
          )}
          <input type="file" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
            onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-gray-600 file:mr-3 file:px-3 file:py-1.5 file:rounded-lg file:border-0 file:bg-gray-100 file:text-gray-700" />
          {doc?.file_url && !archivo && !quitarArchivo && (
            <p className="text-xs text-gray-500 mt-1">Si subes otro, reemplaza al actual.</p>
          )}
        </Campo>

        {(errores.general || errores.non_field_errors || errores.kind) && (
          <p className="text-sm text-red-600">{errores.general || errores.non_field_errors || errores.kind}</p>
        )}
        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
          <button type="submit" disabled={guardar.isPending} className="btn-primary inline-flex items-center gap-2">
            {guardar.isPending && <Spinner className="w-4 h-4 text-white" />}
            {esNuevo ? 'Guardar' : 'Guardar cambios'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

/**
 * Equipos que cubre una garantía: filtra por ubicación (con lo que tiene
 * dentro) o por código, y marca. Los marcados se conservan al cambiar de filtro.
 */
function SelectorEquipos({ hospital, equipos, setEquipos, error }) {
  const [node, setNode] = useState('')
  const [buscar, setBuscar] = useState('')
  const { data: tree = [] } = useAssetTree(hospital)
  const nodos = useMemo(() => flattenTree(tree), [tree])
  const params = {
    hospital_id: hospital,
    ...(node && { node_id: node, include_sublocations: true }),
    ...(buscar.trim() && { search: buscar.trim() }),
  }
  const { data: activos = [], isFetching } = useAssets(params, { enabled: !!hospital })
  const todos = activos.length > 0 && activos.every((a) => equipos.has(a.id))

  function toggle(a) {
    const m = new Map(equipos)
    if (m.has(a.id)) m.delete(a.id)
    else m.set(a.id, { id: a.id, code: a.code, name: a.name })
    setEquipos(m)
  }

  function toggleTodos() {
    const m = new Map(equipos)
    for (const a of activos) {
      if (todos) m.delete(a.id)
      else m.set(a.id, { id: a.id, code: a.code, name: a.name })
    }
    setEquipos(m)
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-gray-600">
        Equipos que cubre {equipos.size > 0 && <span className="text-brand">({equipos.size} marcado{equipos.size > 1 ? 's' : ''})</span>}
      </p>
      {equipos.size > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {[...equipos.values()].map((a) => (
            <span key={a.id} className="inline-flex items-center gap-1 text-xs bg-brand/10 text-brand rounded-full pl-2 pr-1 py-0.5">
              <span className="font-mono">{a.code}</span>
              <button type="button" onClick={() => toggle(a)} aria-label={`Quitar ${a.code}`}
                className="rounded-full hover:bg-brand/20 w-4 h-4 leading-none">&times;</button>
            </span>
          ))}
        </div>
      )}
      <div className="grid gap-2 sm:grid-cols-2">
        <select value={node} onChange={(e) => setNode(e.target.value)} disabled={!hospital} className="input-field" aria-label="Ubicación">
          <option value="">Todo el hospital</option>
          {nodos.map((n) => <option key={n.id} value={n.id}>{indentedLabel(n.name, n.depth)}</option>)}
        </select>
        <input value={buscar} onChange={(e) => setBuscar(e.target.value)} disabled={!hospital}
          placeholder="Código o nombre" aria-label="Buscar equipo" className="input-field" />
      </div>
      <div className={`border rounded-lg max-h-60 overflow-y-auto ${error ? 'border-red-300' : 'border-gray-100'}`}>
        {!hospital ? (
          <p className="text-sm text-gray-500 text-center py-6">Elige el hospital para ver sus equipos.</p>
        ) : isFetching && activos.length === 0 ? (
          <div className="flex justify-center py-6"><Spinner /></div>
        ) : activos.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-6">Ningún equipo con este filtro.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0">
              <tr className="text-left text-xs font-medium text-gray-500">
                <th className="px-3 py-2 w-8">
                  <input type="checkbox" checked={todos} onChange={toggleTodos} aria-label="Marcar todos" />
                </th>
                <th className="px-3 py-2">Equipo</th>
                <th className="px-3 py-2">Ubicación</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {activos.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => toggle(a)}>
                  <td className="px-3 py-1.5">
                    <input type="checkbox" checked={equipos.has(a.id)} onChange={() => toggle(a)}
                      onClick={(e) => e.stopPropagation()} aria-label={`Marcar ${a.code}`} />
                  </td>
                  <td className="px-3 py-1.5">
                    <span className="font-mono text-xs text-gray-500">{a.code}</span>{' '}
                    <span className="text-gray-800">{a.name}</span>
                  </td>
                  <td className="px-3 py-1.5 text-xs text-gray-500">{a.node?.path ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
}

function DeleteModal({ doc, onClose }) {
  const borrar = useDeleteContract()
  return (
    <Modal title="Eliminar documento" onClose={onClose}>
      <p className="text-sm text-gray-700">
        ¿Eliminar <strong>{doc.name}</strong>? Deja de contar para la vigencia del hospital y de sus equipos.
        Si solo terminó, no hace falta borrarlo: queda como vencido en el historial.
      </p>
      {borrar.isError && <p className="text-sm text-red-600 mt-3">{apiErrorMessage(borrar.error)}</p>}
      <div className="flex justify-end gap-3 pt-5">
        <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
        <button type="button" disabled={borrar.isPending}
          onClick={() => borrar.mutate(doc.id, { onSuccess: onClose })}
          className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 disabled:opacity-50">
          Eliminar
        </button>
      </div>
    </Modal>
  )
}

function Campo({ label, error, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
      {error && <p className="text-xs text-red-500 mt-0.5">{error}</p>}
    </div>
  )
}

