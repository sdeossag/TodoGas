/**
 * Indicador de carga.
 *
 * Vivia duplicado en una docena de paginas, cada copia con su propio tamano.
 * Aqui hay una sola definicion; el color se hereda con currentColor para que
 * tambien sirva dentro de un boton solido.
 */
export default function Spinner({ className = 'h-6 w-6 text-brand', label = 'Cargando' }) {
  return (
    <svg
      className={`animate-spin ${className}`}
      fill="none"
      viewBox="0 0 24 24"
      role="status"
      aria-label={label}
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

/**
 * Filas fantasma con el mismo ritmo que la tabla que van a sustituir.
 * Un circulo girando en el centro de un recuadro vacio no dice nada sobre lo
 * que esta a punto de aparecer; estas barras si.
 */
export function TableSkeleton({ rows = 5, columns = 5 }) {
  const widths = ['w-3/4', 'w-1/2', 'w-5/6', 'w-2/3', 'w-4/5', 'w-3/5']
  return (
    <div className="divide-y divide-gray-100" aria-hidden="true">
      {[...Array(rows)].map((_, r) => (
        <div key={r} className="flex gap-4 px-4 py-3.5">
          {[...Array(columns)].map((_, c) => (
            <div
              key={c}
              className={`h-3 flex-1 rounded-full bg-gray-100 animate-pulse ${
                widths[(r + c) % widths.length]
              }`}
              style={{ animationDelay: `${r * 70}ms` }}
            />
          ))}
        </div>
      ))}
    </div>
  )
}
