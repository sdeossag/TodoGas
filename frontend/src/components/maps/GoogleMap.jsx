import { useEffect, useRef, useState } from 'react'

import Icon from '../ui/Icon'

/**
 * Google Maps (decisión del 2026-09-24), como el campo *LOCALIZACIÓN y la
 * ficha de ubicación de Fracttal: mapa o satélite, zoom, Street View y
 * pantalla completa.
 *
 * La clave va en VITE_GOOGLE_MAPS_API_KEY. Sin clave o sin red (el técnico en
 * un sótano) no se muestra el mapa: quedan las coordenadas y el enlace para
 * abrirlas en Google Maps, que no necesita clave.
 */
const KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY
let cargando = null

export function mapsDisponible() {
  return !!KEY && (typeof navigator === 'undefined' || navigator.onLine !== false)
}

function cargarGoogleMaps() {
  if (window.google?.maps?.Map) return Promise.resolve(window.google.maps)
  if (cargando) return cargando
  cargando = new Promise((resolve, reject) => {
    const callback = '__todogasMapsListo'
    window[callback] = () => resolve(window.google.maps)
    const s = document.createElement('script')
    s.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(KEY)}&language=es&region=CO&loading=async&callback=${callback}`
    s.async = true
    s.onerror = () => { cargando = null; reject(new Error('No cargó Google Maps')) }
    document.head.appendChild(s)
  })
  return cargando
}

export function enlaceGoogleMaps(lat, lng) {
  return `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`
}

/** "4.437887,-75.220034" → { lat, lng }, o null. */
export function parseLatLng(texto) {
  const m = String(texto ?? '').match(/^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/)
  if (!m) return null
  const lat = Number(m[1])
  const lng = Number(m[2])
  return Math.abs(lat) <= 90 && Math.abs(lng) <= 180 ? { lat, lng } : null
}

/**
 * Mapa con un punto. `editable`: un clic o arrastrar el pin cambia el punto
 * (onChange({lat, lng})), y `buscar` agrega el cuadro "Busca en el mapa".
 * Sin punto se centra en Colombia.
 */
export default function GoogleMap({ lat, lng, height = 260, editable = false, buscar = false, onChange, zoom = 17 }) {
  const div = useRef(null)
  const mapa = useRef(null)
  const pin = useRef(null)
  const [estado, setEstado] = useState(mapsDisponible() ? 'cargando' : 'sin-mapa')
  const [texto, setTexto] = useState('')
  const [buscando, setBuscando] = useState(false)
  const [errorBusqueda, setErrorBusqueda] = useState('')
  const tienePunto = lat !== null && lat !== undefined && lng !== null && lng !== undefined

  useEffect(() => {
    if (estado === 'sin-mapa') return undefined
    let vivo = true
    cargarGoogleMaps().then((maps) => {
      if (!vivo || !div.current) return
      const centro = tienePunto ? { lat: Number(lat), lng: Number(lng) } : { lat: 4.6, lng: -74.1 }
      mapa.current = new maps.Map(div.current, {
        center: centro,
        zoom: tienePunto ? zoom : 5,
        mapTypeControl: true,
        streetViewControl: true,
        fullscreenControl: true,
      })
      pin.current = new maps.Marker({ map: mapa.current, position: tienePunto ? centro : null, draggable: editable })
      if (editable) {
        const mover = (pos) => onChange?.({ lat: pos.lat(), lng: pos.lng() })
        mapa.current.addListener('click', (e) => { pin.current.setPosition(e.latLng); mover(e.latLng) })
        pin.current.addListener('dragend', (e) => mover(e.latLng))
      }
      setEstado('listo')
    }).catch(() => vivo && setEstado('sin-mapa'))
    return () => { vivo = false }
    // El mapa se crea una vez; los cambios de punto se aplican abajo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (estado !== 'listo' || !tienePunto) return
    const pos = { lat: Number(lat), lng: Number(lng) }
    pin.current.setPosition(pos)
    mapa.current.panTo(pos)
  }, [estado, lat, lng, tienePunto])

  async function buscarDireccion(e) {
    e.preventDefault()
    if (!texto.trim() || estado !== 'listo') return
    setBuscando(true)
    setErrorBusqueda('')
    try {
      const { results } = await new window.google.maps.Geocoder().geocode({ address: texto, region: 'co' })
      const loc = results[0].geometry.location
      pin.current.setPosition(loc)
      mapa.current.setCenter(loc)
      mapa.current.setZoom(17)
      onChange?.({ lat: loc.lat(), lng: loc.lng(), address: results[0].formatted_address })
    } catch {
      setErrorBusqueda('No encontré esa dirección.')
    } finally {
      setBuscando(false)
    }
  }

  if (estado === 'sin-mapa') {
    return tienePunto ? (
      <a href={enlaceGoogleMaps(lat, lng)} target="_blank" rel="noreferrer"
        className="inline-flex items-center gap-1.5 text-sm text-brand hover:underline">
        <Icon name="area" className="w-4 h-4" /> Abrir en Google Maps
      </a>
    ) : null
  }

  return (
    <div className="space-y-2">
      {buscar && (
        <form onSubmit={buscarDireccion} className="flex gap-2">
          <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Busca en el mapa"
            aria-label="Busca en el mapa" className="input-field" />
          <button type="submit" disabled={buscando || estado !== 'listo'}
            className="px-3 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">
            Buscar
          </button>
        </form>
      )}
      {errorBusqueda && <p className="text-xs text-red-600">{errorBusqueda}</p>}
      <div ref={div} style={{ height }} className="w-full rounded-lg border border-gray-200 bg-gray-100"
        role="img" aria-label="Mapa de la ubicación" />
    </div>
  )
}

/**
 * Lo que muestra un campo GPS respondido, como el *LOCALIZACIÓN de Fracttal:
 * la dirección (la calcula el servidor al sincronizar), las coordenadas, la
 * hora y el mapa.
 */
export function UbicacionGps({ value, address, answeredAt, conMapa = true, height = 220 }) {
  const punto = parseLatLng(value)
  if (!punto) return <span>{value}</span>
  return (
    <div className="space-y-2">
      <div className="text-sm text-gray-700 leading-snug">
        {address && <p>{address}</p>}
        {answeredAt && (
          <p className="text-xs text-gray-500">
            {new Date(answeredAt).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })}
          </p>
        )}
        <p className="text-xs text-gray-500 tabular-nums">Lat: {punto.lat} · Long: {punto.lng}</p>
      </div>
      {conMapa && <GoogleMap lat={punto.lat} lng={punto.lng} height={height} />}
    </div>
  )
}
