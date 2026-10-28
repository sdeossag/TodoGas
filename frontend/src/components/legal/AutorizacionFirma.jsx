import { useState } from 'react'

import { PARRAFOS, RAZON_SOCIAL } from '../../legal/avisoPrivacidad'
import { TEXTO_AUTORIZACION_FIRMA } from '../../utils/consentimiento'

/**
 * Linea bajo la firma de quien recibe en el hospital. El aviso se despliega en
 * linea, sin salir de la pantalla de firma (salir perderia la firma en curso).
 */
export default function AutorizacionFirma() {
  const [abierto, setAbierto] = useState(false)

  return (
    <div className="text-xs text-gray-500">
      <p>
        {TEXTO_AUTORIZACION_FIRMA} {RAZON_SOCIAL}.{' '}
        <button
          type="button"
          onClick={() => setAbierto((v) => !v)}
          aria-expanded={abierto}
          className="underline hover:text-gray-700"
        >
          {abierto ? 'Ocultar' : 'Ver aviso de privacidad'}
        </button>
      </p>
      {abierto && (
        <div className="mt-2 space-y-2 leading-relaxed text-gray-600">
          {PARRAFOS.map((p) => (
            <p key={p}>{p}</p>
          ))}
        </div>
      )}
    </div>
  )
}
