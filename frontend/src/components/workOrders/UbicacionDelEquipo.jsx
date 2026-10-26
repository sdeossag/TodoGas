import { useState } from 'react'

import GoogleMap from '../maps/GoogleMap'
import Icon from '../ui/Icon'
import { rutaLegible, textoOrigen } from '../../utils/ubicacion'

/**
 * Dónde está el equipo (o dónde es la visita): la ruta completa en palabras,
 * su dirección y un mapa pequeño que se pliega. Las coordenadas no se muestran;
 * quien las necesita las tiene en el enlace del mapa.
 *
 * `sub` es la sububicación efectiva que entrega el servidor (propia o heredada).
 * Sin red el mapa de Google no carga y queda la ruta, la dirección y el enlace.
 */
export default function UbicacionDelEquipo({ sub, hospitalName, titulo = 'Dónde está', abierto = true, altura = 160 }) {
  const [verMapa, setVerMapa] = useState(abierto)
  if (!sub) return null
  const hayPunto = sub.latitude !== null && sub.latitude !== undefined && sub.longitude !== null && sub.longitude !== undefined
  const origen = textoOrigen(sub.point_origin)

  return (
    <section aria-label={titulo} className="rounded-xl border border-gray-200 bg-white p-4 space-y-2">
      <div className="flex items-start gap-3">
        <Icon name="area" className="w-4 h-4 mt-0.5 flex-shrink-0 text-gray-400" />
        <div className="min-w-0 flex-1">
          <p className="text-xs text-gray-500">{titulo}</p>
          <p className="text-sm font-medium text-gray-900 leading-snug">{rutaLegible(hospitalName, sub.path || sub.name)}</p>
          {sub.address && <p className="text-sm text-gray-600 leading-snug mt-0.5">{sub.address}</p>}
        </div>
        {hayPunto && (
          <button type="button" onClick={() => setVerMapa((v) => !v)} aria-expanded={verMapa}
            className="flex-shrink-0 text-sm text-brand hover:underline py-1">
            {verMapa ? 'Ocultar mapa' : 'Ver mapa'}
          </button>
        )}
      </div>
      {hayPunto && verMapa && (
        <div className="space-y-1">
          <GoogleMap lat={sub.latitude} lng={sub.longitude} height={altura} zoom={18} />
          {origen && <p className="text-xs text-gray-500">{origen}</p>}
        </div>
      )}
    </section>
  )
}
