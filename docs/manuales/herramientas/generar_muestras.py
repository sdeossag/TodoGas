"""Genera los archivos SINTETICOS de muestra para las capturas de importacion.

    backend/.venv/Scripts/python.exe docs/manuales/herramientas/generar_muestras.py

Crea en docs/manuales/herramientas/muestras/:
  - ubicaciones-muestra.xlsx y equipos-muestra.xlsx  (formato del Excel de Fracttal)
  - fracttal-muestra.json                            (formato "fracttal-json-v1" del extractor)

Todo es inventado (sede «Sede Demo Fracttal»): no hay datos reales.
"""
import base64
import io
import json
from pathlib import Path

from openpyxl import Workbook

SALIDA = Path(__file__).parent / "muestras"
SALIDA.mkdir(exist_ok=True)

URL_UBIC = "https://app.fracttal.com/#inventories.facilities/"
URL_EQ = "https://app.fracttal.com/#inventories.equipments/"
COLS_UBIC = ["Habilitado", "Fuera de servicio", "Descripción", "Nombre (C)", "Dirección (C)",
             "Ciudad (C)", "Código", "Notas", "Ubicado en ó es Parte de", "Url Código QR"]
COLS_EQ = ["Habilitado", "Fuera de servicio", "Código", "Nombre (C)", "Fabricante (C)",
           "Modelo (C)", "Número de Serial (C)", "Prioridad", "Clasificación 1",
           "Fecha de Compra", "Ubicado en ó es Parte de", "Plan de Tareas", "Notas",
           "Url Código QR"]


def libro(nombre, columnas, filas):
    wb = Workbook()
    ws = wb.active
    ws.title = "data"
    ws.append(columnas)
    for f in filas:
        ws.append(f)
    wb.save(SALIDA / nombre)


def ubic(nombre, ruta, fid, direccion=None, ciudad=None, codigo=None):
    return ["Si", "No", nombre, nombre, direccion, ciudad, codigo, None, ruta, f"{URL_UBIC}{fid}"]


def equipo(nombre, ruta, fid, codigo=None, prioridad="Media", plan=None, fabricante=None, fuera="No"):
    return ["Si", fuera, codigo, nombre, fabricante, None, None, prioridad, None, "---", ruta, plan, None, f"{URL_EQ}{fid}"]


libro("ubicaciones-muestra.xlsx", COLS_UBIC, [
    ubic("CLINICA DEMO ORIENTE", "// ", 9001, "Av. Demo # 1-23", "CALI"),
    ubic("PISO 1", "// CLINICA DEMO ORIENTE/ ", 9002, codigo="DO-P1"),
    ubic("SALA DE GASES", "// CLINICA DEMO ORIENTE/ PISO 1/ ", 9003),
    ubic("PISO 2", "// CLINICA DEMO ORIENTE/ ", 9004, codigo="DO-P2"),
    # Aviso: la ubicacion intermedia "TORRE B" no existe en el archivo.
    ubic("SALA 201", "// CLINICA DEMO ORIENTE/ TORRE B/ PISO 2/ ", 9005),
])
libro("equipos-muestra.xlsx", COLS_EQ, [
    equipo("TOMA DE OXIGENO 1", "// CLINICA DEMO ORIENTE/ PISO 1/ SALA DE GASES/ ", 9101, "DO-O2-01", fabricante="OHMEDA"),
    equipo("TOMA DE OXIGENO 2", "// CLINICA DEMO ORIENTE/ PISO 1/ SALA DE GASES/ ", 9102, "DO-O2-02", fabricante="OHMEDA"),
    equipo("ALARMA DE PRESION", "// CLINICA DEMO ORIENTE/ PISO 2/ ", 9103, "DO-ALM-01", prioridad="Alta", fabricante="AMICO"),
    # Avisos: sin codigo y con un protocolo que no existe todavia.
    equipo("VALVULA DE CORTE", "// CLINICA DEMO ORIENTE/ PISO 2/ ", 9104, None, plan="PROTOCOLO QUE NO EXISTE"),
    equipo("COMPRESOR DE RESPALDO", "// CLINICA DEMO ORIENTE/ PISO 1/ ", 9105, "DO-CMP-01", fuera="Si"),
])

# ---- JSON del extractor (formato fracttal-json-v1) ----
PNG = base64.b64encode(bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360f8ffff3f0005fe02fea7d6ca6f0000000049454e44ae426082")).decode()
FIRMA = "data:image/png;base64," + PNG


def sub(i, desc, tipo, grupo=None, requerida=False, unidad=None, opciones=None):
    return {"id": i, "descripcion": desc, "tipo": tipo, "grupo": grupo, "orden": i, "requerida": requerida,
            "unidad": unidad, "opciones": opciones or [], "iteraciones": {}, "adjuntos_requeridos": None}


def resp(i, desc, tipo, valor, grupo=None):
    return {"id_plan_subtarea": i, "descripcion": desc, "tipo": tipo, "grupo": grupo, "orden": i,
            "valor": valor, "unidad": None, "hecha": True}


def ot(idot, folio, estado, creada, tecnico, valores):
    return {"id": idot, "folio": folio, "estado": estado, "creada": creada, "creada_por": "PLANIFICADOR EJEMPLO",
            "responsable": tecnico, "nota": "Revisión sin novedades (dato de muestra).", "calificacion": 5,
            "clasificaciones": None, "tareas": [{
                "id": idot * 10, "id_tarea": 500, "id_activo": 200, "descripcion": "REVISION SEMESTRAL",
                "activo": "BOMBA DEMO ALFA", "inicio": creada, "fin": creada, "programada": creada,
                "duracion_seg": 3600, "duracion_real_min": 55, "paro_seg": 600, "tecnico": tecnico, "tipo": None,
                "tipo_principal": "PREVENTIVO", "activador": "DATE$EVERY$6$MONTHS", "prioridad": "HIGH",
                "nota": None, "nota_tarea": "ok", "calificacion": 5, "firma": FIRMA, "hecha": True,
                "subtareas": valores, "archivos": [
                    {"ruta": f".ot/{idot}/a.jpeg", "nombre": "a.jpeg", "descripcion": None, "fecha": creada, "id_subtarea": None}]}]}


def valores(estado_bomba, presion):
    return [resp(2, "Observaciones", "TEXT", "Sin novedades", "GENERAL"),
            resp(3, "Estado bomba", "BOOLEAN", estado_bomba, "GENERAL"),
            resp(4, "Presion", "READING_METER", presion, "LECTURAS"),
            resp(8, "Valvula", "VERIFICATION", "1", "VERIFICAR")]


datos = {
    "formato": "fracttal-json-v1", "extraido": "2026-11-04T00:00:00Z", "sede": "DEMO",
    "ubicaciones": [
        {"id": 100, "id_parent": None, "code": None, "nombre": "SEDE DEMO FRACTTAL", "descripcion": "x",
         "direccion": "Calle 1 # 2-3", "ciudad": "CALI", "latitud": 3.45, "longitud": -76.53,
         "ruta": "// ", "path_node": "100", "habilitado": True, "reconstruida": True},
        {"id": 101, "id_parent": 100, "code": "/DEMO/P1/", "nombre": "PISO UNO", "descripcion": "x", "direccion": None,
         "ciudad": "CALI", "latitud": None, "longitud": None, "ruta": "// SEDE DEMO FRACTTAL/ ",
         "path_node": "100.101", "habilitado": True},
        {"id": 102, "id_parent": 101, "code": None, "nombre": "SALA DE GASES", "descripcion": "x", "direccion": None,
         "ciudad": None, "latitud": None, "longitud": None, "ruta": "// SEDE DEMO FRACTTAL/ PISO UNO/ ",
         "path_node": "100.101.102", "habilitado": True},
    ],
    "activos": [
        {"id": 200, "id_parent": 102, "code": "DEMO-001", "barcode": "B1", "descripcion": "d", "nombre": "BOMBA DEMO ALFA",
         "fabricante": "ACME", "modelo": "M-1", "serie": "S-1", "ubicacion_equipo": None, "otro": None,
         "path_node": "100.101.102.200", "habilitado": True, "disponible": True, "id_plan": 10,
         "plan": "PROTOCOLO DEMO", "prioridad": "HIGH", "centro_costo": "001", "clasificacion_1": "CONTRATO",
         "clasificacion_2": None, "notas": None},
        {"id": 201, "id_parent": 101, "code": None, "barcode": None, "descripcion": "d", "nombre": "VALVULA DEMO BETA",
         "fabricante": None, "modelo": None, "serie": None, "ubicacion_equipo": None, "otro": None,
         "path_node": "100.101.201", "habilitado": False, "disponible": True, "id_plan": None, "plan": None,
         "prioridad": None, "centro_costo": None, "clasificacion_1": None, "clasificacion_2": None, "notas": "vieja"},
    ],
    "planes": [{"id": 10, "nombre": "PROTOCOLO DEMO", "tareas": [
        {"id": 500, "descripcion": "REVISION SEMESTRAL", "duracion_seg": 3600, "activa": True, "tipo": None,
         "tipo_principal": "PREVENTIVO", "tipo_2": None, "prioridad": "HIGH", "paro_activo": True, "paro_seg": 1800,
         "iteraciones": {"num": None, "nombre": {}, "ciclica": None},
         "subtareas": [sub(1, "UBICACION", "GEOREFERENCE"), sub(2, "Observaciones", "TEXT", "GENERAL"),
                       sub(3, "Estado bomba", "BOOLEAN", "GENERAL", requerida=True),
                       sub(4, "Presion", "READING_METER", "LECTURAS", unidad="PSI"),
                       sub(8, "Valvula", "VERIFICATION", "VERIFICAR")]},
        {"id": 501, "descripcion": "PRUEBA ESPECIAL", "duracion_seg": 600, "activa": True, "tipo": "GARANTIA",
         "tipo_principal": "CORRECTIVO", "prioridad": None, "paro_activo": False, "paro_seg": None,
         "iteraciones": {}, "subtareas": [sub(20, "Resultado", "TEXT")]}]}],
    "activadores": [
        {"id_activo": 200, "id_tarea": 500, "activador": "DATE$EVERY$6$MONTHS",
         "proxima": "2027-03-18T15:00:00+00:00", "ultima": "2026-09-18T15:00:00+00:00"},
        {"id_activo": 200, "id_tarea": 501, "activador": "METER$EVERY$100$HOURS", "proxima": None, "ultima": None}],
    "ots": [ot(9001, "7001", 3, "2026-09-18T13:00:00+00:00", "TECNICO EJEMPLO UNO", valores("true", "58")),
            ot(9002, "7002", 3, "2026-03-20T13:00:00+00:00", "TECNICO EJEMPLO DOS", valores("true", "61"))],
}
(SALIDA / "fracttal-muestra.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
print("Muestras generadas en", SALIDA)
