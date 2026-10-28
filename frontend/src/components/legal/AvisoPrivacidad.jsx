import { PARRAFOS, TITULO } from '../../legal/avisoPrivacidad'

/** Texto del aviso de privacidad; la unica fuente es legal/avisoPrivacidad.js. */
export default function AvisoPrivacidad({ conTitulo = true }) {
  return (
    <div className="space-y-3 text-sm leading-relaxed text-gray-700">
      {conTitulo && <h2 className="text-base font-semibold text-gray-900">{TITULO}</h2>}
      {PARRAFOS.map((p) => (
        <p key={p}>{p}</p>
      ))}
    </div>
  )
}
