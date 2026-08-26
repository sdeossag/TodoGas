import { useWorkOrderPhotos, useWorkOrderSignatures } from '../../api/evidence'

function formatDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const yyyy = d.getFullYear()
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${dd}/${mm}/${yyyy} ${hh}:${min}`
}

function PhotoSkeleton() {
  return (
    <div className="space-y-2">
      <div className="w-full aspect-video bg-gray-200 animate-pulse rounded-lg" />
      <div className="h-3 bg-gray-200 animate-pulse rounded w-2/3" />
      <div className="h-3 bg-gray-200 animate-pulse rounded w-1/2" />
    </div>
  )
}

export default function EvidenceGallery({ workOrderId }) {
  const photos = useWorkOrderPhotos(workOrderId)
  const signatures = useWorkOrderSignatures(workOrderId)

  return (
    <div className="space-y-8">
      {/* Fotos */}
      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide border-b border-gray-200 pb-2 mb-4">
          Fotos
        </h3>
        {photos.isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => <PhotoSkeleton key={i} />)}
          </div>
        ) : photos.isError ? (
          <p className="text-sm text-red-400">Error al cargar las fotos.</p>
        ) : !photos.data?.length ? (
          <p className="text-sm text-gray-500">Sin fotos registradas.</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {photos.data.map((photo) => (
              <div key={photo.id} className="space-y-1.5">
                <img
                  src={photo.file_url}
                  alt={photo.caption || 'Foto de evidencia'}
                  className="w-full aspect-video object-cover rounded-lg border border-gray-200"
                />
                {photo.caption && (
                  <p className="text-xs text-gray-600">{photo.caption}</p>
                )}
                <p className="text-xs text-gray-500">{formatDateTime(photo.taken_at)}</p>
                {photo.latitude != null && photo.longitude != null && (
                  <p className="text-xs text-gray-500">
                    {Number(photo.latitude).toFixed(4)}, {Number(photo.longitude).toFixed(4)}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Firmas */}
      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide border-b border-gray-200 pb-2 mb-4">
          Firmas
        </h3>
        {signatures.isLoading ? (
          <div className="space-y-3">
            {[...Array(1)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 animate-pulse rounded-lg" />
            ))}
          </div>
        ) : signatures.isError ? (
          <p className="text-sm text-red-400">Error al cargar las firmas.</p>
        ) : !signatures.data?.length ? (
          <p className="text-sm text-gray-500">Sin firmas registradas.</p>
        ) : (
          <div className="space-y-4">
            {signatures.data.map((sig) => (
              <div
                key={sig.id}
                className="flex flex-col sm:flex-row items-start gap-4 p-4 border border-gray-100 rounded-lg"
              >
                <img
                  src={sig.file_url}
                  alt="Firma"
                  className="h-20 border border-gray-200 rounded bg-white object-contain"
                />
                <div className="space-y-0.5 text-sm">
                  <p className="font-medium text-gray-800">{sig.signer_name}</p>
                  {sig.signer_role && (
                    <p className="text-gray-500 text-xs">{sig.signer_role}</p>
                  )}
                  <p className="text-gray-500 text-xs">{formatDateTime(sig.signed_at || sig.created_at)}</p>
                  {sig.sha256_hash && (
                    <p className="text-gray-500 text-xs font-mono">
                      {sig.sha256_hash.slice(0, 12)}...
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
