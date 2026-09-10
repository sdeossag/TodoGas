import { Link, useLocation } from 'react-router-dom'
import Icon from '../components/ui/Icon'

/**
 * Ruta inexistente para un usuario ya autenticado.
 *
 * Antes cualquier URL desconocida redirigia en silencio al inicio del rol, asi
 * que un enlace mal copiado parecia un fallo de la aplicacion. Ahora se dice
 * que la direccion no existe y se ofrece la salida.
 */
export default function NotFoundPage({ homePath = '/' }) {
  const location = useLocation()

  return (
    <div className="relative min-h-dvh bg-gray-50 flex items-center justify-center px-6 py-16 grain">
      <div className="relative w-full max-w-lg">
        <p className="font-mono text-sm font-medium text-brand-500 tracking-[0.2em]">ERROR 404</p>

        <h1 className="mt-4 text-[2.5rem] leading-[1.1] font-semibold tracking-tightest text-gray-900">
          Esta dirección no existe.
        </h1>

        <p className="mt-4 text-base leading-relaxed text-gray-600">
          No hay ninguna página en{' '}
          <code className="px-1.5 py-0.5 rounded bg-gray-100 font-mono text-sm text-gray-700 break-all">
            {location.pathname}
          </code>. Puede que el enlace esté desactualizado o que el registro se haya eliminado.
        </p>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Link to={homePath} className="btn-primary">
            <Icon name="arrowLeft" className="w-4 h-4" />
            Volver al inicio
          </Link>
          <button type="button" onClick={() => window.history.back()} className="btn-ghost">
            Página anterior
          </button>
        </div>
      </div>
    </div>
  )
}
