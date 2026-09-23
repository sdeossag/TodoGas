import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useHospitals } from '../../api/assets'
import { SEVERITIES, useFindings, useFindingsSummary } from '../../api/findings'
import { DecisionInfo, DecisionModal, SeverityBadge } from '../../components/findings/FindingsPanel'
import EmptyState from '../../components/ui/EmptyState'
import Spinner from '../../components/ui/Spinner'

const VISTAS = [
  { value: 'PENDING', label: 'Por decidir' },
  { value: 'CONVERTED', label: 'Convertidos' },
  { value: 'DISMISSED', label: 'Descartados' },
  { value: 'RESOLVED', label: 'Resueltos en sitio' },
]

/**
 * Bandeja de hallazgos del planificador (bloque E). Lo que los técnicos
 * encontraron y no resolvieron en sitio: se convierte en una tarea correctiva
 * pendiente (y se agrupa en una OT desde Tareas pendientes) o se descarta con
 * motivo. Lo más grave primero; cada uno dentro del alcance del usuario.
 */
export default function FindingsInboxPage() {
  const [vista, setVista] = useState('PENDING')
  const [hospital, setHospital] = useState('')
  const [severidad, setSeveridad] = useState('')
  const [decidiendo, setDecidiendo] = useState(null) // { hallazgo, accion }

  const { data: hospitales = [] } = useHospitals({ is_active: true })
  const lista = Array.isArray(hospitales) ? hospitales : hospitales?.results ?? []
  const { data: resumen } = useFindingsSummary()
  const params = { status: vista, ...(hospital && { hospital_id: hospital }), ...(severidad && { severity: severidad }) }
  const { data: hallazgos = [], isLoading } = useFindings(params)
  // Uno de una OT que aún no se entrega no se decide: el técnico lo puede corregir.
  const decidibles = (f) => ['IN_REVIEW', 'COMPLETED'].includes(f.work_order_info.status)

  return (
    <div className="space-y-5 max-w-6xl">
      <div>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Hallazgos</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Lo que los técnicos encontraron en campo y hay que corregir.
          {resumen?.serious > 0 && (
            <span className="text-red-700"> {resumen.serious} crítico{resumen.serious > 1 ? 's' : ''} o con equipo fuera de servicio.</span>
          )}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-xl">
          {VISTAS.map((v) => (
            <button key={v.value} type="button" onClick={() => setVista(v.value)}
              className={`px-3 py-1.5 rounded-lg text-sm ${vista === v.value ? 'bg-white shadow-sm font-medium text-gray-900' : 'text-gray-500'}`}>
              {v.label}
              {v.value === 'PENDING' && resumen?.pending > 0 && (
                <span className="ml-1.5 text-xs px-1.5 rounded bg-red-500/90 text-white">{resumen.pending}</span>
              )}
            </button>
          ))}
        </div>
        <select value={hospital} onChange={(e) => setHospital(e.target.value)} className="input-field w-56">
          <option value="">Todos los hospitales</option>
          {lista.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
        <select value={severidad} onChange={(e) => setSeveridad(e.target.value)} className="input-field w-44">
          <option value="">Toda severidad</option>
          {SEVERITIES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-card">
        {isLoading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : hallazgos.length === 0 ? (
          <EmptyState icon="checkCircle" title="Nada por aquí"
            description={vista === 'PENDING' ? 'No hay hallazgos esperando decisión.' : 'No hay hallazgos en esta vista.'} />
        ) : (
          <ul className="divide-y divide-gray-100">
            {hallazgos.map((f) => (
              <li key={f.id} className="p-5 space-y-2">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="min-w-0 space-y-1">
                    <SeverityBadge hallazgo={f} />
                    <p className="text-sm font-medium text-gray-800">
                      {f.asset_info.name} <span className="font-mono text-xs text-gray-500">{f.asset_info.code}</span>
                    </p>
                    <p className="text-xs text-gray-500">
                      {f.work_order_info.hospital}{f.asset_info.node_path ? ` · ${f.asset_info.node_path}` : ''} ·{' '}
                      <Link to={`/ordenes/${f.work_order_info.id}`} className="text-brand hover:underline">{f.work_order_info.wo_code}</Link>
                    </p>
                  </div>
                  {vista === 'PENDING' && (
                    decidibles(f) ? (
                      <div className="flex gap-2">
                        <button type="button" onClick={() => setDecidiendo({ hallazgo: f, accion: 'convert' })} className="btn-primary text-sm">
                          Convertir en correctivo
                        </button>
                        <button type="button" onClick={() => setDecidiendo({ hallazgo: f, accion: 'dismiss' })} className="btn-secondary text-sm">
                          Descartar
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-500">La OT sigue en curso</span>
                    )
                  )}
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-line">{f.description}</p>
                {f.resolved_on_site && <p className="text-sm text-green-800">Qué se hizo: {f.resolution_notes}</p>}
                <DecisionInfo hallazgo={f} />
                <p className="text-xs text-gray-500">
                  {f.reported_by_name} · {new Date(f.reported_at).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })}
                  {f.photos_count > 0 && ` · ${f.photos_count} foto${f.photos_count > 1 ? 's' : ''}`}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>

      {decidiendo && (
        <DecisionModal hallazgo={decidiendo.hallazgo} accion={decidiendo.accion} onClose={() => setDecidiendo(null)} />
      )}
    </div>
  )
}
