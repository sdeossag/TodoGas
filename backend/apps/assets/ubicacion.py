"""
Sububicacion efectiva de un equipo: su direccion y su punto en el mapa.

Cada nodo del arbol puede tener direccion y punto propios. Sin ellos, valen los
del primer nodo de arriba que los tenga y, al final, los del hospital. El
resultado dice de donde viene cada dato ("propio" o "heredado de Piso 1") para
que la pantalla lo cuente en lenguaje claro.

Direccion y punto se heredan por separado: un nodo con punto propio pero sin
direccion muestra la direccion de arriba, y al reves.

Se carga el arbol del hospital de una vez y se recorre en memoria: resolver 30
equipos cuesta la misma consulta que resolver uno.
"""

from apps.assets.models import AssetNode


def _tiene_punto(o):
    return o.latitude is not None and o.longitude is not None


def _origen(dueno, es_propio):
    if es_propio:
        return {"kind": "own", "name": dueno.name, "label": "propio"}
    return {"kind": "inherited", "name": dueno.name, "label": f"heredado de {dueno.name}"}


class ResolvedorUbicaciones:
    """Resuelve nodos de UN hospital. Se crea por serializacion, no se guarda."""

    def __init__(self, hospital):
        self.hospital = hospital
        self._nodos = None

    def _arbol(self):
        if self._nodos is None:
            self._nodos = {
                n.id: n
                for n in AssetNode.objects.filter(hospital_id=self.hospital.id).only(
                    "id", "name", "path", "parent_id", "address", "latitude", "longitude"
                )
            }
        return self._nodos

    def resolver(self, nodo_id):
        """El diccionario de la sububicacion efectiva, o None si no hay nodo."""
        if not nodo_id:
            return None
        arbol = self._arbol()
        nodo = arbol.get(nodo_id)
        if nodo is None:
            return None

        direccion, origen_dir, punto, origen_punto = "", None, None, None
        actual, visitados = nodo, set()
        while actual is not None and actual.id not in visitados:
            visitados.add(actual.id)
            propio = actual.id == nodo.id
            if origen_dir is None and (actual.address or "").strip():
                direccion, origen_dir = actual.address.strip(), _origen(actual, propio)
            if origen_punto is None and _tiene_punto(actual):
                punto, origen_punto = (actual.latitude, actual.longitude), _origen(actual, propio)
            actual = arbol.get(actual.parent_id) if actual.parent_id else None

        h = self.hospital
        if origen_dir is None and (h.address or "").strip():
            direccion, origen_dir = h.address.strip(), _origen(h, False)
        if origen_punto is None and _tiene_punto(h):
            punto, origen_punto = (h.latitude, h.longitude), _origen(h, False)

        return {
            "id": str(nodo.id),
            "name": nodo.name,
            "path": nodo.path,
            "address": direccion,
            "address_origin": origen_dir,
            "latitude": float(punto[0]) if punto else None,
            "longitude": float(punto[1]) if punto else None,
            "point_origin": origen_punto,
        }
