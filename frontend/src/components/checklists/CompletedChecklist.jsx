import { useWorkOrderPhotos } from '../../api/evidence'
import { mediaUrl } from '../../api/client'
import Icon from '../ui/Icon'
import useNetworkStore from '../../store/networkStore'
import { countFor, isRepeatable, slotKey } from '../../utils/checklistSlots'
import { booleanLabel } from '../../constants/checklistFields'
import { UbicacionGps } from '../maps/GoogleMap'

/**
 * Checklist cerrado, de solo lectura. Lo comparten el detalle de la OT y el
 * portal del hospital, que ve el checklist de sus OTs finalizadas.
 */

/** Valor del campo foto: `foto:<id>` o, tomada sin red, `sin-conexion:<uuid>`. */
export const FOTO = 'foto:'
export const SIN_CONEXION = 'sin-conexion:'

export function groupFields(fields) {
  const groups = []
  const map = {}
  for (const f of fields) {
    const key = f.group || ''
    if (!map[key]) {
      map[key] = { name: key, fields: [] }
      groups.push(map[key])
    }
    map[key].fields.push(f)
  }
  return groups.length ? groups : [{ name: '', fields }]
}

/**
 * Enlace a la foto de un campo del checklist, con su URL recien firmada.
 *
 * La busca en la evidencia de la OT: por id (`foto:<id>`) o, si se tomo sin
 * red, por el offline_uuid con que se sincronizo. Los valores de antes de este
 * cambio son la URL misma.
 */
export function FotoDelChecklist({ workOrderId, value }) {
  const isOnline = useNetworkStore((s) => s.isOnline)
  const guardaReferencia = value.startsWith(FOTO) || value.startsWith(SIN_CONEXION)
  const { data: fotos = [], isLoading } = useWorkOrderPhotos(
    isOnline && guardaReferencia ? workOrderId : null
  )

  let url = guardaReferencia ? null : value
  if (value.startsWith(FOTO)) {
    url = fotos.find((f) => f.id === value.slice(FOTO.length))?.file_url
  } else if (value.startsWith(SIN_CONEXION)) {
    url = fotos.find((f) => f.offline_uuid === value.slice(SIN_CONEXION.length))?.file_url
  }

  let nota = null
  if (!url && value.startsWith(SIN_CONEXION)) nota = 'tomada sin conexión, se sube con la evidencia'
  else if (!url && !isOnline) nota = 'se puede ver con conexión'
  else if (!url && !isLoading) nota = 'no se encontró en la evidencia de la OT'

  return (
    <span className="inline-flex items-center gap-1 text-green-600">
      <Icon name="camera" className="w-3.5 h-3.5 flex-shrink-0" />
      Foto adjunta
      {url ? (
        <a href={mediaUrl(url)} target="_blank" rel="noopener noreferrer" className="text-brand hover:underline">
          ver
        </a>
      ) : nota && (
        <span className="text-gray-500">· {nota}</span>
      )}
    </span>
  )
}

export default function CompletedChecklistView({ response }) {
  const allFields = response.version_fields ?? []
  const fieldResponses = response.field_responses ?? []
  const answeredMap = Object.fromEntries(
    fieldResponses.map((fr) => [slotKey(fr.field, fr.repetition), fr])
  )
  const groups = groupFields(allFields)
  // Un grupo repetible se muestra una vez por toma: [{ titulo, fields, n }].
  const bloques = groups.flatMap((g) =>
    isRepeatable(response, g.name)
      ? Array.from({ length: countFor(response, g.name) }, (_, i) => ({
          titulo: `${g.name} ${i + 1}`, fields: g.fields, n: i + 1,
        }))
      : [{ titulo: g.name, fields: g.fields, n: 0 }]
  )

  return (
    <div className="space-y-6">
      {/* Summary banner */}
      <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-xl p-4">
        <Icon name="checkCircle" className="w-7 h-7 flex-shrink-0 text-green-600" />
        <div>
          <p className="text-sm font-semibold text-green-800">Checklist completado</p>
          <p className="text-xs text-green-600">
            {response.started_at && `Inicio: ${new Date(response.started_at).toLocaleString('es-CO')} · `}
            Cierre: {new Date(response.completed_at).toLocaleString('es-CO')}
          </p>
          {response._completionPending && (
            <p className="text-xs text-amber-700 mt-0.5">
              Cerrado en el teléfono. Se enviará al servidor al recuperar la conexión.
            </p>
          )}
        </div>
      </div>

      {/* Read-only answers */}
      {bloques.map((group, gi) => (
        <div key={gi} className="space-y-4">
          {group.titulo && (
            <h3 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2">
              {group.titulo}
            </h3>
          )}
          {group.fields.map((field) => {
            const fr = answeredMap[slotKey(field.id, group.n)]
            return (
              <div key={field.id} className="space-y-1">
                <label className="block text-xs font-medium text-gray-500">
                  {field.label}
                  {fr?.out_of_range && (
                    <span className="ml-2 inline-flex items-center gap-1 text-red-600 normal-case font-normal">
                      <Icon name="warning" className="w-3.5 h-3.5" />fuera de rango
                    </span>
                  )}
                </label>
                <div
                  className={`px-3 py-2 rounded-lg border text-sm ${
                    fr?.out_of_range
                      ? 'bg-red-50 border-red-200 text-red-700'
                      : 'bg-gray-50 border-gray-200 text-gray-700'
                  }`}
                >
                  {!fr?.value ? (
                    <span className="text-gray-500 italic">Sin respuesta</span>
                  ) : field.field_type === 'GPS' ? (
                    <UbicacionGps value={fr.value} address={fr.geo_address} answeredAt={fr.answered_at} />
                  ) : field.field_type === 'PHOTO' ? (
                    <FotoDelChecklist workOrderId={response.work_order} value={fr.value} />
                  ) : field.field_type === 'BOOLEAN' ? (
                    booleanLabel(fr.value)
                  ) : (
                    fr.value
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}
