/**
 * Iniciales del usuario en un cuadrado redondeado.
 *
 * Deliberadamente no es un circulo: el circulo es el avatar por defecto de
 * cualquier panel, y el squircle encaja mejor con el resto de superficies de
 * la aplicacion, que tambien son rectangulos redondeados.
 */

const SIZES = {
  sm: 'w-7 h-7 text-[11px] rounded-lg',
  md: 'w-9 h-9 text-xs rounded-[0.625rem]',
  lg: 'w-11 h-11 text-sm rounded-xl',
}

const TONES = {
  light: 'bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-200',
  dark: 'bg-white/10 text-white ring-1 ring-inset ring-white/15',
}

function initials(firstName, lastName, fallback) {
  const a = (firstName ?? '').trim()
  const b = (lastName ?? '').trim()
  if (a || b) return `${a.charAt(0)}${b.charAt(0)}`.toUpperCase() || '?'
  return (fallback ?? '').trim().charAt(0).toUpperCase() || '?'
}

export default function Avatar({ user, size = 'md', tone = 'light', className = '' }) {
  return (
    <span
      aria-hidden="true"
      className={`flex-shrink-0 inline-flex items-center justify-center font-semibold
        select-none ${SIZES[size] ?? SIZES.md} ${TONES[tone] ?? TONES.light} ${className}`}
    >
      {initials(user?.first_name, user?.last_name, user?.email)}
    </span>
  )
}
