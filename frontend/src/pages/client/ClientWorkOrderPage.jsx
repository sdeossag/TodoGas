import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { useChecklistResponse } from '../../api/checklists'
import { useReportDownload, useWorkOrderReports } from '../../api/reports'
import { useWorkOrder } from '../../api/workOrders'
import CompletedChecklistView from '../../components/checklists/CompletedChecklist'
import PhotoGallery from '../../components/evidence/PhotoGallery'
import FindingsPanel from '../../components/findings/FindingsPanel'
import SignatureList from '../../components/evidence/SignatureList'
import Icon from '../../components/ui/Icon'
import Spinner from '../../components/ui/Spinner'
import { taskTypeLabel } from '../../constants/labels'
import { formatDate } from '../../utils/maintenance'
import { formatWoCode } from '../../utils/workOrder'

/**
 * Una OT finalizada vista por el hospital, de solo lectura: cada equipo con
 * su checklist, la evidencia y el acta. El servidor solo le da las OTs
 * finalizadas de su alcance; cualquier otra responde 404.
 */
export default function ClientWorkOrderPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: ot, isLoading, isError } = useWorkOrder(id)
  const { data: actas = [] } = useWorkOrderReports(id)
  const descargar = useReportDownload()
  const [abierta, setAbierta] = useState(null)

  if (isLoading) return <div className="flex justify-center py-20"><Spinner /></div>
  if (isError || !ot) {
    return <p className="text-center py-20 text-sm text-gray-500">No se encontró la orden de trabajo.</p>
  }

  const tareas = (ot.tasks ?? []).filter((t) => t.status !== 'CANCELLED')
  const acta = actas[0]

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <button type="button" onClick={() => navigate(-1)} className="text-xs text-brand hover:underline">← Volver</button>
        <div className="flex items-start justify-between gap-4 flex-wrap mt-1">
          <div>
            <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">{formatWoCode(ot)}</h1>
            <p className="text-sm text-gray-500">
              {taskTypeLabel(ot.task_type)} · Finalizada {ot.completed_at ? formatDate(ot.completed_at) : ''}
            </p>
          </div>
          {acta && (
            <button type="button" onClick={() => descargar.mutate(acta.id)} className="btn-primary">
              <Icon name="download" className="w-4 h-4" /> Descargar acta
            </button>
          )}
        </div>
        {ot.title && <p className="text-sm text-gray-700 mt-2">{ot.title}</p>}
      </div>

      <section className="bg-white rounded-xl border border-gray-200 shadow-card">
        <h2 className="px-5 py-4 border-b border-gray-100 font-semibold text-gray-700 text-sm">
          Equipos intervenidos ({tareas.length})
        </h2>
        <ul className="divide-y divide-gray-100">
          {tareas.map((t) => (
            <li key={t.id}>
              <button
                type="button"
                onClick={() => setAbierta(abierta === t.id ? null : t.id)}
                aria-expanded={abierta === t.id}
                className="w-full px-5 py-3 flex items-center justify-between gap-4 text-left hover:bg-gray-50"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    <Link to={`/mis-activos/${t.asset.id}`} onClick={(e) => e.stopPropagation()} className="hover:underline">
                      {t.asset.name}
                    </Link>
                    <span className="font-mono text-xs text-gray-500 ml-2">{t.asset.code}</span>
                  </p>
                  <p className="text-xs text-gray-500 truncate">{t.title}{t.asset.location ? ` · ${t.asset.location}` : ''}</p>
                </div>
                <span className="text-xs text-gray-500 whitespace-nowrap">
                  {t.checklist_response_id ? (abierta === t.id ? 'Ocultar checklist' : 'Ver checklist') : 'Sin checklist'}
                </span>
              </button>
              {abierta === t.id && t.checklist_response_id && (
                <div className="px-5 pb-5">
                  <ChecklistDeLaTarea responseId={t.checklist_response_id} />
                </div>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
        <h2 className="font-semibold text-gray-700 text-sm mb-4">Hallazgos</h2>
        <FindingsPanel wo={ot} readOnly />
      </section>

      <section className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
        <h2 className="font-semibold text-gray-700 text-sm mb-4">Fotos</h2>
        <PhotoGallery workOrderId={id} />
      </section>

      <section className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
        <h2 className="font-semibold text-gray-700 text-sm mb-4">Firmas</h2>
        <SignatureList workOrderId={id} />
      </section>
    </div>
  )
}

function ChecklistDeLaTarea({ responseId }) {
  const { data, isLoading, isError } = useChecklistResponse(responseId)
  if (isLoading) return <div className="flex justify-center py-6"><Spinner /></div>
  if (isError || !data) return <p className="text-sm text-gray-500">No se pudo cargar el checklist.</p>
  return <CompletedChecklistView response={data} />
}
