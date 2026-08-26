import { useWorkOrderPhotos } from '../../api/evidence'

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

export default function PhotoGallery({ workOrderId }) {
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
          <a href={photo.file_url} target="_blank" rel="noopener noreferrer">
            <img
              src={photo.file_url}
              alt={photo.caption || 'Foto de evidencia'}
              className="w-full aspect-video object-cover rounded-lg border border-gray-200 hover:opacity-90 transition-opacity cursor-pointer"
            />
          </a>
          {photo.caption && (
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
