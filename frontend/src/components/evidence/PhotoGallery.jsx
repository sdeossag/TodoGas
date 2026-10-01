import { useState } from 'react'
import { useUpdatePhoto, useWorkOrderPhotos } from '../../api/evidence'
import { mediaUrl } from '../../api/client'

function formatDateCO(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-CO', { timeZone: 'America/Bogota' })
}

function PhotoSkeleton() {
  return (
    <div className="space-y-2">
      <div className="w-full aspect-video bg-gray-200 animate-pulse rounded-lg" />
      <div className="h-3 bg-gray-200 animate-pulse rounded w-3/4" />
      <div className="h-3 bg-gray-200 animate-pulse rounded w-1/2" />
    </div>
  )
}

/**
 * `editable`: quien ejecuta la OT en proceso, o el admin o supervisor que la
 * corrige en revisión, cambia la descripción u oculta una foto del acta. No
 * se borra: queda en la OT y en la auditoría (decisión del 2026-10-01).
 */
export default function PhotoGallery({ workOrderId, editable = false }) {
  const { data: photos = [], isLoading, isError } = useWorkOrderPhotos(workOrderId)

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((n) => <PhotoSkeleton key={n} />)}
      </div>
    )
  }

  if (isError) {
    return <p className="text-sm text-red-400">Error al cargar las fotos.</p>
  }

  if (!photos.length) {
    return <p className="text-sm text-gray-500">Aun no hay fotos registradas.</p>
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {photos.map((photo) => (
        <div key={photo.id} className="space-y-1.5">
          <a href={mediaUrl(photo.file_url)} target="_blank" rel="noopener noreferrer">
            <img
              src={mediaUrl(photo.file_url)}
              alt={photo.caption || 'Foto de evidencia'}
              className={`w-full aspect-video object-cover rounded-lg border border-gray-200 hover:opacity-90 transition-opacity cursor-pointer ${photo.hidden ? 'opacity-40 grayscale' : ''}`}
            />
          </a>
          {photo.hidden && (
            <p className="text-xs text-amber-700">
              Oculta del acta{photo.hidden_by_name && ` por ${photo.hidden_by_name}`}
            </p>
          )}
          {editable ? (
            <CorregirFoto workOrderId={workOrderId} photo={photo} />
          ) : photo.caption && (
            <p className="text-xs text-gray-600">{photo.caption}</p>
          )}
          <p className="text-xs text-gray-500">{formatDateCO(photo.taken_at)}</p>
          {photo.latitude != null && photo.longitude != null ? (
            <a
              href={`https://maps.google.com/?q=${photo.latitude},${photo.longitude}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-brand hover:underline"
            >
              {Number(photo.latitude).toFixed(4)}, {Number(photo.longitude).toFixed(4)}
            </a>
          ) : (
            <p className="text-xs text-gray-500">Sin GPS</p>
          )}
        </div>
      ))}
    </div>
  )
}

function CorregirFoto({ workOrderId, photo }) {
  const updateMut = useUpdatePhoto(workOrderId)
  const [caption, setCaption] = useState(photo.caption ?? '')
  const [error, setError] = useState('')

  async function guardar(cambios) {
    setError('')
    try {
      await updateMut.mutateAsync({ id: photo.id, ...cambios })
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'No se pudo guardar el cambio.')
    }
  }

  return (
    <div className="space-y-1">
      <input
        value={caption}
        onChange={(e) => setCaption(e.target.value)}
        onBlur={() => caption !== (photo.caption ?? '') && guardar({ caption })}
        maxLength={500}
        placeholder="Descripción"
        aria-label="Descripción de la foto"
        className="w-full border border-gray-200 rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-brand/30"
      />
      <button
        type="button"
        onClick={() => guardar({ hidden: !photo.hidden })}
        disabled={updateMut.isPending}
        className="text-xs text-brand hover:underline disabled:opacity-50"
      >
        {photo.hidden ? 'Volver a mostrar en el acta' : 'Ocultar del acta'}
      </button>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}
