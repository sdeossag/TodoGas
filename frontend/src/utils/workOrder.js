/**
 * Número legible de una OT: OT-2026-00001 (RF-OT-02).
 *
 * El backend lo entrega ya formateado en `wo_code`. El fallback a
 * `OT-{wo_number}` existe para las OT servidas desde SQLite sin conexión: el
 * esquema offline solo guarda el entero `wo_number`, no la cadena compuesta.
 * Así una misma tarjeta se ve igual con red y sin ella, sin arriesgar un
 * "OT-undefined" si algún endpoint todavía no expone wo_code.
 */
export function formatWoCode(wo) {
  if (!wo) return ''
  if (wo.wo_code) return wo.wo_code
  if (wo.wo_number != null) return `OT-${wo.wo_number}`
  return ''
}
