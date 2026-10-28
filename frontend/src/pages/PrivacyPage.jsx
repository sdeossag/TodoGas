import { useLocation, useNavigate } from 'react-router-dom'

import AvisoPrivacidad from '../components/legal/AvisoPrivacidad'
import { RAZON_SOCIAL, VERSION } from '../legal/avisoPrivacidad'

/** Pagina publica /privacidad: el aviso, sin necesidad de iniciar sesion. */
export default function PrivacyPage() {
  const navigate = useNavigate()
  const location = useLocation()

  // En la primera pagina de la sesion no hay a donde volver: react-router marca
  // esa entrada con la clave "default".
  function volver() {
    if (location.key !== 'default') navigate(-1)
    else navigate('/', { replace: true })
  }

  return (
    <main className="min-h-dvh bg-gray-50 px-4 py-10">
      <div className="mx-auto max-w-2xl bg-white rounded-xl border border-gray-200 shadow-card p-6 sm:p-8">
        <AvisoPrivacidad />
        <p className="mt-5 text-sm text-gray-600">
          La política completa de tratamiento la publica {RAZON_SOCIAL}.
        </p>
        <p className="mt-6 text-xs text-gray-400">Versión del aviso: {VERSION}</p>
        <button
          type="button"
          onClick={volver}
          className="mt-4 inline-block text-sm text-brand underline"
        >
          Volver
        </button>
      </div>
    </main>
  )
}
