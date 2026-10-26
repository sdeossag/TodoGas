import { createContext } from 'react'

/**
 * El punto registrado de la ubicación del equipo ({lat, lng}), para que un
 * campo GPS respondido diga a qué distancia se tomó. Sin proveedor, null: el
 * campo se ve como siempre.
 */
export const UbicacionReferencia = createContext(null)
