/**
 * La API pasó a paginar por defecto (50 por página, configurable hasta 200).
 *
 * Antes cada endpoint de lista devolvía la tabla entera y los componentes
 * hacían `const { data: x = [] } = useX()` para luego mapear. Con la respuesta
 * paginada el valor deja de ser un array y pasa a ser
 * `{ count, next, previous, results }`: el default `= []` ya no entra y el
 * `.map()` revienta. Donde no reventara sería peor, porque la página mostraría
 * en silencio sólo los primeros 50 registros.
 *
 * Estas dos ayudas cubren los dos casos que existen en la aplicación.
 */

// Tope de seguridad: 50 páginas de 200 son 10.000 filas. Si una lista pensada
// como acotada llega aquí, es que dejó de serlo y toca paginarla de verdad en
// la interfaz, no seguir tirando peticiones.
const MAX_PAGES = 50
const PAGE_SIZE = 200

/**
 * Devuelve la lista completa recorriendo todas las páginas.
 *
 * Para listas acotadas por naturaleza que la interfaz filtra en memoria o
 * pinta en un desplegable: usuarios, hospitales, plantillas de checklist,
 * historial de una OT. Con 200 por página casi siempre es una sola petición.
 */
export async function fetchAllPages(client, url, params = {}) {
  const items = []
  for (let page = 1; page <= MAX_PAGES; page += 1) {
    const { data } = await client.get(url, {
      params: { ...params, page, page_size: PAGE_SIZE },
    })
    // Un endpoint que construye su propia Response no pasa por el paginador
    // de DRF y sigue devolviendo un array.
    if (Array.isArray(data)) return data
    items.push(...(data?.results ?? []))
    if (!data?.next) return items
  }
  return items
}

/**
 * Normaliza una respuesta paginada para una interfaz que pinta su paginador.
 *
 * Acepta también un array plano, para que un endpoint sin paginar no obligue
 * a cambiar el componente que lo consume.
 */
export function unwrapPage(data) {
  if (Array.isArray(data)) {
    return { items: data, count: data.length, hasNext: false, hasPrev: false }
  }
  return {
    items: data?.results ?? [],
    count: data?.count ?? 0,
    hasNext: Boolean(data?.next),
    hasPrev: Boolean(data?.previous),
  }
}
