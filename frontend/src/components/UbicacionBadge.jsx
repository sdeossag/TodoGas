/** Marca de un activo que representa una ubicación entera (protocolo por ubicación). */
export default function UbicacionBadge({ asset, className = '' }) {
  if (!asset?.is_location) return null
  return (
    <span className={`ml-1.5 inline-flex items-center rounded-full bg-sky-50 px-2 py-0.5 text-[11px] font-medium text-sky-700 align-middle ${className}`}>
      Ubicación
    </span>
  )
}
