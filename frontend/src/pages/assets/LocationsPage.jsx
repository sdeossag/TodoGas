import { Fragment, useCallback, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  useAssetNodes,
  useCreateAssetNode,
  useDeleteAssetNode,
  useHospital,
  useUpdateAssetNode,
} from '../../api/assets'
import Icon from '../../components/ui/Icon'
import Spinner from '../../components/ui/Spinner'
import useModalDismiss from '../../hooks/useModalDismiss'
import {
  NODE_TYPES,
  buildTree,
  flattenTree,
  indentedLabel,
  nodeTypeIcon,
  nodeTypeLabel,
  subtreeIds,
  suggestedChildType,
} from '../../utils/locationTree'

/**
 * Árbol de ubicaciones de un hospital: torres, pisos, servicios y salas.
 *
 * Es donde se arma la jerarquía que luego usan el formulario de activos y el
 * filtro de la pantalla de activos. Hasta ahora solo se podía crear por API.
 */
export default function LocationsPage() {
  const { id: hospitalId } = useParams()
  const { data: hospital, isLoading: hospitalLoading, isError: hospitalError } = useHospital(hospitalId)
  const { data: flatNodes = [], isLoading: nodesLoading, isError: nodesError } = useAssetNodes(hospitalId)

  const [collapsed, setCollapsed] = useState(() => new Set())
  const [search, setSearch] = useState('')
  const [modal, setModal] = useState(null) // { mode: 'create', parent } | { mode: 'edit', node }
  const [confirm, setConfirm] = useState(null) // { kind: 'delete' | 'deactivate', node }
  const [rowError, setRowError] = useState(null) // { id, message }

  const { roots, byId } = useMemo(() => buildTree(flatNodes), [flatNodes])

  // Una ubicación activa bajo otra inactiva tampoco sale en /tree/, así que no
  // aparece en los formularios. Se marca para que no parezca un error.
  const hiddenBy = useMemo(() => {
    const result = new Map()
    function walk(nodes, inactiveAncestor) {
      for (const n of nodes) {
        if (inactiveAncestor) result.set(n.id, inactiveAncestor)
        walk(n.children, inactiveAncestor ?? (n.is_active ? null : n))
      }
    }
    walk(roots, null)
    return result
  }, [roots])

  const query = normalize(search.trim())
  const matches = useMemo(() => {
    if (!query) return null
    const hits = new Set()
    const visible = new Set()
    for (const node of byId.values()) {
      if (normalize(node.name).includes(query) || normalize(node.code).includes(query)) {
        hits.add(node.id)
        // Los antecesores se muestran para no perder el contexto del hallazgo.
        let current = node
        while (current) {
          visible.add(current.id)
          current = current.parent ? byId.get(current.parent.id) : null
        }
      }
    }
    return { hits, visible }
  }, [query, byId])

  const stats = useMemo(() => {
    let active = 0
    let assets = 0
    for (const n of byId.values()) {
      if (n.is_active) active += 1
      assets += n.asset_count ?? 0
    }
    return { total: byId.size, active, assets }
  }, [byId])

  const toggle = useCallback((id) => {
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  function expandAll() { setCollapsed(new Set()) }
  function collapseAll() {
    setCollapsed(new Set([...byId.values()].filter((n) => n.children.length).map((n) => n.id)))
  }

  function handleCreated(parentId) {
    // Que la ubicación recién creada quede a la vista.
    if (parentId) {
      setCollapsed((prev) => {
        if (!prev.has(parentId)) return prev
        const next = new Set(prev)
        next.delete(parentId)
        return next
      })
    }
  }

  if (hospitalLoading || nodesLoading) {
    return <div className="flex justify-center py-20"><Spinner className="w-10 h-10 text-brand" label="Cargando ubicaciones" /></div>
  }

  if (hospitalError || !hospital) {
    return (
      <div className="text-center py-20 space-y-3">
        <p className="text-gray-600">No se encontró el hospital.</p>
        <Link to="/hospitales" className="text-sm text-brand hover:underline">Volver a hospitales</Link>
      </div>
    )
  }

  function renderNodes(nodes) {
    return nodes
      .filter((n) => !matches || matches.visible.has(n.id))
      .map((n) => {
        const open = matches ? true : !collapsed.has(n.id)
        return (
          <Fragment key={n.id}>
            <LocationRow
              node={n}
              open={open}
              highlighted={matches?.hits.has(n.id)}
              hiddenBy={hiddenBy.get(n.id)}
              hospitalId={hospitalId}
              error={rowError?.id === n.id ? rowError.message : null}
              onToggle={() => toggle(n.id)}
              onAddChild={() => setModal({ mode: 'create', parent: n })}
              onEdit={() => setModal({ mode: 'edit', node: n })}
              onDeactivate={() => setConfirm({ kind: 'deactivate', node: n })}
              onDelete={() => setConfirm({ kind: 'delete', node: n })}
              onError={(message) => setRowError(message ? { id: n.id, message } : null)}
            />
            {open && n.children.length > 0 && renderNodes(n.children)}
          </Fragment>
        )
      })
  }

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div>
        <Link to="/hospitales" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-brand">
          <Icon name="arrowLeft" className="w-4 h-4" /> Hospitales
        </Link>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">
              Ubicaciones
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {hospital.name} <span className="font-mono text-gray-400">· {hospital.code}</span>
              {!hospital.is_active && (
                <span className="ml-2 inline-flex px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-500">
                  Hospital inactivo
                </span>
              )}
            </p>
          </div>
          <button onClick={() => setModal({ mode: 'create', parent: null })}
            className="btn-primary inline-flex items-center gap-1.5">
            <Icon name="plus" className="w-4 h-4" /> Nueva ubicación
          </button>
        </div>
      </div>

      {nodesError ? (
        <div className="bg-white rounded-xl border border-gray-200 shadow-card text-center py-16 text-red-600 text-sm">
          No se pudieron cargar las ubicaciones. Revisa tu conexión e intenta de nuevo.
        </div>
      ) : stats.total === 0 ? (
        <EmptyState onCreate={() => setModal({ mode: 'create', parent: null })} />
      ) : (
        <>
          {/* Barra de herramientas */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <Icon name="search" className="w-4 h-4 text-gray-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por nombre o código..."
                aria-label="Buscar ubicación"
                className="border border-gray-200 rounded-lg pl-8 pr-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 w-64"
              />
            </div>
            {!matches && (
              <div className="flex gap-1 text-sm">
                <button onClick={expandAll} className="px-2.5 py-1.5 rounded-lg text-gray-600 hover:bg-gray-100">
                  Expandir todo
                </button>
                <button onClick={collapseAll} className="px-2.5 py-1.5 rounded-lg text-gray-600 hover:bg-gray-100">
                  Contraer todo
                </button>
              </div>
            )}
            <p className="text-sm text-gray-500 ml-auto">
              {stats.total} {stats.total === 1 ? 'ubicación' : 'ubicaciones'}
              {stats.active !== stats.total &&
                ` · ${stats.total - stats.active} ${stats.total - stats.active === 1 ? 'inactiva' : 'inactivas'}`}
              {' · '}{stats.assets} {stats.assets === 1 ? 'activo asignado' : 'activos asignados'}
            </p>
          </div>

          {/* Árbol */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
            {matches && matches.hits.size === 0 ? (
              <p className="text-center py-12 text-sm text-gray-500">
                Ninguna ubicación coincide con «{search.trim()}».
              </p>
            ) : (
              <ul className="divide-y divide-gray-50">{renderNodes(roots)}</ul>
            )}
          </div>
        </>
      )}

      {modal && (
        <LocationModal
          hospitalId={hospitalId}
          hospitalName={hospital.name}
          roots={roots}
          byId={byId}
          initial={modal}
          onCreated={handleCreated}
          onClose={() => setModal(null)}
        />
      )}

      {confirm && (
        <ConfirmDialog
          confirm={confirm}
          onClose={() => setConfirm(null)}
        />
      )}
    </div>
  )
}

// ── Fila del árbol ────────────────────────────────────────────────────────────

function LocationRow({
  node, open, highlighted, hiddenBy, hospitalId, error,
  onToggle, onAddChild, onEdit, onDeactivate, onDelete, onError,
}) {
  const updateMut = useUpdateAssetNode()
  const hasChildren = node.children.length > 0
  const blockedDelete = node.children_count > 0 || node.asset_count > 0

  async function activate() {
    onError(null)
    try {
      await updateMut.mutateAsync({ id: node.id, is_active: true })
    } catch (err) {
      onError(apiMessage(err, 'No se pudo activar la ubicación.'))
    }
  }

  const deleteHint = node.children_count > 0
    ? 'No se puede eliminar: tiene sububicaciones'
    : node.asset_count > 0
      ? 'No se puede eliminar: tiene activos asignados'
      : 'Eliminar ubicación'

  return (
    <li>
      <div
        className={`group flex flex-wrap md:flex-nowrap items-center gap-x-3 gap-y-1 py-2 pr-3 transition-colors
          ${highlighted ? 'bg-yellow-50' : 'hover:bg-gray-50'}`}
        style={{ paddingLeft: `${12 + node.depth * 24}px` }}
      >
        {/* Nombre */}
        <div className={`flex items-center gap-2 min-w-0 flex-1 ${node.is_active ? '' : 'opacity-60'}`}>
          {hasChildren ? (
            <button
              onClick={onToggle}
              aria-expanded={open}
              aria-label={open ? `Contraer ${node.name}` : `Expandir ${node.name}`}
              className="w-5 h-5 flex items-center justify-center rounded text-gray-400 hover:text-gray-700 hover:bg-gray-200 flex-shrink-0">
              <Icon name={open ? 'chevronDown' : 'chevronRight'} className="w-3.5 h-3.5" />
            </button>
          ) : (
            <span className="w-5 flex-shrink-0" />
          )}
          <Icon name={nodeTypeIcon(node.node_type)} className="w-4 h-4 text-gray-500 flex-shrink-0"
            title={nodeTypeLabel(node.node_type)} />
          <span className="font-medium text-gray-800 truncate">{node.name}</span>
          {node.code && <span className="font-mono text-xs text-gray-400 flex-shrink-0">{node.code}</span>}
          {!node.is_active && (
            <span className="px-1.5 py-0.5 rounded text-[11px] bg-gray-100 text-gray-500 flex-shrink-0">Inactiva</span>
          )}
          {node.is_active && hiddenBy && (
            <span className="px-1.5 py-0.5 rounded text-[11px] bg-amber-50 text-amber-700 flex-shrink-0"
              title={`No aparece en los formularios porque «${hiddenBy.name}» está inactiva.`}>
              Oculta
            </span>
          )}
        </div>

        {/* Conteos */}
        <div className="flex items-center gap-3 text-xs text-gray-500 flex-shrink-0 pl-7 md:pl-0">
          <span className="hidden sm:inline text-gray-400">{nodeTypeLabel(node.node_type)}</span>
          {node.asset_count > 0 ? (
            <Link to={`/activos?hospital_id=${hospitalId}&node_id=${node.id}`}
              className="text-brand hover:underline whitespace-nowrap">
              {node.asset_count} {node.asset_count === 1 ? 'activo' : 'activos'}
            </Link>
          ) : (
            <span className="text-gray-400 whitespace-nowrap">Sin activos</span>
          )}
        </div>

        {/* Acciones: siempre visibles en pantallas táctiles, al pasar el ratón en escritorio */}
        <div className="flex items-center gap-0.5 flex-shrink-0 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 transition-opacity">
          <RowButton icon="plus" label={`Añadir sububicación en ${node.name}`} onClick={onAddChild} />
          <RowButton icon="edit" label={`Editar ${node.name}`} onClick={onEdit} />
          {node.is_active ? (
            <RowButton icon="eyeOff" label={`Desactivar ${node.name}`} onClick={onDeactivate} />
          ) : (
            <RowButton icon="eye" label={`Activar ${node.name}`} onClick={activate}
              disabled={updateMut.isPending} />
          )}
          <RowButton icon="trash" label={deleteHint} onClick={onDelete} disabled={blockedDelete} danger />
        </div>
      </div>
      {error && (
        <p className="text-xs text-red-600 pb-2" style={{ paddingLeft: `${40 + node.depth * 24}px` }}>{error}</p>
      )}
    </li>
  )
}

function RowButton({ icon, label, onClick, disabled, danger }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className={`w-8 h-8 flex items-center justify-center rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed
        ${danger ? 'text-gray-500 hover:text-red-600 hover:bg-red-50 disabled:hover:bg-transparent disabled:hover:text-gray-500'
                 : 'text-gray-500 hover:text-brand hover:bg-brand/10'}`}>
      <Icon name={icon} className="w-4 h-4" />
    </button>
  )
}

function EmptyState({ onCreate }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-card text-center py-14 px-6">
      <Icon name="building" className="w-10 h-10 mx-auto mb-3 text-gray-400" />
      <p className="font-medium text-gray-700">Este hospital todavía no tiene ubicaciones</p>
      <p className="text-sm text-gray-500 mt-1 max-w-md mx-auto">
        Organízalo como lo recorre el técnico: torre, piso, servicio. Cada activo se asigna
        después a la ubicación más específica.
      </p>
      <button onClick={onCreate} className="btn-primary inline-flex items-center gap-1.5 mt-5">
        <Icon name="plus" className="w-4 h-4" /> Crear la primera ubicación
      </button>
    </div>
  )
}

// ── Crear / editar ────────────────────────────────────────────────────────────

function LocationModal({ hospitalId, hospitalName, roots, byId, initial, onCreated, onClose }) {
  useModalDismiss(onClose)
  const isEdit = initial.mode === 'edit'
  const editing = isEdit ? initial.node : null
  const nameRef = useRef(null)

  const [form, setForm] = useState(() => (isEdit ? {
    name: editing.name,
    node_type: editing.node_type,
    parent: editing.parent?.id ?? '',
    code: editing.code ?? '',
    sort_order: editing.sort_order ?? 0,
  } : {
    name: '',
    node_type: suggestedChildType(initial.parent?.node_type),
    parent: initial.parent?.id ?? '',
    code: '',
    sort_order: 0,
  }))
  const [errors, setErrors] = useState({})
  const [lastCreated, setLastCreated] = useState(null)

  const createMut = useCreateAssetNode()
  const updateMut = useUpdateAssetNode()
  const saving = createMut.isPending || updateMut.isPending

  // Al mover una ubicación no puede quedar dentro de sí misma ni de una de sus
  // sububicaciones (el backend también lo rechaza, pero mejor no ofrecerlo).
  const parentOptions = useMemo(() => {
    const excluded = editing ? subtreeIds(byId.get(editing.id)) : new Set()
    return flattenTree(roots).filter((n) => !excluded.has(n.id))
  }, [roots, byId, editing])

  const parentNode = form.parent ? byId.get(form.parent) : null
  const preview = [
    hospitalName,
    ...(parentNode ? parentNode.path.split('/') : []),
    form.name.trim() || '…',
  ].join(' / ')

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
    setErrors((e) => ({ ...e, [field]: undefined, non_field_errors: undefined }))
  }

  async function save(keepOpen) {
    if (!form.name.trim()) {
      setErrors({ name: 'El nombre es obligatorio' })
      return
    }
    const payload = {
      name: form.name.trim(),
      node_type: form.node_type,
      parent: form.parent || null,
      code: form.code.trim(),
      sort_order: Number(form.sort_order) || 0,
    }
    try {
      if (isEdit) {
        await updateMut.mutateAsync({ id: editing.id, ...payload })
        onClose()
        return
      }
      const created = await createMut.mutateAsync({ hospital: hospitalId, ...payload })
      onCreated(payload.parent)
      if (!keepOpen) {
        onClose()
        return
      }
      // Alta en serie: mismo padre y mismo tipo, campos de texto en blanco.
      setLastCreated(created.name)
      setForm((f) => ({ ...f, name: '', code: '' }))
      nameRef.current?.focus()
    } catch (err) {
      setErrors(fieldErrors(err))
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    save(false)
  }

  const title = isEdit
    ? 'Editar ubicación'
    : initial.parent ? `Nueva sububicación en ${initial.parent.name}` : 'Nueva ubicación'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 backdrop-blur-[2px]">
      <div role="dialog" aria-modal="true" aria-labelledby="location-modal-title"
        className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b flex items-center justify-between gap-4">
          <h2 id="location-modal-title" className="text-lg font-semibold text-gray-800 truncate">{title}</h2>
          <button onClick={onClose} aria-label="Cerrar"
            className="text-gray-500 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {lastCreated && (
            <p className="text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2 flex items-center gap-2">
              <Icon name="checkCircle" className="w-4 h-4 flex-shrink-0" />
              Se creó «{lastCreated}». Puedes añadir la siguiente.
            </p>
          )}

          <Field label="Nombre *" error={errors.name}>
            <input ref={nameRef} autoFocus value={form.name} onChange={(e) => set('name', e.target.value)}
              className={input(errors.name)} placeholder="Urgencias" />
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Tipo" error={errors.node_type}>
              <select value={form.node_type} onChange={(e) => set('node_type', e.target.value)}
                className={input(errors.node_type)}>
                {NODE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </Field>
            <Field label="Ubicada dentro de" error={errors.parent}>
              <select value={form.parent} onChange={(e) => set('parent', e.target.value)}
                className={input(errors.parent)}>
                <option value="">Nivel principal del hospital</option>
                {parentOptions.map((n) => (
                  <option key={n.id} value={n.id}>
                    {indentedLabel(n.name, n.depth)}{n.is_active ? '' : ' (inactiva)'}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Código" error={errors.code}>
              <input value={form.code} onChange={(e) => set('code', e.target.value)}
                className={input(errors.code)} placeholder="Opcional" />
            </Field>
            <Field label="Orden" error={errors.sort_order}
              hint="Opcional. Sin orden se listan por nombre.">
              <input type="number" value={form.sort_order} onChange={(e) => set('sort_order', e.target.value)}
                className={input(errors.sort_order)} />
            </Field>
          </div>

          <p className="text-xs text-gray-500">
            Ruta: <span className="text-gray-700">{preview}</span>
          </p>

          {errors.non_field_errors && <p className="text-sm text-red-600">{errors.non_field_errors}</p>}

          <div className="flex flex-wrap justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            {!isEdit && (
              <button type="button" onClick={() => save(true)} disabled={saving} className="btn-secondary">
                Guardar y crear otra
              </button>
            )}
            <button type="submit" disabled={saving} className="btn-primary inline-flex items-center gap-2">
              {saving && <Spinner className="w-4 h-4 text-white" label="Guardando" />}
              {isEdit ? 'Guardar cambios' : 'Crear ubicación'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Desactivar / eliminar ─────────────────────────────────────────────────────

function ConfirmDialog({ confirm, onClose }) {
  useModalDismiss(onClose)
  const { kind, node } = confirm
  const updateMut = useUpdateAssetNode()
  const deleteMut = useDeleteAssetNode()
  const [error, setError] = useState(null)
  const pending = updateMut.isPending || deleteMut.isPending

  const descendants = subtreeIds(node).size - 1
  let assetsInSubtree = 0
  ;(function sum(n) {
    assetsInSubtree += n.asset_count ?? 0
    n.children.forEach(sum)
  })(node)

  async function run() {
    setError(null)
    try {
      if (kind === 'delete') await deleteMut.mutateAsync(node.id)
      else await updateMut.mutateAsync({ id: node.id, is_active: false })
      onClose()
    } catch (err) {
      setError(apiMessage(err, 'No se pudo completar la acción.'))
    }
  }

  const isDelete = kind === 'delete'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 backdrop-blur-[2px]">
      <div role="alertdialog" aria-modal="true" aria-labelledby="confirm-title"
        className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6 space-y-4">
        <h3 id="confirm-title" className="text-lg font-semibold text-gray-800">
          {isDelete ? `Eliminar «${node.name}»` : `Desactivar «${node.name}»`}
        </h3>
        {isDelete ? (
          <p className="text-sm text-gray-600">
            La ubicación se borra definitivamente. No tiene sububicaciones ni activos asignados.
          </p>
        ) : (
          <div className="text-sm text-gray-600 space-y-2">
            <p>Dejará de aparecer al elegir la ubicación de un activo. Se puede volver a activar.</p>
            {descendants > 0 && (
              <p>
                Sus <strong>{descendants}</strong> {descendants === 1 ? 'sububicación' : 'sububicaciones'} también
                {descendants === 1 ? ' quedará oculta' : ' quedarán ocultas'}.
              </p>
            )}
            {assetsInSubtree > 0 && (
              <p>
                Los <strong>{assetsInSubtree}</strong> {assetsInSubtree === 1 ? 'activo' : 'activos'} que ya
                están aquí no cambian: conservan su ubicación y su historial.
              </p>
            )}
          </div>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-3 pt-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancelar</button>
          <button onClick={run} disabled={pending}
            className={`px-5 py-2 text-white text-sm rounded-lg disabled:opacity-50 flex items-center gap-2
              ${isDelete ? 'bg-red-600 hover:bg-red-700' : 'bg-orange-600 hover:bg-orange-700'}`}>
            {pending && <Spinner className="w-4 h-4 text-white" label="Procesando" />}
            {isDelete ? 'Eliminar' : 'Desactivar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function Field({ label, error, hint, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
      {error ? (
        <p className="text-xs text-red-500 mt-0.5">{error}</p>
      ) : hint ? (
        <p className="text-xs text-gray-400 mt-0.5">{hint}</p>
      ) : null}
    </div>
  )
}

function input(hasError) {
  return `input-field ${hasError ? 'border-red-400' : ''}`
}

// Sin tildes ni mayúsculas: "urgencias" encuentra "Urgencias" y "uci" a "UCI".
function normalize(text) {
  return (text ?? '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()
}

function apiMessage(err, fallback) {
  const data = err?.response?.data
  if (typeof data === 'string') return data
  if (data?.detail) return data.detail
  const first = data && typeof data === 'object' ? Object.values(data)[0] : null
  if (first) return Array.isArray(first) ? first.join(' ') : String(first)
  return fallback
}

function fieldErrors(err) {
  const data = err?.response?.data
  if (!data || typeof data !== 'object') {
    return { non_field_errors: 'No se pudo guardar. Revisa tu conexión e intenta de nuevo.' }
  }
  const out = {}
  for (const [key, value] of Object.entries(data)) {
    out[key] = Array.isArray(value) ? value.join(' ') : String(value)
  }
  // Errores sin campo visible en el formulario (hospital, detail) van abajo.
  const shown = new Set(['name', 'node_type', 'parent', 'code', 'sort_order', 'non_field_errors'])
  const rest = Object.entries(out).filter(([k]) => !shown.has(k)).map(([, v]) => v)
  if (rest.length && !out.non_field_errors) out.non_field_errors = rest.join(' ')
  return out
}
