/**
 * Paleta unica de datos.
 *
 * Antes cada grafica traia sus propios hexes (#3b82f6, #16a34a, #f59e0b...),
 * saturados al maximo y de familias distintas: el mismo "verde" no era el
 * mismo verde en el dashboard, en la barra de cumplimiento y en las etiquetas.
 * Aqui viven todos, desaturados por debajo del 80% para que convivan con el
 * navy de marca en lugar de gritar por encima de el.
 */

export const CHART = {
  // Series categoricas
  neutral: '#9ba7b5', // gray-400 de la escala tenida
  brand: '#2f588e', // brand-600
  brandSoft: '#6b93c7', // brand-400

  // Semanticos
  amber: '#c58120',
  amberSoft: '#dfa849',
  green: '#2a8454',
  greenSoft: '#44a772',
  red: '#c6342f',
  redSoft: '#d16561',

  // Cromo de la grafica
  grid: '#e2e7ee', // gray-200
  axis: '#6b7b8e', // gray-500
  cursor: '#f1f4f8', // gray-100
  surface: '#ffffff',
}

/** Colores de estado de una orden de trabajo, en su orden natural de flujo. */
export const STATUS_COLORS = {
  PENDING: CHART.neutral,
  IN_PROGRESS: CHART.brandSoft,
  IN_REVIEW: CHART.amber,
  COMPLETED: CHART.green,
  CANCELLED: CHART.red,
}

/** Umbrales de cumplimiento: verde a partir de 80%, ambar sobre 50%, rojo debajo. */
export function complianceColor(percentage) {
  if (percentage == null) return CHART.neutral
  if (percentage >= 80) return CHART.green
  if (percentage >= 50) return CHART.amber
  return CHART.red
}
