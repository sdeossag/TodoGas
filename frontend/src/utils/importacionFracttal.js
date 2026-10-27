/**
 * Lógica pura de la pantalla "Importar desde Fracttal": qué filas mostrar,
 * cómo contar lo que va a pasar y si se puede importar. Sin React, para poder
 * probarla con node --test.
 */

export const FILTROS_FILAS = [
  { id: 'todas', label: 'Todas' },
  { id: 'errores', label: 'Con errores' },
  { id: 'avisos', label: 'Con avisos' },
]

const ARCHIVOS = { ubicaciones: 'Ubicaciones', equipos: 'Equipos' }

export function nombreArchivo(clave) {
  return ARCHIVOS[clave] ?? clave ?? ''
}

export function filtrarFilas(rows, filtro) {
  const lista = Array.isArray(rows) ? rows : []
  if (filtro === 'errores') return lista.filter((r) => r.errors?.length > 0)
  if (filtro === 'avisos') return lista.filter((r) => r.warnings?.length > 0)
  return lista
}

export function contarFilas(rows) {
  const lista = Array.isArray(rows) ? rows : []
  return {
    todas: lista.length,
    errores: lista.filter((r) => r.errors?.length > 0).length,
    avisos: lista.filter((r) => r.warnings?.length > 0).length,
  }
}

export function puedeImportar(resumen) {
  if (!resumen) return false
  if ((resumen.errors_count ?? 0) > 0) return false
  const total = (resumen.assets?.create ?? 0) + (resumen.assets?.update ?? 0) +
    (resumen.locations?.create ?? 0) + (resumen.locations?.update ?? 0) +
    (resumen.hospitals?.create?.length ?? 0)
  return total > 0
}

export const MENSAJE_CORREGIR = 'Corrige los errores en Fracttal o en el archivo y vuelve a subirlo'

function plural(n, uno, varios) {
  return `${n} ${n === 1 ? uno : varios}`
}

export function textoEquipos(n) {
  return plural(n, 'equipo', 'equipos')
}

export function textoUbicaciones(n) {
  return plural(n, 'ubicación', 'ubicaciones')
}

export function textoProtocolos(n) {
  return plural(n, 'protocolo', 'protocolos')
}

export function textoBotonImportar(resumen) {
  const equipos = (resumen?.assets?.create ?? 0) + (resumen?.assets?.update ?? 0)
  const ubicaciones = (resumen?.locations?.create ?? 0) + (resumen?.locations?.update ?? 0)
  return `Importar ${textoEquipos(equipos)} y ${textoUbicaciones(ubicaciones)}`
}

export function textoResultado(resumen) {
  const creados = resumen?.applied_counts?.plans_created ?? resumen?.plans?.create?.length ?? 0
  const hosp = resumen?.hospitals?.create?.length ?? 0
  const partes = []
  if (hosp > 0) partes.push(plural(hosp, 'hospital nuevo', 'hospitales nuevos'))
  const lc = resumen?.locations?.create ?? 0
  const lu = resumen?.locations?.update ?? 0
  const ac = resumen?.assets?.create ?? 0
  const au = resumen?.assets?.update ?? 0
  if (lc > 0) partes.push(`${textoUbicaciones(lc)} ${lc === 1 ? 'creada' : 'creadas'}`)
  if (lu > 0) partes.push(`${textoUbicaciones(lu)} ${lu === 1 ? 'actualizada' : 'actualizadas'}`)
  if (creados > 0) partes.push(`${textoProtocolos(creados)} ${creados === 1 ? 'creado vacío' : 'creados vacíos'}`)
  if (ac > 0) partes.push(`${textoEquipos(ac)} ${ac === 1 ? 'creado' : 'creados'}`)
  if (au > 0) partes.push(`${textoEquipos(au)} ${au === 1 ? 'actualizado' : 'actualizados'}`)
  return partes
}

export function hayArchivos(archivos) {
  return Boolean(archivos?.ubicaciones || archivos?.equipos)
}

export function esXlsx(archivo) {
  return Boolean(archivo?.name) && /\.xlsx$/i.test(archivo.name)
}

export const MAX_BYTES = 10 * 1024 * 1024

/** Error de un archivo antes de enviarlo, o null si está bien. */
export function errorDeArchivo(archivo) {
  if (!archivo) return null
  if (!esXlsx(archivo)) return 'El archivo debe ser un Excel (.xlsx).'
  if (archivo.size > MAX_BYTES) return 'El archivo pesa más de 10 MB.'
  return null
}
