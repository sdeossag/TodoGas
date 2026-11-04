"""Importacion desde el JSON que produce el extractor de Fracttal.

Formato "fracttal-json-v1" (ver docs/fracttal/extractor-fracttal.js). Trae una
sede completa: ubicaciones, activos, protocolos con sus subtareas, activadores
y el historial de OTs con sus respuestas. Este modulo no conoce HTTP ni consola:

  leer(archivo)      ->  datos (dict ya validado)
  planificar(datos)  ->  Plan (solo lee la base de datos)
  aplicar(plan, user) ->  escribe todo en UNA transaccion

Es el hermano de `importacion_fracttal` (Excel) y reutiliza sus piezas de
texto. Las dos importaciones conviven: se emparejan por el id de Fracttal
(`fracttal_id`) o, si no lo tienen, por nombre o codigo.

Reglas que importan:
  - Reimportar actualiza lo que ya vino de Fracttal y no duplica. Las OT
    historicas que ya estan (por su id de Fracttal) se saltan: no se reescriben.
  - Las OT historicas se escriben directo en la base, sin pasar por las
    transiciones: sin acta PDF, sin correos, sin notificaciones. Quedan con
    `origin="FRACTTAL"`; el verificador de integridad las ignora.
  - Las personas de Fracttal no son usuarios: sus nombres quedan como texto.
"""

import base64
import hashlib
import json
import re
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from apps.checklists.models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)
from apps.evidence.models import Signature
from apps.maintenance.models import (
    MaintenancePlan,
    PlanTask,
    Task,
    TaskTypeCatalog,
)
from apps.maintenance.services import ensure_open_task, set_asset_plan
from apps.work_orders.models import WorkOrder, WorkOrderStatusHistory

from .importacion_fracttal import ImportacionError, _slug, _unico, normalizar
from .models import Asset, AssetNode, Hospital

FORMATO = "fracttal-json-v1"
LOTE = 1000  # filas por bulk_create
LOTE_OT = 150  # OT por lote al escribir el historial
MAX_EJEMPLOS = 5

FT = ChecklistField.FieldType

# Tipo de subtarea de Fracttal -> tipo de campo nuestro.
TIPOS_CAMPO = {
    "TEXT": FT.TEXT,
    "BOOLEAN": FT.BOOLEAN,
    "NUMBER": FT.NUMBER,
    # Decision: NUMBER con unidad y no METER. METER se enlaza con las unidades
    # y lecturas de medidor (activadores "Cada"/"Cuando"); un valor historico
    # de presion en PSI no es una lectura viva de un contador y reinterpretarlo
    # al sincronizar podria disparar tareas. NUMBER guarda el numero y la unidad.
    "READING_METER": FT.NUMBER,
    "GEOREFERENCE": FT.GPS,
    "DROPDOWN": FT.SELECT,
    "DATE_TIME": FT.DATETIME,
    "VERIFICATION": FT.PASS_ALERT_FAIL,
}
VERIFICACION = {"1": "APROBO", "2": "ALERTA", "3": "FALLO"}
PRIORIDADES = {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
UNIDADES = {"DAYS": "DAYS", "WEEKS": "WEEKS", "MONTHS": "MONTHS", "YEARS": "YEARS"}
_RE_CADA = re.compile(r"^DATE\$EVERY\$(\d+)\$([A-Z]+)$")
_RE_HORA_GEO = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2}):(\d{2}):(\d{2})\s*$")


# --------------------------------------------------------------------------
# Textos y fechas
# --------------------------------------------------------------------------


def _txt(valor, largo=None):
    """Texto sin espacios repetidos ni sobrantes. Conserva las barras."""
    if valor is None:
        return ""
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    return texto[:largo] if largo else texto


def _fid(valor):
    return "" if valor is None else str(valor)


def _dt(valor):
    """ISO-8601 de Fracttal -> datetime con zona, o None."""
    if not valor:
        return None
    try:
        d = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None
    return timezone.make_aware(d, timezone.utc) if timezone.is_naive(d) else d


def _fecha_local(dt):
    return timezone.localtime(dt).date() if dt else None


def _decimal(valor, maximo):
    if valor in (None, ""):
        return None
    try:
        d = Decimal(str(valor)).quantize(Decimal("0.0000001"))
    except (InvalidOperation, ValueError):
        return None
    return d if abs(d) <= maximo else None


def _segundos(valor):
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return None
    return timedelta(seconds=n) if n > 0 else None


# --------------------------------------------------------------------------
# Lectura
# --------------------------------------------------------------------------

_LISTAS = ("ubicaciones", "activos", "planes", "activadores", "ots")


def leer(archivo):
    """Lee y valida el JSON. `archivo` es una ruta o un archivo abierto."""
    try:
        if hasattr(archivo, "read"):
            if hasattr(archivo, "seek"):
                archivo.seek(0)
            crudo = archivo.read()
        else:
            with open(archivo, "rb") as f:
                crudo = f.read()
        if isinstance(crudo, bytes):
            crudo = crudo.decode("utf-8-sig")
        datos = json.loads(crudo)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ImportacionError("El archivo no es un JSON válido.") from exc
    if not isinstance(datos, dict) or datos.get("formato") != FORMATO:
        raise ImportacionError(f"El archivo no es del formato «{FORMATO}» del extractor de Fracttal.")
    for clave in _LISTAS:
        if not isinstance(datos.get(clave, []), list):
            raise ImportacionError(f"El campo «{clave}» del archivo debe ser una lista.")
        datos.setdefault(clave, [])
    return datos


# --------------------------------------------------------------------------
# Plan
# --------------------------------------------------------------------------


class _Avisos:
    """Avisos agrupados por categoria: un conteo y unos pocos ejemplos."""

    def __init__(self):
        self._g = {}

    def add(self, categoria, mensaje, ejemplo=None):
        g = self._g.setdefault(categoria, {"mensaje": mensaje, "cantidad": 0, "ejemplos": []})
        g["cantidad"] += 1
        if ejemplo and len(g["ejemplos"]) < MAX_EJEMPLOS and ejemplo not in g["ejemplos"]:
            g["ejemplos"].append(ejemplo)

    def lista(self):
        return list(self._g.values())

    @property
    def total(self):
        return sum(g["cantidad"] for g in self._g.values())


@dataclass
class HospitalJ:
    fid: str
    nombre: str
    campos: dict
    existente: object = None
    codigo: str = ""


@dataclass
class NodoJ:
    fid: str
    hospital_fid: str
    padre_fid: str  # "" = cuelga del hospital
    nombre: str
    campos: dict
    activo: bool = True
    existente: object = None
    profundidad: int = 0


@dataclass
class ActivoJ:
    fid: str
    hospital_fid: str
    nodo_fid: str
    campos: dict
    plan_fid: str = ""
    existente: object = None
    proximas: dict = field(default_factory=dict)  # id de tarea -> fecha local


@dataclass
class CampoJ:
    """Una subtarea de Fracttal convertida a campo de checklist."""

    fid: str
    label: str
    tipo: str
    grupo: str
    orden: int
    requerida: bool
    opciones: object  # list o dict (options_json)

    def firma(self):
        return (self.orden, self.label, self.tipo, self.grupo, self.requerida)


@dataclass
class TareaPlanJ:
    fid: str
    plan_fid: str
    nombre: str
    campos: dict  # campos de PlanTask
    tipo_nombre: str
    checklist: list  # [CampoJ]
    existente: object = None
    plan_existente_con_checklist: bool = False


@dataclass
class PlanJ:
    fid: str
    nombre: str
    existente: object = None
    tareas: list = field(default_factory=list)


@dataclass
class OtJ:
    datos: dict
    existe: bool = False


@dataclass
class Plan:
    sede: str = ""
    hospitales: dict = field(default_factory=dict)  # fid -> HospitalJ
    nodos: dict = field(default_factory=dict)  # fid -> NodoJ
    activos: dict = field(default_factory=dict)  # fid -> ActivoJ
    planes: dict = field(default_factory=dict)  # fid -> PlanJ
    ots: list = field(default_factory=list)
    adhoc: dict = field(default_factory=dict)  # id de tarea -> TareaPlanJ (sin protocolo)
    conteo: dict = field(default_factory=dict)
    avisos: _Avisos = field(default_factory=_Avisos)
    errores_lista: list = field(default_factory=list)

    @property
    def errores(self):
        return len(self.errores_lista)

    def resumen(self, aplicado=False):
        c = self.conteo
        return {
            "format": FORMATO,
            "sede": self.sede,
            "hospitals": {
                "create": [h.nombre for h in self.hospitales.values() if h.existente is None],
                "existing": [h.nombre for h in self.hospitales.values() if h.existente is not None],
            },
            "locations": {
                "create": sum(1 for n in self.nodos.values() if n.existente is None),
                "update": sum(1 for n in self.nodos.values() if n.existente is not None),
            },
            "assets": {
                "create": sum(1 for a in self.activos.values() if a.existente is None),
                "update": sum(1 for a in self.activos.values() if a.existente is not None),
            },
            "plans": {
                "create": sum(1 for p in self.planes.values() if p.existente is None),
                "update": sum(1 for p in self.planes.values() if p.existente is not None),
            },
            "plan_tasks": {
                "create": sum(1 for p in self.planes.values() for t in p.tareas if t.existente is None),
                "update": sum(1 for p in self.planes.values() for t in p.tareas if t.existente is not None),
            },
            "checklist_fields": c.get("campos", 0),
            "field_types": c.get("tipos_campo", {}),
            "triggers": c.get("activadores", {}),
            "work_orders": {
                "create": sum(1 for o in self.ots if not o.existe),
                "existing": sum(1 for o in self.ots if o.existe),
                "completed": c.get("ot_finalizadas", 0),
                "cancelled": c.get("ot_canceladas", 0),
            },
            "tasks": c.get("tareas_ot", 0),
            "responses": c.get("respuestas", 0),
            "signatures": c.get("firmas", 0),
            "photos_pending": c.get("fotos", 0),
            "warnings": self.avisos.lista(),
            "warnings_count": self.avisos.total,
            "errors": list(self.errores_lista),
            "errors_count": self.errores,
            "applied": aplicado,
        }


def _unidad_de_activador(texto):
    """'DATE$EVERY$6$MONTHS' -> ('DATE', 6, 'MONTHS'); 'NO_SCHEDULE_TASK' -> ('EVENT', None, '').

    Devuelve None si no se reconoce.
    """
    texto = (texto or "").strip().upper()
    if texto == "NO_SCHEDULE_TASK":
        return ("EVENT", None, "")
    m = _RE_CADA.match(texto)
    if m and m.group(2) in UNIDADES and int(m.group(1)) > 0:
        return ("DATE", int(m.group(1)), UNIDADES[m.group(2)])
    return None


def _compatible(tipo_ot, tipo_campo):
    """La respuesta de la OT (tipo de Fracttal) cabe en el campo (tipo nuestro)."""
    esperado = TIPOS_CAMPO.get(str(tipo_ot))
    if esperado is None:
        return False
    return str(esperado) == str(tipo_campo) or {str(esperado), str(tipo_campo)} == {"TEXT", "TEXTAREA"}


def _convertir_campo(s, con_saltos):
    """Subtarea de Fracttal -> CampoJ, o (None, motivo) si el tipo no se conoce."""
    tipo = TIPOS_CAMPO.get(str(s.get("tipo")))
    if tipo is None:
        return None
    label = _txt(s.get("descripcion"), 500) or "(sin texto)"
    opciones = []
    if tipo == FT.SELECT:
        opciones = [_txt(o) for o in (s.get("opciones") or []) if _txt(o)]
    elif tipo == FT.NUMBER and s.get("unidad"):
        opciones = {"unit": _txt(s["unidad"], 20)}
    elif tipo in (FT.BOOLEAN, FT.PASS_ALERT_FAIL):
        opciones = {"allow_na": True}
    elif tipo == FT.TEXT and _fid(s.get("id")) in con_saltos:
        tipo = FT.TEXTAREA
    return CampoJ(
        fid=_fid(s.get("id") if s.get("id") is not None else s.get("id_plan_subtarea")),
        label=label,
        tipo=str(tipo),
        grupo=_txt(s.get("grupo"), 100),
        orden=int(s.get("orden") or 0),
        requerida=bool(s.get("requerida")),
        opciones=opciones,
    )


class _Planificador:
    def __init__(self, datos):
        self.d = datos
        self.plan = Plan(sede=_txt(datos.get("sede")))
        self.av = self.plan.avisos
        self.hospitales_db = {}
        self.hospitales_fid = {}
        for h in Hospital.objects.order_by("created_at"):
            self.hospitales_db.setdefault(normalizar(h.name), h)
            if h.fracttal_id:
                self.hospitales_fid[h.fracttal_id] = h
        self.codigos_hospital = {c.lower() for c in Hospital.objects.values_list("code", flat=True)}
        self.codigos_activo = {c.lower() for c in Asset.objects.values_list("code", flat=True)}
        self.nodos_por_fid = {n.fracttal_id: n for n in AssetNode.objects.exclude(fracttal_id="")}
        self.nodos_por_nombre = {}
        for n in AssetNode.objects.all():
            self.nodos_por_nombre.setdefault((n.hospital_id, n.parent_id, normalizar(n.name)), n)
        self.activos_por_fid = {a.fracttal_id: a for a in Asset.objects.exclude(fracttal_id="")}
        self.activos_por_codigo = {}
        for a in Asset.objects.filter(fracttal_id=""):
            self.activos_por_codigo.setdefault(a.code.lower(), a)
        self.planes_por_fid = {p.fracttal_plan_id: p for p in MaintenancePlan.objects.exclude(fracttal_plan_id="")}
        self.planes_por_nombre = {}
        for p in MaintenancePlan.objects.order_by("created_at"):
            self.planes_por_nombre.setdefault(normalizar(p.name), p)
        self.catalogo = {normalizar(t.name): t for t in TaskTypeCatalog.objects.all()}
        self.hospital_de_nodo = {}  # fid de nodo -> fid de hospital

    # --- ubicaciones --------------------------------------------------------
    def ubicaciones(self):
        locs = {}
        for u in self.d["ubicaciones"]:
            fid = _fid(u.get("id"))
            if not fid:
                self.plan.errores_lista.append("Una ubicación no trae id.")
                continue
            if fid in locs:
                self.plan.errores_lista.append(f"El id de ubicación {fid} está repetido en el archivo.")
                continue
            locs[fid] = u
        self.locs = locs

        def raiz_de(fid):
            visto = set()
            while True:
                p = _fid(locs[fid].get("id_parent"))
                if not p or p not in locs or p in visto:
                    return fid
                visto.add(fid)
                fid = p

        # Raices = hospitales.
        for fid, u in locs.items():
            p = _fid(u.get("id_parent"))
            if p and p in locs:
                continue
            if p:  # padre fuera del archivo: se trata como raiz
                self.av.add("raiz_huerfana", "Ubicaciones cuyo padre no viene en el archivo; se tratan como sede.",
                            _txt(u.get("nombre")))
            nombre = _txt(u.get("nombre"), 255) or _txt(u.get("descripcion"), 255) or f"Sede {fid}"
            existente = self.hospitales_fid.get(fid) or self.hospitales_db.get(normalizar(nombre))
            lat = _decimal(u.get("latitud"), Decimal("90"))
            lon = _decimal(u.get("longitud"), Decimal("180"))
            campos = {
                "address": _txt(u.get("direccion"), 255),
                "city": _txt(u.get("ciudad"), 100),
                "department": _txt(u.get("departamento"), 100),
                "latitude": lat,
                "longitude": lon,
                "is_active": u.get("habilitado") is not False,
            }
            hp = HospitalJ(fid=fid, nombre=existente.name if existente else nombre, campos=campos, existente=existente)
            if existente is None:
                hp.codigo = _unico(_slug(nombre, 40), self.codigos_hospital, 50)
            if u.get("reconstruida"):
                self.av.add("raiz_reconstruida", "La sede raíz no venía en Fracttal y se reconstruyó por su ruta.",
                            nombre)
            self.plan.hospitales[fid] = hp
            self.hospital_de_nodo[fid] = fid

        if not self.plan.hospitales:
            self.plan.errores_lista.append("El archivo no trae ninguna sede (ubicación raíz).")
            return

        # Nodos (todo lo que no es raiz), padres primero.
        hijos_de = defaultdict(list)
        for fid, u in locs.items():
            if fid in self.plan.hospitales:
                continue
            hijos_de[_fid(u.get("id_parent"))].append(fid)
        cola = [(h, "", 1) for h in self.plan.hospitales]
        usados = {}  # (hospital_fid, padre_fid, nombre normalizado) -> fid
        vistos = set(self.plan.hospitales)
        while cola:
            padre, _, prof = cola.pop(0)
            hosp = self.hospital_de_nodo[padre]
            padre_nodo = "" if padre in self.plan.hospitales else padre
            for fid in sorted(hijos_de.get(padre, []), key=lambda f: locs[f].get("nombre") or ""):
                if fid in vistos:
                    continue
                vistos.add(fid)
                u = locs[fid]
                self.hospital_de_nodo[fid] = hosp
                nombre = _txt(u.get("nombre"), 255) or _txt(u.get("descripcion"), 255) or f"Ubicación {fid}"
                clave = (hosp, padre_nodo, normalizar(nombre))
                if clave in usados:
                    self.av.add("nombre_repetido", "Ubicaciones hermanas con el mismo nombre; se les añadió el id.",
                                nombre)
                    nombre = f"{nombre} ({fid})"[:255]
                    clave = (hosp, padre_nodo, normalizar(nombre))
                usados[clave] = fid
                lat = _decimal(u.get("latitud"), Decimal("90"))
                lon = _decimal(u.get("longitud"), Decimal("180"))
                direccion = ", ".join(x for x in (_txt(u.get("direccion")), _txt(u.get("ciudad"))) if x)[:255]
                campos = {
                    "code": _txt(u.get("code"), 50),
                    "address": direccion,
                    "latitude": lat,
                    "longitude": lon,
                }
                self.plan.nodos[fid] = NodoJ(
                    fid=fid, hospital_fid=hosp, padre_fid=padre_nodo, nombre=nombre, campos=campos,
                    activo=u.get("habilitado") is not False, profundidad=prof,
                )
                cola.append((fid, "", prof + 1))
        for fid in locs:
            if fid not in vistos:
                self.av.add("ubicacion_aislada", "Ubicaciones que no cuelgan de ninguna sede; no se importan.",
                            _txt(locs[fid].get("nombre")))

        # Emparejar con lo que ya existe, padres primero.
        for n in sorted(self.plan.nodos.values(), key=lambda x: x.profundidad):
            hosp = self.plan.hospitales[n.hospital_fid]
            existente = self.nodos_por_fid.get(n.fid)
            if existente is not None:
                if hosp.existente is None or existente.hospital_id != hosp.existente.id:
                    self.plan.errores_lista.append(
                        f"La ubicación «{n.nombre}» (id {n.fid}) ya existe en otro hospital."
                    )
                    continue
            elif hosp.existente is not None:
                padre_id = None
                if n.padre_fid:
                    padre = self.plan.nodos[n.padre_fid].existente
                    padre_id = padre.id if padre is not None else False
                if padre_id is not False:
                    cand = self.nodos_por_nombre.get((hosp.existente.id, padre_id, normalizar(n.nombre)))
                    if cand is not None and not cand.fracttal_id:
                        existente = cand
                    elif cand is not None:
                        self.av.add("nombre_ocupado",
                                    "Ya existe una ubicación con ese nombre y otro id de Fracttal; se crea con el id añadido.",
                                    n.nombre)
                        n.nombre = f"{n.nombre} ({n.fid})"[:255]
            n.existente = existente

    # --- protocolos ---------------------------------------------------------
    def _tipo_de_tarea(self, tipo, principal):
        """Codigo del catalogo para una tarea. Nunca crea tipos nuevos."""
        t = self.catalogo.get(normalizar(tipo)) if tipo else None
        if t is not None:
            return t.code
        pr = normalizar(principal)
        if tipo and normalizar(tipo) not in ("preventivo", "correctivo"):
            self.av.add("tipo_sin_catalogo",
                        "Tipos de tarea de Fracttal que no están en el catálogo; la tarea toma Preventivo o Correctivo.",
                        _txt(tipo))
        if pr.startswith("correctiv"):
            return "CORRECTIVE"
        if pr.startswith("preventiv"):
            return "PREVENTIVE"
        t = self.catalogo.get(pr) if pr else None
        if t is not None:
            return t.code
        self.av.add("tipo_desconocido", "Tareas sin tipo reconocible; quedan como Preventivo.", _txt(tipo or principal))
        return "PREVENTIVE"

    def protocolos(self):
        # Subtareas con saltos de linea en alguna respuesta -> TEXTAREA.
        con_saltos = set()
        for o in self.d["ots"]:
            for t in o.get("tareas", []):
                for s in t.get("subtareas", []):
                    if s.get("tipo") == "TEXT" and "\n" in str(s.get("valor") or ""):
                        con_saltos.add(_fid(s.get("id_plan_subtarea")))
        self.con_saltos = con_saltos

        # Activadores por tarea.
        por_tarea = defaultdict(list)
        self.proximas = defaultdict(dict)  # fid de activo -> {id tarea: fecha}
        for a in self.d["activadores"]:
            idt = _fid(a.get("id_tarea"))
            por_tarea[idt].append(a)
            f = _fecha_local(_dt(a.get("proxima")))
            if f:
                self.proximas[_fid(a.get("id_activo"))][idt] = f
        tipos_activador = Counter()

        for p in self.d["planes"]:
            pfid = _fid(p.get("id"))
            nombre = _txt(p.get("nombre"), 255)
            if not pfid or not nombre:
                self.av.add("plan_sin_nombre", "Protocolos sin id o sin nombre; se saltan.", pfid or "(sin id)")
                continue
            existente = self.planes_por_fid.get(pfid) or self.planes_por_nombre.get(normalizar(nombre))
            pj = PlanJ(fid=pfid, nombre=nombre, existente=existente)
            tareas_db = {}
            if existente is not None:
                for t in existente.tasks.all():
                    tareas_db[t.fracttal_task_id or ""] = t
                    tareas_db.setdefault("n:" + normalizar(t.name), t)
            for i, t in enumerate(p.get("tareas", [])):
                tfid = _fid(t.get("id"))
                nombre_t = _txt(t.get("descripcion"), 255) or f"Tarea {tfid}"
                campos_cl = []
                for s in sorted(t.get("subtareas", []), key=lambda x: x.get("orden") or 0):
                    c = _convertir_campo(s, con_saltos)
                    if c is None:
                        self.av.add("subtarea_tipo", "Subtareas de un tipo desconocido; se saltan.",
                                    f"{s.get('tipo')}: {_txt(s.get('descripcion'), 60)}")
                        continue
                    campos_cl.append(c)
                    self.plan.conteo.setdefault("tipos_campo", {})
                    self.plan.conteo["tipos_campo"][c.tipo] = self.plan.conteo["tipos_campo"].get(c.tipo, 0) + 1
                self.plan.conteo["campos"] = self.plan.conteo.get("campos", 0) + len(campos_cl)

                # Activador: el mas comun entre los activos de la tarea.
                reconocidos = Counter()
                crudos = Counter()
                for a in por_tarea.get(tfid, []):
                    r = _unidad_de_activador(a.get("activador"))
                    crudos[a.get("activador")] += 1
                    if r is not None:
                        reconocidos[r] += 1
                trig, valor, unidad = "EVENT", None, ""
                if reconocidos:
                    (trig, valor, unidad), _ = reconocidos.most_common(1)[0]
                    if len(reconocidos) > 1 or len(crudos) > len(reconocidos):
                        self.av.add("activador_mixto",
                                    "Tareas con activadores distintos entre sus activos; se usa el más común.",
                                    nombre_t)
                    tipos_activador["DATE" if trig == "DATE" else "EVENT (sin programar)"] += 1
                elif crudos:
                    self.av.add("activador_no_reconocido",
                                "Activadores que no se reconocen; la tarea queda por evento (sin programar).",
                                f"{nombre_t}: {', '.join(str(k) for k in crudos)}")
                    tipos_activador["no reconocido"] += 1
                else:
                    self.av.add("sin_activador",
                                "Tareas sin activador en el archivo; quedan por evento (el planificador las crea).",
                                nombre_t)
                    tipos_activador["sin activador"] += 1

                paro = _segundos(t.get("paro_seg")) if t.get("paro_activo") else None
                campos = {
                    "name": nombre_t,
                    "description": "" if not t.get("tipo") else f"Tipo en Fracttal: {_txt(t.get('tipo'))}",
                    "task_type": self._tipo_de_tarea(t.get("tipo"), t.get("tipo_principal")),
                    "priority": PRIORIDADES.get(str(t.get("prioridad")), "MEDIUM"),
                    "trigger": trig,
                    "frequency_value": valor,
                    "frequency_unit": unidad,
                    "estimated_duration": _segundos(t.get("duracion_seg")),
                    "downtime_duration": paro,
                    "is_active": t.get("activa") is not False,
                    "sort_order": i,
                    "fracttal_task_id": tfid,
                }
                if (t.get("iteraciones") or {}).get("num"):
                    self.av.add("iteraciones", "Tareas con repeticiones (iteraciones) de Fracttal; no se traducen.",
                                nombre_t)
                ex = tareas_db.get(tfid) or tareas_db.get("n:" + normalizar(nombre_t))
                pj.tareas.append(TareaPlanJ(
                    fid=tfid, plan_fid=pfid, nombre=nombre_t, campos=campos, tipo_nombre=_txt(t.get("tipo")),
                    checklist=campos_cl, existente=ex,
                ))
            self.plan.planes[pfid] = pj
        self.plan.conteo["activadores"] = dict(tipos_activador)

    # --- activos ------------------------------------------------------------
    def activos(self):
        locs = self.locs
        assets_json = {_fid(a.get("id")): a for a in self.d["activos"]}

        def nodo_de(a):
            """Ubicacion (fid) mas cercana hacia arriba; los activos pueden colgar de otros activos."""
            p = _fid(a.get("id_parent"))
            visto = set()
            while p and p not in visto:
                visto.add(p)
                if p in locs:
                    return p
                if p in assets_json:
                    p = _fid(assets_json[p].get("id_parent"))
                else:
                    return None
            return None

        vistos = set()
        for fid, a in assets_json.items():
            if not fid:
                continue
            if fid in vistos:
                continue
            vistos.add(fid)
            nombre = _txt(a.get("nombre"), 255) or _txt(a.get("descripcion"), 255) or f"Activo {fid}"
            loc = nodo_de(a)
            if loc is None or loc not in self.hospital_de_nodo:
                # Sin ubicacion conocida: cuelga de la primera sede.
                hosp = next(iter(self.plan.hospitales), None)
                self.av.add("activo_sin_ubicacion", "Activos sin ubicación conocida; quedan en la sede, sin ubicación.",
                            nombre)
                nodo_fid = ""
            else:
                hosp = self.hospital_de_nodo[loc]
                nodo_fid = "" if loc in self.plan.hospitales else loc
            if hosp is None:
                continue

            campos = {"name": nombre}
            for campo, origen, largo in (
                ("manufacturer", "fabricante", 200),
                ("model", "modelo", 200),
                ("serial_number", "serie", 200),
                ("equipment_location", "ubicacion_equipo", 255),
                ("barcode", "barcode", 100),
                ("classification_1", "clasificacion_1", 100),
                ("classification_2", "clasificacion_2", 100),
            ):
                v = _txt(a.get(origen))
                if len(v) > largo:
                    self.av.add("recortado", "Textos de activos recortados al largo máximo.", origen)
                    v = v[:largo]
                campos[campo] = v
            campos["priority"] = PRIORIDADES.get(str(a.get("prioridad")), "MEDIUM")
            if a.get("habilitado") is False:
                campos["status"] = Asset.Status.DECOMMISSIONED
            elif a.get("disponible") is False:
                campos["status"] = Asset.Status.OUT_OF_SERVICE
            else:
                campos["status"] = Asset.Status.ACTIVE
            if a.get("centro_costo"):
                self.av.add("centro_costo", "Activos con centro de costo; TodoGas no tiene dónde guardarlo y se omite.")
            if _txt(a.get("notas")):
                campos["notes"] = _txt(a.get("notas"))

            hp = self.plan.hospitales[hosp]
            existente = self.activos_por_fid.get(fid)
            codigo = _txt(a.get("code"), 100)
            if existente is None and codigo and hp.existente is not None:
                cand = self.activos_por_codigo.get(codigo.lower())
                if cand is not None and cand.hospital_id == hp.existente.id:
                    existente = cand
                    self.av.add("emparejado_por_codigo",
                                "Activos que ya existían (Excel o a mano) y se emparejaron por código.", codigo)
            if existente is not None:
                if hp.existente is not None and existente.hospital_id != hp.existente.id:
                    self.plan.errores_lista.append(f"El activo «{nombre}» (id {fid}) ya existe en otro hospital.")
                    continue
                campos["code"] = existente.code
            else:
                if codigo and len(codigo) <= 50 and codigo.lower() not in self.codigos_activo:
                    self.codigos_activo.add(codigo.lower())
                    campos["code"] = codigo
                else:
                    campos["code"] = _unico("FRC-" + fid, self.codigos_activo, 50)
                    self.av.add("codigo_generado",
                                "Activos sin código usable (vacío, largo o repetido); se generó uno FRC-<id>.",
                                codigo or nombre)
            self.plan.activos[fid] = ActivoJ(
                fid=fid, hospital_fid=hosp, nodo_fid=nodo_fid, campos=campos,
                plan_fid=_fid(a.get("id_plan")), existente=existente,
                proximas=self.proximas.get(fid, {}),
            )
            if a.get("id_plan") and _fid(a.get("id_plan")) not in self.plan.planes:
                self.av.add("activo_plan_ausente", "Activos con un protocolo que no viene en el archivo.", nombre)

    # --- historial ----------------------------------------------------------
    def historial(self):
        c = self.plan.conteo
        existentes = set(
            WorkOrder.objects.exclude(fracttal_id="").values_list("fracttal_id", flat=True)
        )
        tareas_plan = {t.fid: t for p in self.plan.planes.values() for t in p.tareas}
        subtareas_plan = {t.fid: {x.fid: x.tipo for x in t.checklist} for t in tareas_plan.values()}
        plan_de_tarea = {t.fid: t.plan_fid for t in tareas_plan.values()}
        adhoc = defaultdict(dict)  # id tarea -> {subtarea fid: subtarea}
        adhoc_desc = {}
        vistas = set()
        c.update(ot_finalizadas=0, ot_canceladas=0, tareas_ot=0, respuestas=0, firmas=0, fotos=0)
        for o in self.d["ots"]:
            ofid = _fid(o.get("id"))
            if not ofid or ofid in vistas:
                if ofid:
                    self.plan.errores_lista.append(f"La OT {ofid} está repetida en el archivo.")
                continue
            vistas.add(ofid)
            if o.get("estado") not in (3, 4):
                self.av.add("ot_estado", "OT con un estado que no es finalizada ni cancelada; se salta.", ofid)
                continue
            existe = ofid in existentes
            tareas_validas = []
            for t in o.get("tareas", []):
                if _fid(t.get("id_activo")) not in self.plan.activos and not self._activo_en_db(t.get("id_activo")):
                    self.av.add("ot_tarea_sin_activo", "Tareas de OT cuyo activo no está; se saltan.", ofid)
                    continue
                tareas_validas.append(t)
            if not tareas_validas:
                self.av.add("ot_sin_tareas", "OT sin tareas importables; se salta.", ofid)
                continue
            o = {**o, "tareas": tareas_validas}
            self.plan.ots.append(OtJ(datos=o, existe=existe))
            if existe:
                continue
            c["ot_finalizadas" if o["estado"] == 3 else "ot_canceladas"] += 1
            if any(t.get("firma") for t in tareas_validas):
                c["firmas"] += 1
            for t in tareas_validas:
                c["tareas_ot"] += 1
                idt = _fid(t.get("id_tarea"))
                if idt not in tareas_plan:
                    adhoc_desc.setdefault(idt, _txt(t.get("descripcion"), 200) or f"Tarea {idt}")
                    for s in t.get("subtareas", []):
                        adhoc[idt].setdefault(_fid(s.get("id_plan_subtarea")), s)
                    self.av.add("tarea_sin_protocolo",
                                "Tareas de OT que no están en ningún protocolo; se arma su checklist con lo respondido.",
                                adhoc_desc[idt])
                else:
                    esperadas = subtareas_plan[idt]
                    faltan = [s for s in t.get("subtareas", [])
                              if _fid(s.get("id_plan_subtarea")) not in esperadas]
                    distintas = [s for s in t.get("subtareas", [])
                                 if _fid(s.get("id_plan_subtarea")) in esperadas and s.get("valor") not in (None, "")
                                 and not _compatible(s.get("tipo"), esperadas[_fid(s.get("id_plan_subtarea"))])]
                    if faltan:
                        self.av.add("respuesta_fuera_de_protocolo",
                                    "Respuestas de subtareas que ya no están en el protocolo; se descartan.",
                                    _txt(t.get("descripcion"), 60))
                        c["descartadas"] = c.get("descartadas", 0) + len(faltan)
                    if distintas:
                        self.av.add("respuesta_tipo_distinto",
                                    "Respuestas cuyo tipo en la OT no coincide con el de la subtarea del protocolo "
                                    "actual (el protocolo cambió después); se descartan.",
                                    _txt(t.get("descripcion"), 60))
                        c["descartadas"] = c.get("descartadas", 0) + len(distintas)
                con_valor = [s for s in t.get("subtareas", []) if s.get("valor") not in (None, "")]
                if idt in tareas_plan:
                    esperadas = subtareas_plan[idt]
                    con_valor = [s for s in con_valor if _fid(s.get("id_plan_subtarea")) in esperadas
                                 and _compatible(s.get("tipo"), esperadas[_fid(s.get("id_plan_subtarea"))])]
                c["respuestas"] += len(con_valor)
                c["fotos"] += len(t.get("archivos") or [])
                if _fid(t.get("id_activo")) in self.plan.activos and plan_de_tarea.get(idt):
                    act = self.plan.activos[_fid(t.get("id_activo"))]
                    if act.plan_fid != plan_de_tarea[idt]:
                        self.av.add("tarea_de_otro_protocolo",
                                    "Tareas de OT hechas con un protocolo distinto al que tiene hoy el activo.",
                                    _txt(t.get("descripcion"), 60))
        # Checklists de las tareas sin protocolo.
        for idt, subs in adhoc.items():
            campos_cl = []
            for s in sorted(subs.values(), key=lambda x: x.get("orden") or 0):
                s2 = {**s, "id": s.get("id_plan_subtarea"), "requerida": False}
                cj = _convertir_campo(s2, self.con_saltos)
                if cj is not None:
                    campos_cl.append(cj)
            nombre = f"Fracttal tarea {idt} — {adhoc_desc[idt]}"[:255]
            self.plan.adhoc[idt] = TareaPlanJ(
                fid=idt, plan_fid="", nombre=nombre, campos={}, tipo_nombre="", checklist=campos_cl,
            )

    def _activo_en_db(self, fid):
        return _fid(fid) in self.activos_por_fid

    def cerrar(self):
        return self.plan


def planificar(datos):
    """Arma el plan de importacion. Solo lee la base de datos."""
    p = _Planificador(datos)
    p.ubicaciones()
    if p.plan.errores:
        return p.plan
    p.protocolos()
    p.activos()
    p.historial()
    return p.cerrar()


# --------------------------------------------------------------------------
# Aplicar
# --------------------------------------------------------------------------


def _rellenar(obj, campos, vacios=("", None)):
    """Copia solo los datos que Fracttal trae: un vacio no borra lo ya completado."""
    cambio = False
    for campo, valor in campos.items():
        if valor in vacios:
            continue
        if getattr(obj, campo) != valor:
            setattr(obj, campo, valor)
            cambio = True
    return cambio


def _firma_de_campos(campos):
    return [c.firma() for c in campos]


def _firma_de_version(version):
    return [
        (f.sort_order, f.label, f.field_type, f.group, f.is_required)
        for f in sorted(version.fields.all(), key=lambda x: x.sort_order)
    ]


def _crear_version(template, campos, user):
    """Publica una version nueva del template con `campos`. Devuelve (version, {fid: campo})."""
    ultimo = template.versions.aggregate(m=Max("version_number"))["m"] or 0
    template.versions.filter(is_current=True).update(is_current=False)
    version = ChecklistTemplateVersion.objects.create(
        template=template, version_number=ultimo + 1, published_by=user, is_current=True,
    )
    objetos = [
        ChecklistField(
            version=version, label=c.label, field_type=c.tipo, group=c.grupo,
            is_required=c.requerida, sort_order=c.orden, options_json=c.opciones,
        )
        for c in campos
    ]
    ChecklistField.objects.bulk_create(objetos, batch_size=LOTE)
    return version, {c.fid: o for c, o in zip(campos, objetos)}


def _mapear(version, campos):
    """{fid de subtarea: campo de la version}: por orden y texto."""
    por_orden = {f.sort_order: f for f in version.fields.all()}
    mapa = {}
    for c in campos:
        f = por_orden.get(c.orden)
        if f is not None and f.label == c.label:
            mapa[c.fid] = f
    return mapa


def _nombre_unico_template(base, usados):
    return _unico(base, usados, 255)


def _valor(campo_tipo, tipo_fracttal, valor):
    """Respuesta de Fracttal -> (valor, direccion, hora, problema|None)."""
    if valor is None or valor == "":
        return None
    v = str(valor)
    if campo_tipo == FT.BOOLEAN:
        low = v.strip().lower()
        if low == "true":
            return ("true", "", None, None)
        if low == "false":
            return ("false", "", None, None)
        if low in ("n/a", "na"):
            return ("na", "", None, None)
        return (v, "", None, "booleano")
    if campo_tipo == FT.PASS_ALERT_FAIL:
        r = VERIFICACION.get(v.strip())
        if r:
            return (r, "", None, None)
        if v.strip().lower() in ("n/a", "na"):
            return ("NA", "", None, None)
        return (v, "", None, "verificacion")
    if campo_tipo == FT.NUMBER:
        try:
            float(v.replace(",", "."))
            return (v.strip().replace(",", "."), "", None, None)
        except ValueError:
            return (v, "", None, "numero")
    if campo_tipo == FT.GPS:
        try:
            g = json.loads(v)
            lat, lon = float(g["latitude"]), float(g["longitude"])
        except (ValueError, KeyError, TypeError):
            return (v, "", None, "gps")
        hora = None
        m = _RE_HORA_GEO.match(str(g.get("hour") or ""))
        if m:
            d, mes, a, h, mi, s = (int(x) for x in m.groups())
            try:
                hora = timezone.make_aware(datetime(a, mes, d, h, mi, s))
            except ValueError:
                hora = None
        return (f"{lat},{lon}", _txt(g.get("address"), 300), hora, None)
    if campo_tipo == FT.DATETIME:
        d = _dt(v)
        if d is None:
            return (v, "", None, "fecha")
        return (d.isoformat(), "", None, None)
    return (v, "", None, None)


def _decodificar_firma(texto):
    if not texto:
        return None
    base64_ = str(texto).split(",", 1)[-1]
    try:
        datos = base64.b64decode(base64_, validate=False)
    except ValueError:
        return None
    return datos if datos[:4] == b"\x89PNG" else None


def aplicar(plan, user):
    """Escribe el plan en una sola transaccion. Devuelve los conteos aplicados."""
    if plan.errores:
        raise ImportacionError("El plan tiene errores; no se puede aplicar.")
    k = Counter()
    problemas = Counter()
    try:
        with transaction.atomic():
            hospitales = _aplicar_hospitales(plan, k)
            nodos = _aplicar_nodos(plan, hospitales, k)
            activos = _aplicar_activos(plan, hospitales, nodos, k)
            planes, tareas_plan, mapas = _aplicar_protocolos(plan, user, k)
            _aplicar_planes_a_activos(plan, activos, planes, user, k, solo_sin_plan=True)
            _aplicar_historial(plan, user, activos, tareas_plan, mapas, k, problemas)
            _aplicar_planes_a_activos(plan, activos, planes, user, k, solo_sin_plan=False)
    except IntegrityError as exc:
        raise ImportacionError(f"La base de datos rechazó la importación: {exc}") from exc
    conteos = dict(k)
    if problemas:
        conteos["valores_con_problemas"] = dict(problemas)
    return conteos


def _aplicar_hospitales(plan, k):
    hospitales = {}
    for fid, hp in plan.hospitales.items():
        if hp.existente is not None:
            h = Hospital.objects.get(pk=hp.existente.pk)
            cambio = _rellenar(h, {c: v for c, v in hp.campos.items() if c not in ("is_active",)})
            if h.fracttal_id != fid and not Hospital.objects.filter(fracttal_id=fid).exclude(pk=h.pk).exists():
                h.fracttal_id = fid
                cambio = True
            if cambio:
                h.save()
                k["hospitals_updated"] += 1
        else:
            h = Hospital.objects.create(name=hp.nombre, code=hp.codigo, fracttal_id=fid, **hp.campos)
            k["hospitals_created"] += 1
        hospitales[fid] = h
    return hospitales


def _aplicar_nodos(plan, hospitales, k):
    nodos = {}
    for n in sorted(plan.nodos.values(), key=lambda x: x.profundidad):
        padre = nodos.get(n.padre_fid) if n.padre_fid else None
        if n.existente is not None:
            obj = AssetNode.objects.get(pk=n.existente.pk)
            _rellenar(obj, n.campos)
            obj.fracttal_id = n.fid
            obj.is_active = n.activo
            obj.save()
            k["locations_updated"] += 1
        else:
            obj = AssetNode(
                hospital=hospitales[n.hospital_fid], parent=padre, name=n.nombre,
                is_active=n.activo, fracttal_id=n.fid, **n.campos,
            )
            obj.save()
            k["locations_created"] += 1
        nodos[n.fid] = obj
    return nodos


def _aplicar_activos(plan, hospitales, nodos, k):
    activos = {}
    nuevos, a_actualizar = [], []
    for a in plan.activos.values():
        hospital = hospitales[a.hospital_fid]
        nodo = nodos.get(a.nodo_fid) if a.nodo_fid else None
        if a.existente is not None:
            obj = Asset.objects.get(pk=a.existente.pk)
            _rellenar(obj, {c: v for c, v in a.campos.items() if c != "code"})
            obj.hospital, obj.node, obj.fracttal_id = hospital, nodo, a.fid
            obj.updated_at = timezone.now()
            a_actualizar.append(obj)
        else:
            obj = Asset(hospital=hospital, node=nodo, fracttal_id=a.fid, **a.campos)
            nuevos.append(obj)
        activos[a.fid] = obj
    Asset.objects.bulk_create(nuevos, batch_size=LOTE)
    if a_actualizar:
        Asset.objects.bulk_update(
            a_actualizar,
            ["name", "manufacturer", "model", "serial_number", "equipment_location", "barcode", "priority",
             "classification_1", "classification_2", "status", "notes", "hospital", "node", "fracttal_id",
             "updated_at"],
            batch_size=LOTE,
        )
    k["assets_created"] = len(nuevos)
    k["assets_updated"] = len(a_actualizar)
    return activos


def _aplicar_protocolos(plan, user, k):
    """Protocolos, tareas del plan y checklist. Devuelve (planes, tareas_plan, mapas)."""
    planes = {}
    tareas_plan = {}  # fid de tarea -> PlanTask
    mapas = {}  # fid de tarea -> {fid de subtarea: ChecklistField}
    nombres_template = {n.lower() for n in ChecklistTemplate.objects.values_list("name", flat=True)}
    for pj in plan.planes.values():
        if pj.existente is not None:
            obj = MaintenancePlan.objects.get(pk=pj.existente.pk)
            if obj.fracttal_plan_id != pj.fid:
                obj.fracttal_plan_id = pj.fid
                obj.save(update_fields=["fracttal_plan_id", "updated_at"])
            k["plans_updated"] += 1
        else:
            obj = MaintenancePlan.objects.create(
                name=pj.nombre, fracttal_plan_id=pj.fid,
                description="Importado del JSON de Fracttal.",
            )
            k["plans_created"] += 1
        planes[pj.fid] = obj
        for tj in pj.tareas:
            if tj.existente is not None:
                pt = PlanTask.objects.get(pk=tj.existente.pk)
                if pt.fracttal_task_id != tj.fid:
                    pt.fracttal_task_id = tj.fid
                    pt.save(update_fields=["fracttal_task_id", "updated_at"])
                k["plan_tasks_updated"] += 1
            else:
                pt = PlanTask.objects.create(plan=obj, **tj.campos)
                k["plan_tasks_created"] += 1
            version = _checklist_de_tarea(pt, tj, tj.nombre, f"{pj.nombre} — {tj.nombre}", nombres_template, user, k)
            tareas_plan[tj.fid] = pt
            if version is not None:
                mapas[tj.fid] = (version, _mapear(version, tj.checklist))
    for idt, tj in plan.adhoc.items():
        existente = ChecklistTemplate.objects.filter(name=tj.nombre).first()
        if existente is not None:
            version = existente.versions.filter(is_current=True).first()
        else:
            tpl = ChecklistTemplate.objects.create(
                name=tj.nombre, description="Armado con las respuestas de una OT de Fracttal sin protocolo.",
            )
            version, _ = _crear_version(tpl, tj.checklist, user)
            nombres_template.add(tj.nombre.lower())
            k["checklists_created"] += 1
        mapas[idt] = (version, _mapear(version, tj.checklist))
    return planes, tareas_plan, mapas


def _checklist_de_tarea(pt, tj, _nombre, nombre_template, usados, user, k):
    """Deja la tarea del plan con su checklist al dia. Devuelve la version vigente (o None)."""
    if not tj.checklist:
        return None
    template = pt.checklist_template
    if template is None:
        template = ChecklistTemplate.objects.create(
            name=_nombre_unico_template(nombre_template, usados),
            description="Importado del JSON de Fracttal.",
        )
        pt.checklist_template = template
        pt.save(update_fields=["checklist_template", "updated_at"])
    version = template.versions.filter(is_current=True).first()
    if version is not None and _firma_de_version(version) == _firma_de_campos(tj.checklist):
        return version
    version, _ = _crear_version(template, tj.checklist, user)
    k["checklist_versions_created"] += 1
    return version


def _aplicar_planes_a_activos(plan, activos, planes, user, k, solo_sin_plan):
    """Asigna el protocolo de Fracttal a cada activo y abre sus tareas pendientes.

    Primera pasada (`solo_sin_plan`): los activos sin protocolo reciben el suyo
    SIN abrir pendientes, para que el historial los vea. Segunda pasada: tras
    escribir el historial, un activo que cambia de protocolo pasa por
    `set_asset_plan` (anula las pendientes viejas y hereda la fecha) y a cada
    uno se le abre la pendiente que falte, con la fecha "proxima" de Fracttal.
    """
    if solo_sin_plan:
        for a in plan.activos.values():
            obj = activos[a.fid]
            destino = planes.get(a.plan_fid)
            if destino is not None and obj.plan_id is None:
                obj.plan = destino
                Asset.objects.filter(pk=obj.pk).update(plan=destino)
        return
    abiertas = set(
        Task.objects.filter(status__in=Task.OPEN_STATUSES).values_list("plan_task_id", "asset_id")
    )
    for a in plan.activos.values():
        destino = planes.get(a.plan_fid)
        if destino is None:
            continue
        obj = activos[a.fid]
        if obj.plan_id != destino.id:
            set_asset_plan(obj, destino, created_by=user)
            k["plans_changed"] += 1
        else:
            k["plans_assigned"] += 1
        for pt in destino.tasks.select_related("plan").filter(is_active=True, trigger=PlanTask.Trigger.DATE):
            if (pt.id, obj.id) in abiertas:
                continue
            fecha = a.proximas.get(pt.fracttal_task_id)
            tarea, creada = ensure_open_task(pt, obj, fecha=fecha, created_by=user)
            if creada:
                k["pending_tasks_created"] += 1
                abiertas.add((pt.id, obj.id))


def _aplicar_historial(plan, user, activos, tareas_plan, mapas, k, problemas):
    ots = [o for o in plan.ots if not o.existe]
    if not ots:
        return
    siguiente = (WorkOrder.objects.aggregate(m=Max("wo_number"))["m"] or 0) + 1
    catalogo = {normalizar(t.name): t.code for t in TaskTypeCatalog.objects.filter(is_active=True)}
    activos_db = {a.fracttal_id: a for a in Asset.objects.exclude(fracttal_id="")}
    activos_db.update(activos)

    for inicio in range(0, len(ots), LOTE_OT):
        lote = ots[inicio:inicio + LOTE_OT]
        wos, tareas, historias, respuestas, campos_resp, firmas = [], [], [], [], [], []
        creadas_en = []
        for oj in lote:
            o = oj.datos
            ts = o["tareas"]
            primero = ts[0]
            activo0 = activos_db[_fid(primero.get("id_activo"))]
            inicios = [d for d in (_dt(t.get("inicio")) for t in ts) if d]
            fines = [d for d in (_dt(t.get("fin")) for t in ts) if d]
            creada = _dt(o.get("creada"))
            iniciada = min(inicios) if inicios else creada
            terminada = max(fines) if fines else (iniciada or creada)
            programadas = [d for d in (_dt(t.get("programada")) for t in ts) if d]
            fecha_prog = _fecha_local(min(programadas)) if programadas else _fecha_local(creada or terminada)
            if fecha_prog is None:
                fecha_prog = timezone.localdate()
            estado_ok = o["estado"] == 3
            reales = [t.get("duracion_real_min") for t in ts if isinstance(t.get("duracion_real_min"), (int, float))]
            if reales:
                real = timedelta(minutes=sum(reales))
            elif iniciada and terminada:
                real = terminada - iniciada
            else:
                real = None
            paro = sum((t.get("paro_seg") or 0) for t in ts if isinstance(t.get("paro_seg"), (int, float)))
            estimada = sum(((t.get("duracion_seg") or 0) for t in ts if isinstance(t.get("duracion_seg"), (int, float))), 0)
            cal = o.get("calificacion")
            rating = cal if isinstance(cal, int) and 1 <= cal <= 5 else None
            notas = []
            if _txt(o.get("nota")):
                notas.append(_txt(o["nota"]))
            for t in ts:
                for n in (t.get("nota"), t.get("nota_tarea")):
                    if _txt(n) and _txt(n) not in notas:
                        notas.append(_txt(n))
            tecnicos = []
            for t in ts:
                n = _txt(t.get("tecnico"))
                if n and n not in tecnicos:
                    tecnicos.append(n)
            ejecutor = _txt(o.get("responsable")) or (tecnicos[0] if tecnicos else "")
            folio = _fid(o.get("folio"))
            primera_tarea_tipo = _tipo_de_ot(primero, tareas_plan, catalogo)
            titulo = f"[Fracttal {folio}] {_txt(primero.get('descripcion'))}"[:500] if folio else \
                _txt(primero.get("descripcion"), 500)
            if len(ts) > 1:
                titulo = f"[Fracttal {folio}] {len(ts)} tareas"[:500]
            datos_f = {
                "creada": o.get("creada"),
                "creada_por": _txt(o.get("creada_por")),
                "responsable": _txt(o.get("responsable")),
                "clasificaciones": o.get("clasificaciones"),
                "calificacion": o.get("calificacion"),
                "tareas": [],
            }
            wo = WorkOrder(
                id=uuid.uuid4(), wo_number=siguiente,
                wo_year=(timezone.localtime(creada).year if creada else None),
                hospital=activo0.hospital, task_type=primera_tarea_tipo, title=titulo,
                description="", status=WorkOrder.Status.COMPLETED if estado_ok else WorkOrder.Status.CANCELLED,
                priority=PRIORIDADES.get(str(primero.get("prioridad")), "MEDIUM"),
                progress=100 if estado_ok else 0,
                created_by=user, scheduled_date=fecha_prog,
                started_at=iniciada if estado_ok else None, completed_at=terminada if estado_ok else None,
                estimated_duration=timedelta(seconds=estimada) if estimada else None,
                actual_duration=real if estado_ok else None,
                downtime=timedelta(seconds=paro) if paro else None,
                rating=rating, notes="\n".join(notas),
                origin=WorkOrder.Origin.FRACTTAL, fracttal_id=_fid(o.get("id")), fracttal_folio=folio,
                external_executor=ejecutor[:200],
            )
            siguiente += 1
            wos.append(wo)
            creadas_en.append((wo, creada))
            historias.append(WorkOrderStatusHistory(
                work_order=wo, from_status="", to_status=wo.status, changed_by=user,
                comment="OT histórica importada de Fracttal.", changed_at=terminada or creada or timezone.now(),
            ))
            firma_ot = None
            hashes = set()
            extras = []
            for orden, t in enumerate(ts):
                idt = _fid(t.get("id_tarea"))
                pt = tareas_plan.get(idt)
                version, mapa = mapas.get(idt, (None, {}))
                activo = activos_db[_fid(t.get("id_activo"))]
                fin = _dt(t.get("fin")) or terminada
                ini = _dt(t.get("inicio"))
                prog = _fecha_local(_dt(t.get("programada"))) or fecha_prog
                tarea = Task(
                    id=uuid.uuid4(), asset=activo, plan_task=pt, work_order=wo,
                    status=Task.Status.DONE if estado_ok else Task.Status.CANCELLED,
                    title=_txt(t.get("descripcion"), 500) or wo.title,
                    description="", task_type=pt.task_type if pt is not None else wo.task_type,
                    priority=PRIORIDADES.get(str(t.get("prioridad")), "MEDIUM"),
                    checklist_version=version,
                    calculated_date=prog, scheduled_date=prog,
                    estimated_duration=_segundos(t.get("duracion_seg")),
                    completed_at=fin if estado_ok else None,
                    cancellation_note="" if estado_ok else "OT cancelada en Fracttal.",
                    sort_order=orden, created_by=user,
                )
                tareas.append(tarea)
                if version is not None:
                    resp = ChecklistResponse(
                        id=uuid.uuid4(), task=tarea, version=version, started_at=ini, completed_at=fin if estado_ok else None,
                    )
                    respuestas.append(resp)
                    vistos = set()
                    for s in t.get("subtareas", []):
                        campo = mapa.get(_fid(s.get("id_plan_subtarea")))
                        if campo is None:
                            continue
                        if not _compatible(s.get("tipo"), campo.field_type):
                            continue
                        r = _valor(campo.field_type, s.get("tipo"), s.get("valor"))
                        if r is None or campo.id in vistos:
                            continue
                        vistos.add(campo.id)
                        valor, direccion, hora, problema = r
                        if problema:
                            problemas[f"{campo.field_type}:{problema}"] += 1
                        campos_resp.append(ChecklistFieldResponse(
                            response=resp, field=campo, value=valor, repetition=0,
                            answered_at=hora or fin or timezone.now(), geo_address=direccion,
                        ))
                datos_f["tareas"].append({
                    "id": t.get("id"), "id_tarea": t.get("id_tarea"), "activo": _txt(t.get("activo")),
                    "tecnico": _txt(t.get("tecnico")), "inicio": t.get("inicio"), "fin": t.get("fin"),
                    "duracion_real_min": t.get("duracion_real_min"), "paro_seg": t.get("paro_seg"),
                    "calificacion": t.get("calificacion"), "nota": t.get("nota"), "nota_tarea": t.get("nota_tarea"),
                    "tipo": t.get("tipo"), "tipo_principal": t.get("tipo_principal"), "activador": t.get("activador"),
                    "archivos": t.get("archivos") or [],
                })
                k["photos_pending"] += len(t.get("archivos") or [])
                png = _decodificar_firma(t.get("firma"))
                if png is not None:
                    h = hashlib.sha256(png).hexdigest()
                    if h not in hashes:
                        hashes.add(h)
                        if firma_ot is None:
                            firma_ot = (png, h, _txt(t.get("tecnico")) or ejecutor or "Técnico (Fracttal)", fin)
                        else:
                            extras.append(png)
                elif t.get("firma"):
                    k["signatures_unreadable"] += 1
            if firma_ot is not None:
                png, h, nombre, fecha = firma_ot
                ruta = default_storage.save(
                    f"evidence/signatures/{wo.id}/TECHNICIAN_{uuid.uuid4().hex}.png", ContentFile(png)
                )
                firmas.append(Signature(
                    work_order=wo, signature_type=Signature.SignatureType.TECHNICIAN, file_url=ruta,
                    signer_name=nombre[:200], signer_role="Técnico (Fracttal)", file_hash=h,
                    signed_at=fecha or timezone.now(),
                ))
                k["signatures_saved"] += 1
            if extras:
                rutas = []
                for png in extras:
                    rutas.append(default_storage.save(
                        f"evidence/signatures/{wo.id}/fracttal_extra_{uuid.uuid4().hex}.png", ContentFile(png)
                    ))
                datos_f["firmas_extra"] = rutas
                k["signatures_extra_saved"] += len(rutas)
            datos_f["fotos_pendientes"] = sum(len(t.get("archivos") or []) for t in ts)
            wo.fracttal_data = datos_f

        WorkOrder.objects.bulk_create(wos, batch_size=LOTE)
        # created_at es auto_now_add: se reescribe con la fecha real de Fracttal.
        reales = []
        for wo, creada in creadas_en:
            if creada is not None:
                wo.created_at = creada
                reales.append(wo)
        if reales:
            WorkOrder.objects.bulk_update(reales, ["created_at"], batch_size=LOTE)
        WorkOrderStatusHistory.objects.bulk_create(historias, batch_size=LOTE)
        Task.objects.bulk_create(tareas, batch_size=LOTE)
        ChecklistResponse.objects.bulk_create(respuestas, batch_size=LOTE)
        ChecklistFieldResponse.objects.bulk_create(campos_resp, batch_size=LOTE)
        Signature.objects.bulk_create(firmas, batch_size=LOTE)
        k["work_orders_created"] += len(wos)
        k["work_order_tasks_created"] += len(tareas)
        k["responses_created"] += len(campos_resp)


def _tipo_de_ot(tarea_json, tareas_plan, catalogo):
    """Codigo de tipo de la OT: el de la tarea del protocolo; si no, el de Fracttal por su tipo."""
    pt = tareas_plan.get(_fid(tarea_json.get("id_tarea")))
    if pt is not None:
        return pt.task_type
    codigo = catalogo.get(normalizar(tarea_json.get("tipo")))
    if codigo:
        return codigo
    principal = normalizar(tarea_json.get("tipo_principal"))
    return "CORRECTIVE" if principal.startswith("correctiv") else "PREVENTIVE"


# --------------------------------------------------------------------------
# Auditoria
# --------------------------------------------------------------------------


def auditar(user, archivo, resumen, conteos, ip=None, user_agent=""):
    """Deja constancia de la importacion (quien, que archivo, cuantos)."""
    from apps.audit.models import AuditLog

    AuditLog.objects.create(
        user=user,
        action=AuditLog.Action.CREATE,
        entity_type="FracttalJsonImport",
        entity_id=uuid.UUID(int=0),
        changes={
            "archivo": archivo,
            "formato": FORMATO,
            "sede": resumen.get("sede"),
            "hospitales_nuevos": len(resumen["hospitals"]["create"]),
            "ubicaciones": resumen["locations"],
            "activos": resumen["assets"],
            "protocolos": resumen["plans"],
            "ot": resumen["work_orders"],
            "avisos": resumen["warnings_count"],
            "aplicado": conteos,
        },
        ip_address=ip or None,
        user_agent=(user_agent or "")[:500],
    )
