import EmptyState from './EmptyState'

/**
 * Tabla reutilizable con el estilo consistente de la aplicacion.
 *
 * columns: [{ key, header, render?, className?, headerClassName? }]
 * data:    array de filas
 */

// Anchos irregulares en el esqueleto. Todas las barras del mismo largo delatan
// que es un placeholder; el ruido leve se lee como contenido cargando.
const SKELETON_WIDTHS = ['w-3/4', 'w-1/2', 'w-5/6', 'w-2/3', 'w-4/5', 'w-3/5']

export default function Table({
  columns = [],
  data = [],
  loading = false,
  emptyMessage = 'Sin registros.',
  emptyIcon = 'folder',
  emptyDescription,
  emptyAction,
  rowKey = (row, i) => row.id ?? i,
  onRowClick,
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          {/* La cabecera se queda fija al hacer scroll dentro del panel: en una
              lista larga saber que columna se esta leyendo importa mas que el
              par de pixeles que ocupa. */}
          <tr className="bg-gray-50/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={`px-4 py-3 text-left text-xs font-semibold text-gray-600 whitespace-nowrap ${
                  col.headerClassName ?? ''
                }`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {loading ? (
            [...Array(5)].map((_, i) => (
              <tr key={`skeleton-${i}`}>
                {columns.map((col, ci) => (
                  <td key={col.key} className="px-4 py-3.5">
                    <div
                      className={`h-3 rounded-full bg-gray-100 animate-pulse ${
                        SKELETON_WIDTHS[(i + ci) % SKELETON_WIDTHS.length]
                      }`}
                      style={{ animationDelay: `${i * 70}ms` }}
                    />
                  </td>
                ))}
              </tr>
            ))
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length || 1} className="p-0">
                <EmptyState
                  compact
                  icon={emptyIcon}
                  title={emptyMessage}
                  description={emptyDescription}
                  action={emptyAction}
                />
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr
                key={rowKey(row, i)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                // Una fila que responde al raton tiene que responder tambien al
                // teclado; si no, la vista queda inutilizable sin puntero.
                tabIndex={onRowClick ? 0 : undefined}
                role={onRowClick ? 'button' : undefined}
                onKeyDown={
                  onRowClick
                    ? (e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          onRowClick(row)
                        }
                      }
                    : undefined
                }
                className={`transition-colors duration-100 hover:bg-brand-50/60 ${
                  onRowClick
                    ? 'cursor-pointer focus-visible:outline-none focus-visible:bg-brand-50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500'
                    : ''
                }`}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`px-4 py-3.5 text-gray-700 ${col.className ?? ''}`}
                  >
                    {col.render ? col.render(row) : row[col.key] ?? '—'}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
