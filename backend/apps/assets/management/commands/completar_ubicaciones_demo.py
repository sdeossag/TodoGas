"""Rellena direcciones y puntos del mapa en una base de demo YA creada.

    DB_NAME=todogas_demo python manage.py completar_ubicaciones_demo

El seed viejo dejaba los nodos sin direccion propia (o con la del hospital
copiada), asi que el mapa del detalle de la OT mostraba siempre el mismo punto.
Este comando pone una direccion y un punto propios a los nodos principales de
los dos hospitales demo, sin tocar nada mas: ni hospitales, ni equipos, ni OT.

- Idempotente: un campo solo se escribe si esta vacio o si es una copia exacta
  del dato del hospital. Lo que alguien ya escribio a mano no se pisa, y correrlo
  dos veces deja la base igual.
- Solo corre si el nombre de la base (DB_NAME) contiene "demo".
"""

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

MARCADOR = "demo"

# (codigo del hospital, codigo del nodo) -> (direccion, latitud, longitud).
# Los nodos que no estan aqui (Piso 3) heredan el punto del bloque: asi la
# demo muestra tambien el "heredado de Bloque A".
UBICACIONES = {
    # Clinica Demo Norte: Cra 15 # 100-12, Bogota (zona Chico).
    ("DEMO-NORTE", "N-BA"): ("Cra 15 # 100-12, Bloque A, Bogotá", "4.6781200", "-74.0479500"),
    ("DEMO-NORTE", "N-P1"): ("Cra 15 # 100-12, Urgencias (acceso por la Cl 99), Bogotá", "4.6779000", "-74.0483500"),
    ("DEMO-NORTE", "N-SOT"): ("Cra 15 # 100-12, Sótano, Central de gases (rampa de la Cl 100), Bogotá", "4.6774500", "-74.0477500"),
    # Hospital Demo Sur: Cl 10 Sur # 50-30, Medellin (Guayabal).
    ("DEMO-SUR", "S-BA"): ("Cl 10 Sur # 50-30, Bloque A, Medellín", "6.2001200", "-75.5699500"),
    ("DEMO-SUR", "S-P1"): ("Cl 10 Sur # 50-30, Urgencias (acceso por la Cra 50), Medellín", "6.1999000", "-75.5703500"),
    ("DEMO-SUR", "S-SOT"): ("Cl 10 Sur # 50-30, Sótano, Central de gases (rampa trasera), Medellín", "6.1995500", "-75.5696000"),
}


def es_base_demo(marcador=MARCADOR):
    return marcador.lower() in str(connection.settings_dict["NAME"]).lower()


class Command(BaseCommand):
    help = "Completa direcciones y puntos de los nodos de la demo (solo en una base «demo»)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--marcador", default=MARCADOR,
            help="Palabra que debe llevar el nombre de la base (por defecto «demo»). "
                 "Existe para poder probar el comando en la base de pruebas.",
        )

    def handle(self, *args, **options):
        marcador = options["marcador"]
        if not es_base_demo(marcador):
            raise CommandError(
                f"La base «{connection.settings_dict['NAME']}» no parece una base de demo: "
                f"su nombre no contiene «{marcador}». No se hace nada. "
                "Ejemplo: DB_NAME=todogas_demo python manage.py completar_ubicaciones_demo"
            )

        from apps.assets.models import AssetNode

        cambiados = 0
        with transaction.atomic():
            for (cod_hospital, cod_nodo), (direccion, lat, lng) in UBICACIONES.items():
                nodo = (
                    AssetNode.objects.select_related("hospital")
                    .filter(hospital__code=cod_hospital, code=cod_nodo)
                    .first()
                )
                if nodo is None:
                    continue
                h = nodo.hospital
                campos = []
                # Vacio o copia exacta del hospital: no es una ubicacion propia.
                if not nodo.address or nodo.address == h.address:
                    nodo.address = direccion
                    campos.append("address")
                sin_punto = nodo.latitude is None or nodo.longitude is None
                copia = nodo.latitude == h.latitude and nodo.longitude == h.longitude
                if sin_punto or copia:
                    nodo.latitude, nodo.longitude = Decimal(lat), Decimal(lng)
                    campos += ["latitude", "longitude"]
                if campos:
                    # save() recalcula la ruta, que no cambia: el nombre es el mismo.
                    nodo.save(update_fields=campos + ["updated_at"])
                    cambiados += 1
        self.stdout.write(self.style.SUCCESS(f"Ubicaciones completadas: {cambiados} nodo(s) actualizados."))
