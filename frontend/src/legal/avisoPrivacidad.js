// Aviso de privacidad (Ley 1581 de 2012 y Decreto 1377 de 2013).
// Unico lugar donde vive el texto: lo usan el aviso del primer ingreso, la
// pagina publica /privacidad y la linea bajo la firma de quien recibe.
//
// VERSION debe ser igual a PRIVACY_NOTICE_VERSION de backend/config/settings/
// base.py (una prueba del backend lo comprueba). Al cambiar el texto, se suben
// las dos y todos los usuarios vuelven a aceptar.
//
// Los marcadores [RAZÓN SOCIAL], [NIT] y [CORREO DE CONTACTO] los completa el
// cliente antes de publicar.

export const VERSION = '2026-10-28'

export const RAZON_SOCIAL = '[RAZÓN SOCIAL]'

export const TITULO = 'Aviso de privacidad y tratamiento de datos personales'

export const PARRAFOS = [
  '[RAZÓN SOCIAL], NIT [NIT], es la responsable del tratamiento de los datos personales que se registran en esta aplicación de gestión de mantenimiento.',
  'Tratamos su nombre, correo, teléfono, rol y firma, la ubicación GPS de las fotos de evidencia, su dirección IP y el registro de su actividad en la aplicación.',
  'Los usamos para gestionar el mantenimiento de los equipos, generar las actas de servicio, mantener la trazabilidad que exige la normativa sanitaria y enviarle comunicaciones propias del servicio.',
  'Usted tiene derecho a conocer, actualizar y rectificar sus datos, a solicitar su supresión, a revocar la autorización y a presentar quejas ante la Superintendencia de Industria y Comercio (SIC).',
  'Puede ver y descargar sus datos en «Mi perfil». También puede escribirnos a [CORREO DE CONTACTO]. La supresión no alcanza las actas, firmas, fotos ni registros de auditoría ya generados, porque la normativa sanitaria obliga a conservarlos.',
  'La política completa de tratamiento de datos la publica [RAZÓN SOCIAL] y está disponible para todos los titulares.',
]
