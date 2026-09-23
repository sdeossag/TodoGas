import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'

import { mediaUrl } from '../../api/client'
import { useWorkOrderPhotos } from '../../api/evidence'
import {
  FINDING_STATUS_COLORS,
  SEVERITIES,
  SEVERITY_COLORS,
  useConvertFinding,
  useCreateFinding,
  useDeleteFinding,
  useDismissFinding,
  useFindings,
  useUpdateFinding,
} from '../../api/findings'
import useAuthStore from '../../store/authStore'
import { formatDate, todayIso } from '../../utils/maintenance'
import PhotoCapture from '../evidence/PhotoCapture'
import Icon from '../ui/Icon'
import Modal from '../ui/Modal'

const EDITABLE = ['PENDING', 'IN_PROGRESS']
const DECIDIBLE = ['IN_REVIEW', 'COMPLETED']

/**
 * Hallazgos de una OT (bloque E, decisiones del 2026-09-23).
 *
 * El técnico reporta lo que encontró en un equipo mientras la OT está
 * abierta; si lo arregló ahí mismo lo marca resuelto en sitio con lo que
 * hizo. Enviada a revisión, lo capturado es evidencia. El planificador decide
 * sobre los pendientes: convertirlos en correctivo o descartarlos.
 *
 * `readOnly`: el portal del hospital, que solo mira.
 */
export default function FindingsPanel({ wo, readOnly = false }) {
  const user = useAuthStore((s) => s.user)
  const { data: hallazgos = [], isLoading } = useFindings({ work_order: wo.id })
  const { data: fotos = [] } = useWorkOrderPhotos(wo.id)
  const [editando, setEditando] = useState(null) // null | 'nuevo' | hallazgo

  const esInterno = ['ADMIN', 'SUP'].includes(user?.role)
  const esSuTecnico = user?.role === 'TEC' && wo.assigned_to?.id === user?.id
  const puedeReportar = !readOnly && EDITABLE.includes(wo.status) && (esSuTecnico || esInterno)
  const puedeDecidir = !readOnly && esInterno && DECIDIBLE.includes(wo.status)
  const activos = (wo.tasks ?? []).filter((t) => t.status !== 'CANCELLED').map((t) => t.asset)

  if (isLoading) return <p className="text-sm text-gray-500">Cargando hallazgos…</p>

  return (
    <div className="space-y-4">
      {!readOnly && (
        <p className="text-xs text-gray-500">
          Lo que encontraste en un equipo y hay que corregir, o que corregiste ahí mismo. Sale en el acta.
        </p>
      )}

      {hallazgos.length === 0 && (
        <p className="text-sm text-gray-500">No se reportaron hallazgos en esta visita.</p>
      )}

      {hallazgos.map((f) => (
        <FindingCard
          key={f.id}
          hallazgo={f}
          fotos={fotos.filter((p) => p.finding === f.id)}
          editable={puedeReportar}
          puedeDecidir={puedeDecidir}
          paraHospital={readOnly}
          wo={wo}
          onEdit={() => setEditando(f)}
        />
      ))}

      {puedeReportar && (
        <button type="button" onClick={() => setEditando('nuevo')} className="btn-secondary">
          <Icon name="plus" className="w-4 h-4" /> Reportar hallazgo
        </button>
      )}

      {editando && (
        <FindingForm
          wo={wo}
          activos={activos}
          hallazgo={editando === 'nuevo' ? null : editando}
          onClose={() => setEditando(null)}
        />
      )}
    </div>
  )
}

export function SeverityBadge({ hallazgo }) {
  return (
    <span className="inline-flex items-center gap-1.5 flex-wrap">
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEVERITY_COLORS[hallazgo.severity]}`}>
        {hallazgo.severity_display}
      </span>
      {hallazgo.out_of_service && (
        <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-red-600 text-white">Fuera de servicio</span>
      )}
    </span>
  )
}

function FindingCard({ hallazgo: f, fotos, editable, puedeDecidir, paraHospital, wo, onEdit }) {
  const borrar = useDeleteFinding()
  const qc = useQueryClient()
  const [conFoto, setConFoto] = useState(false)
  const [decidiendo, setDecidiendo] = useState(null) // 'convert' | 'dismiss'

  return (
    <div className="border border-gray-200 rounded-xl p-4 space-y-3">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0 space-y-1">
          <SeverityBadge hallazgo={f} />
          <p className="text-sm font-medium text-gray-800">
            {f.asset_info.name} <span className="font-mono text-xs text-gray-500">{f.asset_info.code}</span>
          </p>
        </div>
        {paraHospital ? (
          <EstadoParaHospital hallazgo={f} />
        ) : (
          <span className="inline-flex items-center gap-1.5">
            {f._pending && (
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-amber-100 text-amber-800">
                En cola
              </span>
            )}
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${FINDING_STATUS_COLORS[f.status]}`}>
              {f.status_display}
            </span>
          </span>
        )}
      </div>

      <p className="text-sm text-gray-700 whitespace-pre-line">{f.description}</p>

      {f.resolved_on_site && (
        <p className="text-sm text-green-800 bg-green-50 rounded-lg px-3 py-2">
          <strong>Qué se hizo:</strong> {f.resolution_notes}
        </p>
      )}
      {!paraHospital && <DecisionInfo hallazgo={f} />}

      {fotos.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {fotos.map((p) => (
            <a key={p.id} href={mediaUrl(p.file_url)} target="_blank" rel="noopener noreferrer">
              <img src={mediaUrl(p.file_url)} alt="Foto del hallazgo" className="w-20 h-20 object-cover rounded-lg border border-gray-200" />
            </a>
          ))}
        </div>
      )}

      <p className="text-xs text-gray-500">
        {f.reported_by_name} · {new Date(f.reported_at).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })}
        {fotos.length === 0 && f.photos_count > 0 && ` · ${f.photos_count} foto${f.photos_count > 1 ? 's' : ''}`}
      </p>

      {(editable || (puedeDecidir && f.status === 'PENDING')) && (
        <div className="flex items-center gap-3 flex-wrap pt-1 border-t border-gray-100">
          {editable && (
            <>
              <button type="button" onClick={() => setConFoto((v) => !v)} className="text-sm text-brand hover:underline">
                <Icon name="camera" className="w-4 h-4 inline -mt-0.5" /> Agregar foto
              </button>
              <button type="button" onClick={onEdit} className="text-sm text-gray-600 hover:underline">Editar</button>
              <button
                type="button"
                disabled={borrar.isPending}
                onClick={() => window.confirm('¿Quitar este hallazgo? Sus fotos quedan en la evidencia de la OT.') && borrar.mutate(f.id)}
                className="text-sm text-red-600 hover:underline disabled:opacity-50"
              >
                Quitar
              </button>
            </>
          )}
          {puedeDecidir && f.status === 'PENDING' && (
            <>
              <button type="button" onClick={() => setDecidiendo('convert')} className="btn-primary text-sm">
                Convertir en correctivo
              </button>
              <button type="button" onClick={() => setDecidiendo('dismiss')} className="btn-secondary text-sm">
                Descartar
              </button>
            </>
          )}
        </div>
      )}

      {conFoto && (
        <PhotoCapture
          workOrderId={wo.id}
          findingId={f.id}
          onUploaded={() => {
            setConFoto(false)
            // Sin red la foto queda en cola: el contador del hallazgo sale de ahí.
            qc.invalidateQueries({ queryKey: ['findings'] })
          }}
        />
      )}
      {decidiendo && (
        <DecisionModal hallazgo={f} accion={decidiendo} onClose={() => setDecidiendo(null)} />
      )}
    </div>
  )
}

/**
 * El estado como lo entiende el hospital: resuelto (en sitio o con el
 * correctivo ya hecho), en corrección, o descartado.
 */
export function EstadoParaHospital({ hallazgo: f }) {
  const corregido = f.status === 'CONVERTED' && f.corrective_task_info?.status === 'DONE'
  const [texto, color] = f.resolved_on_site || corregido
    ? ['Resuelto', 'bg-green-50 text-green-700']
    : f.status === 'DISMISSED'
      ? ['Descartado', 'bg-gray-100 text-gray-600']
      : f.status === 'CONVERTED'
        ? [`Corrección programada ${formatDate(f.corrective_task_info?.scheduled_date)}`, 'bg-blue-50 text-blue-700']
        : ['Pendiente de corrección', 'bg-amber-50 text-amber-700']
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>{texto}</span>
}

/** Qué decidió el planificador sobre un pendiente, y en qué va el correctivo. */
export function DecisionInfo({ hallazgo: f }) {
  if (f.status === 'CONVERTED' && f.corrective_task_info) {
    const t = f.corrective_task_info
    return (
      <p className="text-sm text-blue-800 bg-blue-50 rounded-lg px-3 py-2">
        Correctivo {t.status === 'DONE' ? 'realizado' : `programado para el ${formatDate(t.scheduled_date)}`}
        {t.work_order && (
          <> en la <Link to={`/ordenes/${t.work_order.id}`} className="underline">{t.work_order.wo_code}</Link></>
        )}
        {f.decided_by_name && <span className="text-blue-600"> · decidió {f.decided_by_name}</span>}
      </p>
    )
  }
  if (f.status === 'DISMISSED') {
    return (
      <p className="text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2">
        Descartado{f.decided_by_name ? ` por ${f.decided_by_name}` : ''}: {f.decision_note}
      </p>
    )
  }
  return null
}

export function DecisionModal({ hallazgo, accion, onClose }) {
  const convertir = useConvertFinding()
  const descartar = useDismissFinding()
  const [fecha, setFecha] = useState(todayIso())
  const [nota, setNota] = useState('')
  const mut = accion === 'convert' ? convertir : descartar
  const error = mut.error?.response?.data?.detail

  function enviar(e) {
    e.preventDefault()
    if (accion === 'convert') {
      convertir.mutate({ id: hallazgo.id, scheduled_date: fecha, note: nota }, { onSuccess: onClose })
    } else {
      descartar.mutate({ id: hallazgo.id, note: nota }, { onSuccess: onClose })
    }
  }

  return (
    <Modal
      title={accion === 'convert' ? 'Convertir en correctivo' : 'Descartar hallazgo'}
      subtitle={`${hallazgo.asset_info.name} · ${hallazgo.description.slice(0, 80)}`}
      onClose={onClose}
    >
      <form onSubmit={enviar} className="space-y-4">
        {accion === 'convert' ? (
          <>
            <p className="text-sm text-gray-600">
              Se crea una tarea correctiva pendiente sobre el equipo, con prioridad según la severidad.
              Aparece en Tareas pendientes para agruparla en una OT.
            </p>
            <label className="block">
              <span className="block text-xs font-medium text-gray-500 mb-1">Fecha programada</span>
              <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className="input-field w-48" required />
            </label>
            <label className="block">
              <span className="block text-xs font-medium text-gray-500 mb-1">Nota (opcional)</span>
              <textarea value={nota} onChange={(e) => setNota(e.target.value)} rows={2} className="input-field w-full" />
            </label>
          </>
        ) : (
          <label className="block">
            <span className="block text-xs font-medium text-gray-500 mb-1">Por qué se descarta *</span>
            <textarea value={nota} onChange={(e) => setNota(e.target.value)} rows={3} className="input-field w-full"
              placeholder="Ej.: ya lo corrigió el hospital, duplicado de otro hallazgo…" required />
          </label>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
          <button type="submit" disabled={mut.isPending} className={accion === 'convert' ? 'btn-primary' : 'btn-secondary text-red-700'}>
            {mut.isPending ? 'Guardando…' : accion === 'convert' ? 'Crear correctivo' : 'Descartar'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function FindingForm({ wo, activos, hallazgo, onClose }) {
  const crear = useCreateFinding()
  const editar = useUpdateFinding()
  const [form, setForm] = useState(() => ({
    asset: hallazgo?.asset ?? (activos.length === 1 ? activos[0].id : ''),
    description: hallazgo?.description ?? '',
    severity: hallazgo?.severity ?? 'MEDIUM',
    out_of_service: hallazgo?.out_of_service ?? false,
    resolved_on_site: hallazgo?.resolved_on_site ?? false,
    resolution_notes: hallazgo?.resolution_notes ?? '',
  }))
  const mut = hallazgo ? editar : crear
  const errores = mut.error?.response?.data ?? {}
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  function enviar(e) {
    e.preventDefault()
    const datos = { ...form, resolution_notes: form.resolved_on_site ? form.resolution_notes : '' }
    if (hallazgo) {
      editar.mutate({ id: hallazgo.id, ...datos }, { onSuccess: onClose })
    } else {
      const a = activos.find((x) => x.id === form.asset)
      crear.mutate(
        {
          ...datos,
          work_order: wo.id,
          reported_at: new Date().toISOString(),
          // Sin red es lo que se muestra del equipo hasta sincronizar.
          asset_info: a && { id: a.id, code: a.code, name: a.name, node_path: a.location ?? '' },
        },
        { onSuccess: onClose }
      )
    }
  }

  const campoError = (k) => errores[k] && (
    <p className="mt-1 text-xs text-red-600">{[].concat(errores[k]).join(' ')}</p>
  )

  return (
    <Modal title={hallazgo ? 'Editar hallazgo' : 'Reportar hallazgo'} onClose={onClose}>
      <form onSubmit={enviar} className="space-y-4">
        {activos.length > 1 && (
          <label className="block">
            <span className="block text-xs font-medium text-gray-500 mb-1">Equipo *</span>
            <select value={form.asset} onChange={(e) => set('asset', e.target.value)} className="input-field w-full" required>
              <option value="">Elige el equipo</option>
              {activos.map((a) => (
                <option key={a.id} value={a.id}>{a.name} · {a.code}</option>
              ))}
            </select>
            {campoError('asset')}
          </label>
        )}

        <label className="block">
          <span className="block text-xs font-medium text-gray-500 mb-1">Qué encontraste *</span>
          <textarea value={form.description} onChange={(e) => set('description', e.target.value)} rows={3}
            className="input-field w-full" placeholder="Ej.: fuga en la válvula de oxígeno del cubículo 4" required />
          {campoError('description')}
        </label>

        <fieldset>
          <legend className="block text-xs font-medium text-gray-500 mb-1">Severidad</legend>
          <div className="grid grid-cols-4 gap-2">
            {SEVERITIES.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => set('severity', s.value)}
                aria-pressed={form.severity === s.value}
                className={`py-2 rounded-lg text-sm border ${form.severity === s.value
                  ? `${SEVERITY_COLORS[s.value]} border-current font-semibold`
                  : 'border-gray-200 text-gray-600'}`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </fieldset>

        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={form.out_of_service} onChange={(e) => set('out_of_service', e.target.checked)}
            className="rounded border-gray-300 text-brand focus:ring-brand/30" />
          El equipo queda fuera de servicio
        </label>

        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={form.resolved_on_site} onChange={(e) => set('resolved_on_site', e.target.checked)}
            className="rounded border-gray-300 text-brand focus:ring-brand/30" />
          Lo resolví aquí mismo
        </label>
        {form.resolved_on_site && (
          <label className="block">
            <span className="block text-xs font-medium text-gray-500 mb-1">Qué hiciste *</span>
            <textarea value={form.resolution_notes} onChange={(e) => set('resolution_notes', e.target.value)} rows={2}
              className="input-field w-full" placeholder="Ej.: se cambió el empaque y se probó sin fuga" required />
            {campoError('resolution_notes')}
          </label>
        )}

        {mut.error && !Object.keys(errores).some((k) => ['asset', 'description', 'resolution_notes'].includes(k)) && (
          <p className="text-sm text-red-600">{errores.detail ?? 'No se pudo guardar el hallazgo.'}</p>
        )}

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
          <button type="submit" disabled={mut.isPending} className="btn-primary">
            {mut.isPending ? 'Guardando…' : hallazgo ? 'Guardar' : 'Reportar'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
