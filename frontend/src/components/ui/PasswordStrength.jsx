/**
 * Medidor de fortaleza de contrasena.
 *
 * Los cuatro criterios son los mismos que aplica StrongPasswordValidator en el
 * backend: si aqui marca 4/4, el POST no deberia rebotar por la contrasena.
 */

const SPECIAL_RE = /[!@#$%^&*()\-_=+[\]{};:'",.<>/?\\|`~]/

export function getStrength(password) {
  let score = 0
  if (password.length >= 8) score++
  if (/[A-Z]/.test(password)) score++
  if (/\d/.test(password)) score++
  if (SPECIAL_RE.test(password)) score++
  return score // 0-4
}

const STRENGTH_LABELS = ['', 'Débil', 'Regular', 'Buena', 'Fuerte']
const STRENGTH_COLORS = ['', 'bg-red-400', 'bg-yellow-400', 'bg-blue-400', 'bg-green-500']
const STRENGTH_TEXT = ['', 'text-red-600', 'text-yellow-600', 'text-blue-600', 'text-green-700']

export default function PasswordStrength({ password = '' }) {
  if (!password) return null
  const strength = getStrength(password)

  return (
    <div className="mt-2">
      <div className="flex gap-1 mb-1">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className={`h-1.5 flex-1 rounded-full transition-colors duration-300
              ${strength >= i ? STRENGTH_COLORS[strength] : 'bg-gray-200'}`}
          />
        ))}
      </div>
      <p className={`text-xs font-medium ${STRENGTH_TEXT[strength] || 'text-gray-500'}`}>
        {strength > 0 ? `Fortaleza: ${STRENGTH_LABELS[strength]}` : ''}
      </p>
      <ul className="mt-1 text-xs text-gray-500 space-y-0.5">
        {password.length < 8 && <li>• Mínimo 8 caracteres</li>}
        {!/[A-Z]/.test(password) && <li>• Al menos una mayúscula</li>}
        {!/\d/.test(password) && <li>• Al menos un número</li>}
        {!SPECIAL_RE.test(password) && <li>• Al menos un carácter especial (!@#$%^&*)</li>}
      </ul>
    </div>
  )
}
