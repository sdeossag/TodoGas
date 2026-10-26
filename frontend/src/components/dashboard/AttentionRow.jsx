import { Link } from 'react-router-dom'

import Icon from '../ui/Icon'

// El color dice cuánta urgencia hay; el icono y la frase lo dicen también con
// palabras, para que no dependa de distinguir rojo de ámbar.
const TONES = {
  danger: { icon: 'warning', chip: 'bg-red-50 text-red-700', value: 'text-red-700', note: 'Requiere acción' },
  warn: { icon: 'clock', chip: 'bg-amber-50 text-amber-700', value: 'text-amber-700', note: 'Atender pronto' },
  ok: { icon: 'checkCircle', chip: 'bg-green-50 text-green-700', value: 'text-green-700', note: 'Sin pendientes' },
}

function AttentionCard({ to, title, value, detail, tone }) {
  const t = TONES[tone]
  return (
    <Link to={to} className="card-interactive block p-4">
      <div className="flex items-start gap-3">
        <span className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${t.chip}`}>
          <Icon name={t.icon} className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <p className="label-meta">{title}</p>
          <p className={`mt-1 text-[1.75rem] leading-none stat-value ${t.value}`}>{value}</p>
        </div>
      </div>
      <p className="mt-3 text-sm text-gray-500">
        <span className="font-medium text-gray-700">{t.note}.</span>
        {tone !== 'ok' && ` ${detail}`}
      </p>
    </Link>
  )
}

const severidad = (n, alto) => (n === 0 ? 'ok' : alto ? 'danger' : 'warn')

/**
 * Lo que pide acción hoy, arriba del todo: activos vencidos, hallazgos
 * críticos, OTs vencidas y contratos por atender. Cada tarjeta lleva a la lista.
 */
export default function AttentionRow({ assetsOverdueLink, assetsOverdue, findings, overdue, contracts }) {
  const criticos = findings?.by_severity?.CRITICAL ?? 0
  const ots = overdue?.count ?? 0
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 stagger">
      <AttentionCard
        to={assetsOverdueLink}
        title="Activos con mantenimiento vencido"
        value={assetsOverdue ?? 0}
        detail="Con una tarea preventiva ya pasada de fecha."
        tone={severidad(assetsOverdue ?? 0, true)}
      />
      <AttentionCard
        to="/hallazgos?status=PENDING&severity=CRITICAL"
        title="Hallazgos críticos abiertos"
        value={criticos}
        detail={
          (findings?.out_of_service ?? 0) > 0
            ? `${findings.out_of_service} ${findings.out_of_service === 1 ? 'deja' : 'dejan'} el equipo fuera de servicio.`
            : 'Esperan decisión del planificador.'
        }
        tone={severidad(criticos, true)}
      />
      <AttentionCard
        to="/ordenes"
        title="OTs vencidas"
        value={ots}
        detail={`${overdue?.critical ?? 0} de prioridad alta.`}
        tone={severidad(ots, (overdue?.critical ?? 0) > 0)}
      />
      <AttentionCard
        to="/contratos"
        title="Contratos por atender"
        value={contracts}
        detail="Vencen en 60 días o el hospital no tiene contrato vigente."
        tone={severidad(contracts, false)}
      />
    </div>
  )
}
