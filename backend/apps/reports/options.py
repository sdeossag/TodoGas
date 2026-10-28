"""
Que imprime el acta de servicio (#107, decision del 2026-09-23).

Un solo formato con interruptores, como las "Opciones de Impresion" de
Fracttal: el administrador apaga secciones o campos y aplica a las actas
nuevas. Todo esta encendido por defecto, que es el acta de siempre.

Lo que prueba el servicio no se puede apagar (en Fracttal sale con candado):
el numero de OT, el hospital, las respuestas del checklist y el hash de
integridad, que es con lo que un auditor verifica que el acta no se altero.
"""

# (clave, seccion, rotulo). El orden es el de la pantalla de configuracion.
CATALOGO = [
    ("visita_activos", "Datos de la visita", "Cuántos activos se intervinieron"),
    ("visita_ejecutor", "Datos de la visita", "Quién hizo el trabajo"),
    ("visita_fecha_programada", "Datos de la visita", "Fecha programada"),
    ("visita_trabajo_en_campo", "Datos de la visita", "Fecha y hora del trabajo (inicio y fin)"),
    ("visita_duracion", "Datos de la visita", "Tiempo que tomó el trabajo"),
    ("visita_descripcion", "Datos de la visita", "Descripción del trabajo"),
    ("visita_notas", "Datos de la visita", "Notas de la orden"),
    ("activo_ubicacion_equipo", "Activos", "Dónde está el equipo dentro de la ubicación"),
    ("activo_tipo", "Activos", "Tipo de equipo"),
    ("activo_fabricante", "Activos", "Fabricante"),
    ("activo_modelo", "Activos", "Modelo"),
    ("activo_serie", "Activos", "Número de serie"),
    ("activo_checklist", "Checklist", "Nombre de la lista de revisión"),
    ("checklist_observaciones", "Checklist", "Observaciones de cada resultado"),
    ("checklist_respondido", "Checklist", "Cuándo y quién hizo la revisión"),
    ("checklist_mapa", "Checklist", "Mapa de la ubicación tomada con el celular"),
    ("hallazgos", "Hallazgos", "Problemas encontrados y reportados"),
    ("fotos_activo", "Fotos", "Fotos de cada activo"),
    ("fotos_visita", "Fotos", "Fotos generales de la visita"),
    ("fotos_gps", "Fotos", "Coordenadas de las fotos"),
    ("materiales", "Materiales", "Materiales utilizados"),
    ("firma_realizado", "Firmas", "Realizado por (firma del técnico)"),
    ("firma_validado", "Firmas", "Validado por (aprobación del supervisor)"),
    ("firma_aceptado", "Firmas", "Aceptado por (firma del cliente)"),
]

# La ubicacion fisica (ruta del arbol de ubicaciones, con direccion y mapa) sale
# siempre (REV-12): el GPS no distingue equipos de un mismo edificio. Ya no es un
# interruptor; las claves siguen existiendo para que las configuraciones
# guardadas antiguas (que pueden traerlas en false) se sigan leyendo, pero su
# valor se ignora.
OBLIGATORIAS = ("visita_ubicacion", "activo_ubicacion")

CLAVES = {clave for clave, _, _ in CATALOGO} | set(OBLIGATORIAS)

SIEMPRE_INCLUIDO = [
    "Número de orden, tipo y fecha de emisión",
    "Hospital",
    "Ubicación física (ruta de la ubicación): siempre aparece en el acta",
    "Resultados de la revisión (checklist)",
    "Código de verificación en el pie de página",
    "Aviso de firma electrónica (Ley 527 de 1999)",
]


def efectivas(guardadas=None):
    """Todas las claves del catalogo: lo guardado y, lo demas, encendido."""
    guardadas = guardadas or {}
    return {
        clave: True if clave in OBLIGATORIAS else bool(guardadas.get(clave, True))
        for clave in CLAVES
    }


def numeracion(op):
    """
    Numero de cada seccion del acta segun las que esten encendidas, para que
    apagar una no deje un hueco (1, 2, 4...).
    """
    secciones = [
        ("visita", True),
        ("activos", True),
        ("hallazgos", op["hallazgos"]),
        ("fotos_visita", op["fotos_visita"]),
        ("materiales", op["materiales"]),
        ("firmas", op["firma_realizado"] or op["firma_validado"] or op["firma_aceptado"]),
    ]
    return {nombre: i for i, nombre in enumerate((n for n, activa in secciones if activa), start=1)}
