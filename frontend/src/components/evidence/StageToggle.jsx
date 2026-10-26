/**
 * Etiqueta de la foto: Antes o Después del trabajo (audio3 ~05:10).
 *
 * Dos botones grandes, un toque. Tocar el que está marcado lo quita (sin
 * etiqueta). Responde al tocar (active), sin esperar a soltar. Pensado para un
 * técnico con el teléfono en la mano: objetivos de al menos 44 px.
 */

export const STAGES = [
  { value: 'BEFORE', label: 'Antes' },
  { value: 'AFTER', label: 'Después' },
]

export function StageBadge({ stage }) {
  const etiqueta = STAGES.find((s) => s.value === stage)
  if (!etiqueta) return null
  return (
    <span className="inline-block text-xs font-medium rounded-full px-2 py-0.5 bg-brand/10 text-brand">
      {etiqueta.label}
    </span>
  )
}

export default function StageToggle({ value = '', onChange, disabled = false, compact = false }) {
  return (
    <div role="group" aria-label="Momento de la foto" className="flex gap-2 max-w-xs">
      {STAGES.map(({ value: v, label }) => {
        const activo = value === v
        return (
          <button
            key={v}
            type="button"
            aria-pressed={activo}
            disabled={disabled}
            onClick={() => onChange(activo ? '' : v)}
            className={`flex-1 rounded-lg border font-medium transition-transform duration-100 active:scale-95 disabled:opacity-50 ${
              compact ? 'min-h-[44px] text-xs' : 'min-h-[48px] text-sm'
            } ${
              activo
                ? 'bg-brand text-white border-brand'
                : 'bg-white text-gray-700 border-gray-200'
            }`}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
