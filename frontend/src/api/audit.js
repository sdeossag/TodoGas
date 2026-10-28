import { useQuery } from '@tanstack/react-query'
import client from './client'

export function useAuditLog(filters = {}) {
  return useQuery({
    queryKey: ['audit-log', filters],
    queryFn: () =>
      client.get('/api/audit/', { params: filters }).then((r) => r.data),
  })
}

/** Nombre del archivo: el del servidor si el navegador lo deja leer, si no uno propio. */
function nombreArchivo(headers, filters) {
  const disposition = headers?.['content-disposition'] ?? ''
  const match = /filename="([^"]+)"/.exec(disposition)
  if (match) return match[1]
  const rango = [filters.date_from, filters.date_to].filter(Boolean).join('_a_')
  return `auditoria_${rango || 'ultimos_90_dias'}.csv`
}

/** El 400 (rango no valido) llega como Blob: hay que leerlo para mostrar `detail`. */
async function mensajeDeError(error) {
  const data = error.response?.data
  try {
    if (data instanceof Blob) return JSON.parse(await data.text()).detail ?? null
    return data?.detail ?? null
  } catch {
    return null
  }
}

/**
 * Descarga el log de auditoria en CSV con los mismos filtros del listado.
 *
 * Va por el cliente (que lleva el token) y no con un enlace, para no poner el
 * token en la URL. Lanza un Error con el mensaje que se puede mostrar.
 */
export async function downloadAuditLogCsv(filters = {}) {
  let response
  try {
    response = await client.get('/api/audit/export/', {
      params: filters,
      responseType: 'blob',
    })
  } catch (error) {
    const detalle = await mensajeDeError(error)
    throw new Error(detalle || 'No se pudo exportar el log de auditoria.')
  }

  const url = URL.createObjectURL(response.data)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombreArchivo(response.headers, filters)
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  URL.revokeObjectURL(url)
}
