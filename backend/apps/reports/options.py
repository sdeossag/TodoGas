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
    ("visita_ubicacion", "Datos de la visita", "Ubicación de la visita"),
    ("visita_activos", "Datos de la visita", "Cantidad de activos intervenidos"),
    ("visita_ejecutor", "Datos de la visita", "Ejecutado por"),
    ("visita_fecha_programada", "Datos de la visita", "Fecha programada"),
    ("visita_trabajo_en_campo", "Datos de la visita", "Trabajo en campo (hora de inicio y fin)"),
    ("visita_duracion", "Datos de la visita", "Duración del trabajo"),
    ("visita_descripcion", "Datos de la visita", "Descripción de la intervención"),
    ("visita_notas", "Datos de la visita", "Notas de la OT"),
    ("resumen_activos", "Activos", "Tabla resumen de activos intervenidos"),
    ("activo_ubicacion", "Activos", "Ubicación del activo"),
    ("activo_ubicacion_equipo", "Activos", "Ubicación del equipo"),
    ("activo_tipo", "Activos", "Tipo de activo"),
    ("activo_fabricante", "Activos", "Fabricante"),
    ("activo_modelo", "Activos", "Modelo"),
    ("activo_serie", "Activos", "Número de serie"),
    ("activo_checklist", "Checklist", "Nombre y versión del checklist"),
    ("checklist_observaciones", "Checklist", "Observaciones de cada respuesta"),
    ("checklist_respondido", "Checklist", "Hora y técnico que respondió"),
    ("fotos_activo", "Fotos", "Fotos de cada activo"),
    ("fotos_visita", "Fotos", "Fotos generales de la visita"),
    ("fotos_gps", "Fotos", "Coordenadas GPS de las fotos"),
    ("materiales", "Materiales", "Materiales utilizados"),
    ("firma_realizado", "Firmas", "Realizado por (firma del técnico)"),
    ("firma_validado", "Firmas", "Validado por (aprobación del supervisor)"),
    ("firma_aceptado", "Firmas", "Aceptado por (firma del cliente)"),
]

CLAVES = {clave for clave, _, _ in CATALOGO}

SIEMPRE_INCLUIDO = [
    "Número de OT, tipo y fecha de emisión",
    "Hospital",
    "Respuestas del checklist",
    "Hash de integridad en el pie de página",
]


def efectivas(guardadas=None):
    """Todas las claves del catalogo: lo guardado y, lo demas, encendido."""
    guardadas = guardadas or {}
    return {clave: bool(guardadas.get(clave, True)) for clave in CLAVES}


def numeracion(op):
    """
    Numero de cada seccion del acta segun las que esten encendidas, para que
    apagar una no deje un hueco (1, 2, 4...).
    """
    secciones = [
        ("visita", True),
        ("resumen", op["resumen_activos"]),
        ("activos", True),
        ("fotos_visita", op["fotos_visita"]),
        ("materiales", op["materiales"]),
        ("firmas", op["firma_realizado"] or op["firma_validado"] or op["firma_aceptado"]),
    ]
    return {nombre: i for i, nombre in enumerate((n for n, activa in secciones if activa), start=1)}
