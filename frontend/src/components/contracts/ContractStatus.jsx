import { Link } from 'react-router-dom'
import { useHospital } from '../../api/assets'
import { CONTRACT_STATUS } from '../../api/contracts'
import Icon from '../ui/Icon'
import { formatDate } from '../../utils/maintenance'

/** Vigente, por vencer (con los días), vencido o próximo. */
export function EstadoDocumento({ doc }) {
  const estado = CONTRACT_STATUS[doc.status] ?? CONTRACT_STATUS.ACTIVE
  const d = doc.days_left
  const detalle = doc.status === 'EXPIRING'
    ? (d === 0 ? 'vence hoy' : `vence en ${d} día${d !== 1 ? 's' : ''}`)
    : doc.status === 'EXPIRED'
      ? `hace ${-d} día${d !== -1 ? 's' : ''}`
      : null
  return (
    <span className="inline-flex flex-col items-start gap-0.5">
      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${estado.className}`}>{estado.label}</span>
      {detalle && <span className="text-xs text-gray-500">{detalle}</span>}
    </span>
  )
}

/**
 * Garantía y contrato vigentes que cubren un equipo (`asset.coverage` de la
 * API). `enlace`: la ruta de la pantalla de contratos, solo para el personal.
 */
export function CoberturaEquipo({ coverage, enlace }) {
  if (!coverage) return null
  const filas = [
    { titulo: 'Garantía', doc: coverage.warranty, vacio: 'Sin garantía vigente' },
    { titulo: 'Contrato de mantenimiento', doc: coverage.contract, vacio: 'Sin contrato vigente' },
  ]
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {filas.map(({ titulo, doc, vacio }) => (
        <div key={titulo} className={`rounded-lg border px-3 py-2.5 ${doc ? 'border-gray-200' : 'border-dashed border-gray-300'}`}>
          <p className="text-xs font-medium text-gray-500 mb-1">{titulo}</p>
          {doc ? (
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm text-gray-800 truncate">
                  {enlace ? <Link to={enlace} className="hover:underline">{doc.name}</Link> : doc.name}
                </p>
                <p className="text-xs text-gray-500">hasta {formatDate(doc.end_date)}</p>
              </div>
              <EstadoDocumento doc={doc} />
            </div>
          ) : (
            <p className="text-sm text-gray-500">{vacio}</p>
          )}
        </div>
      ))}
    </div>
  )
}

/**
 * Al armar una OT: si el hospital no tiene contrato vigente, lo dice. No
 * bloquea (decisión del 2026-09-23): el planificador decide si la visita va.
 */
export function AvisoSinContrato({ hospitalId }) {
  const { data: hospital } = useHospital(hospitalId)
  const estado = hospital?.contract_status
  if (!estado || estado.has_active) return null
  return (
    <p role="status" className="text-sm text-amber-800 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 flex gap-2">
      <Icon name="warning" className="w-4 h-4 flex-shrink-0 mt-0.5" />
      <span>
        {hospital.name} no tiene contrato de mantenimiento vigente. Puedes crear la OT igual;
        revisa si la visita va por contrato, garantía o se cobra aparte.
      </span>
    </p>
  )
}
