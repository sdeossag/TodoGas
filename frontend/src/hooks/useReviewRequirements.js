import { useQuery } from '@tanstack/react-query'

import { useWorkOrderPhotos, useWorkOrderSignatures } from '../api/evidence'
import { getUnsyncedPhotos, getUnsyncedSignatures } from '../db/repositories'
import useNetworkStore from '../store/networkStore'

/**
 * Lo que falta para enviar la OT a revision, con los mismos tres requisitos
 * que valida el servidor: el checklist de cada tarea cerrado, al menos una
 * foto y la firma. Con varias tareas nombra el activo al que le falta.
 *
 * Sin red se cuenta lo que ya estaba en el servidor al descargar la OT mas lo
 * que se capturo en el telefono y aun no se subio. Asi el tecnico puede
 * enviarla a revision sin conexion: el cambio queda en cola y el motor de
 * sincronizacion lo sube despues de la evidencia.
 */
export default function useReviewRequirements(workOrder) {
  const isOnline = useNetworkStore((s) => s.isOnline)
  const pendingSyncCount = useNetworkStore((s) => s.pendingSyncCount)
  const id = workOrder?.id
  const enCurso = workOrder?.status === 'IN_PROGRESS'

  const { data: fotos = [] } = useWorkOrderPhotos(isOnline && enCurso ? id : null)
  const { data: firmas = [] } = useWorkOrderSignatures(isOnline && enCurso ? id : null)
  const { data: locales = { fotos: 0, firmas: 0 } } = useQuery({
    queryKey: ['local-evidence', id, pendingSyncCount],
    queryFn: async () => ({
      fotos: (await getUnsyncedPhotos(id)).length,
      firmas: (await getUnsyncedSignatures(id)).length,
    }),
    enabled: !!id && enCurso && !isOnline,
    // Solo lee SQLite y solo corre sin red: TanStack la pausaria por defecto.
    networkMode: 'always',
  })

  const totalFotos = isOnline ? fotos.length : (workOrder?.photos_count ?? 0) + locales.fotos
  const totalFirmas = isOnline ? firmas.length : (workOrder?.signatures_count ?? 0) + locales.firmas

  const conChecklist = (workOrder?.tasks ?? []).filter(
    (t) => t.status !== 'CANCELLED' && t.checklist_version
  )
  const sinCerrar = conChecklist.filter((t) => !t.checklist?.completed_at)

  const missing = []
  if (conChecklist.length === 1 && sinCerrar.length === 1) {
    missing.push('completar el checklist')
  } else {
    for (const t of sinCerrar) missing.push(`completar el checklist de ${t.asset.name}`)
  }
  if (totalFotos === 0) missing.push('subir al menos una foto de evidencia')
  if (totalFirmas === 0) missing.push('capturar la firma digital')

  return {
    missing,
    ready: missing.length === 0,
    checklistsDone: conChecklist.length > 0 && sinCerrar.length === 0,
  }
}
