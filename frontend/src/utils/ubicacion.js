// Ubicación de un equipo para el detalle de la OT: lo legible y lo que ayuda
// al supervisor, sin coordenadas como dato principal.

const num = (v) => (v === null || v === undefined || v === '' ? null : Number(v))

/** Metros entre dos puntos {lat, lng} (haversine), o null si falta alguno. */
export function distanciaMetros(a, b) {
  const [la1, lo1, la2, lo2] = [num(a?.lat), num(a?.lng), num(b?.lat), num(b?.lng)]
  if ([la1, lo1, la2, lo2].some((v) => v === null || Number.isNaN(v))) return null
  const rad = (g) => (g * Math.PI) / 180
  const h =
    Math.sin(rad(la2 - la1) / 2) ** 2 +
    Math.cos(rad(la1)) * Math.cos(rad(la2)) * Math.sin(rad(lo2 - lo1) / 2) ** 2
  return 2 * 6371000 * Math.asin(Math.sqrt(h))
}

/** La distancia dicha como se lo diría una persona al supervisor. */
export function textoDistancia(metros) {
  if (metros === null || metros === undefined || Number.isNaN(metros)) return ''
  if (metros < 10) return 'Tomado en la ubicación registrada'
  if (metros < 1000) return `Tomado a ${Math.round(metros)} m de la ubicación registrada`
  return `Tomado a ${(metros / 1000).toFixed(1).replace('.', ',')} km de la ubicación registrada`
}

/** "Clínica Demo Norte › Bloque A › Piso 1 › Urgencias". */
export function rutaLegible(hospital, path) {
  return [hospital, ...String(path ?? '').split('/')].map((p) => p?.trim()).filter(Boolean).join(' › ')
}

/** De dónde sale el punto del mapa, en una frase. */
export function textoOrigen(origen) {
  if (!origen) return ''
  return origen.kind === 'own' ? 'Punto propio de esta ubicación' : `Punto ${origen.label}`
}
