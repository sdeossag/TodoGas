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
    ("encabezado_calificacion", "Encabezado", "Calificación de la orden"),
    ("visita_genero", "Datos de la visita", "Quién generó la orden"),
    ("visita_ejecutor", "Datos de la visita", "Responsable (quién hizo el trabajo)"),
    ("visita_duracion_estimada", "Datos de la visita", "Duración estimada de la orden"),
    ("visita_activos", "Datos de la visita", "Cuántos activos se intervinieron"),
    ("visita_descripcion", "Datos de la visita", "Descripción del trabajo"),
    ("visita_notas", "Datos de la visita", "Notas de la orden"),
    ("activo_ubicacion_equipo", "Activos", "Dónde está el equipo dentro de la ubicación"),
    ("activo_tipo", "Activos", "Tipo de equipo"),
    ("activo_fabricante", "Activos", "Fabricante"),
    ("activo_modelo", "Activos", "Modelo"),
    ("activo_serie", "Activos", "Número de serie"),
    ("activo_clasificaciones", "Activos", "Clasificaciones del equipo"),
    ("activo_prioridad", "Activos", "Prioridad del equipo"),
    ("activo_codigo_barras", "Activos", "Código de barras"),
    ("activo_checklist", "Tareas", "Nombre de la lista de revisión"),
    ("tarea_tipo", "Tareas", "Tipo y prioridad de la tarea"),
    ("tarea_activador", "Tareas", "Activador del protocolo (por ejemplo, Cada 6 meses)"),
    ("visita_fecha_programada", "Tareas", "Fecha programada"),
    ("visita_trabajo_en_campo", "Tareas", "Fecha y hora de inicio y de fin del trabajo"),
    ("tarea_duracion_estimada", "Tareas", "Duración estimada de la tarea"),
    ("visita_duracion", "Tareas", "Tiempo de ejecución"),
    ("tarea_paro", "Tareas", "Tiempo real de paro del activo"),
    ("checklist_observaciones", "Subtareas", "Observaciones de cada resultado"),
    ("checklist_respondido", "Subtareas", "Cuándo y quién hizo la revisión"),
    ("checklist_mapa", "Subtareas", "Mapa de la ubicación tomada con el celular"),
    ("hallazgos", "Hallazgos", "Problemas encontrados y reportados"),
    ("fotos_activo", "Fotos", "Adjuntos (fotos) de cada tarea"),
    ("fotos_visita", "Fotos", "Fotos generales de la visita"),
    ("fotos_gps", "Fotos", "Coordenadas de las fotos"),
    ("materiales", "Materiales", "Materiales utilizados"),
    ("firma_aceptado", "Firmas", "Aceptado por (firma del cliente)"),
    ("firma_validado", "Firmas", "Validado por (aprobación del supervisor)"),
    ("firma_realizado", "Firmas", "Realizado por (firma del técnico)"),
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
