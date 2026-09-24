import uuid
from collections import defaultdict

from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models
from django.db.models.functions import Upper


class Hospital(models.Model):
    """
    Cliente / Hospital. Entidad de primer nivel.
    En Fracttal: nodos de tipo Ubicación nivel 1 del árbol.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    nit = models.CharField(max_length=20, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    department = models.CharField(max_length=100, blank=True, default="")
    contact_name = models.CharField(max_length=200, blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets_hospital"
        ordering = ["name"]
        indexes = [
            # RF-AC-05 pide que la busqueda de activos alcance tambien el
            # nombre del hospital, que se resuelve por join contra esta tabla.
            GinIndex(
                OpClass(Upper("name"), name="gin_trgm_ops"),
                name="idx_hospital_name_trgm",
            ),
        ]

    def __str__(self):
        return self.name


class AssetNode(models.Model):
    """
    Nodo de la jerarquía interna del hospital (pisos, áreas, servicios).
    Autorreferencial. Fracttal: nodos Ubicación en niveles 2+.
    """

    class NodeType(models.TextChoices):
        AREA = "AREA", "Área / Servicio"
        FLOOR = "FLOOR", "Piso"
        BUILDING = "BUILDING", "Edificio/Torre"
        ROOM = "ROOM", "Habitación/Sala"
        OTHER = "OTHER", "Otro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(
        Hospital, on_delete=models.PROTECT,
        related_name="asset_nodes"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="children",
        help_text="Nodo padre. NULL = nodo raíz directo del hospital"
    )
    name = models.CharField(max_length=255)
    node_type = models.CharField(max_length=10, choices=NodeType.choices, default=NodeType.AREA)
    code = models.CharField(max_length=50, blank=True, default="")
    path = models.CharField(
        max_length=1000, blank=True, default="",
        help_text="Ruta materializada auto-generada. No editar manualmente."
    )
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets_assetnode"
        ordering = ["hospital", "path"]
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "parent", "name"],
                name="uq_assetnode_hospital_parent_name"
            )
        ]

    def save(self, *args, **kwargs):
        if self.parent:
            self.path = f"{self.parent.path}/{self.name}".strip('/')
        else:
            self.path = self.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.hospital.code}/{self.path or self.name}"

    @classmethod
    def subtree_ids(cls, node_id):
        """
        Ids del nodo y de toda su sububicacion. Filtrar por "Piso 3" tiene que
        traer los activos de sus habitaciones. Se recorre por `parent` y no por
        `path`, que se arma con nombres y un nombre puede llevar una barra.
        """
        try:
            raiz = uuid.UUID(str(node_id))
        except ValueError:
            return []
        hospital_id = cls.objects.filter(pk=raiz).values_list("hospital_id", flat=True).first()
        if hospital_id is None:
            return []
        hijos = defaultdict(list)
        for nid, padre in cls.objects.filter(hospital_id=hospital_id).values_list("id", "parent_id"):
            hijos[padre].append(nid)
        ids, pendientes = [], [raiz]
        while pendientes:
            actual = pendientes.pop()
            ids.append(actual)
            pendientes.extend(hijos[actual])
        return ids


class Asset(models.Model):
    """
    Equipo específico con ficha técnica. Hoja del árbol.
    Fracttal: nodo tipo Equipo en nivel 3 del árbol de activos.
    """

    class Priority(models.TextChoices):
        HIGH = "HIGH", "Alta"
        MEDIUM = "MEDIUM", "Media"
        LOW = "LOW", "Baja"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        OUT_OF_SERVICE = "OUT_OF_SERVICE", "Fuera de servicio"
        DECOMMISSIONED = "DECOMMISSIONED", "Dado de baja"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(
        Hospital, on_delete=models.PROTECT,
        related_name="assets"
    )
    node = models.ForeignKey(
        AssetNode, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="assets"
    )
    # Un solo plan por activo, como el campo "Plan de Tareas" de la ficha en
    # Fracttal (decision D7). Las tareas del plan generan las pendientes del
    # activo; cambiar de plan se hace por apps.maintenance.services para que la
    # nueva pendiente herede la fecha de la anterior.
    plan = models.ForeignKey(
        "maintenance.MaintenancePlan", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="assets",
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    manufacturer = models.CharField(max_length=200, blank=True, default="")
    model = models.CharField(max_length=200, blank=True, default="")
    serial_number = models.CharField(max_length=200, blank=True, default="")
    equipment_location = models.CharField(max_length=255, blank=True, default="")
    barcode = models.CharField(max_length=100, blank=True, default="")
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    asset_type = models.CharField(max_length=100, blank=True, default="")
    classification_1 = models.CharField(max_length=100, blank=True, default="")
    classification_2 = models.CharField(max_length=100, blank=True, default="")
    supplier = models.CharField(max_length=200, blank=True, default="")
    purchase_date = models.DateField(null=True, blank=True)
    avg_daily_usage_hours = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True, default="")
    qr_code = models.CharField(max_length=255, blank=True, default="")
    photo_url = models.CharField(max_length=500, blank=True, default="")
    installation_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets_asset"
        ordering = ["hospital", "name"]
        indexes = [
            models.Index(fields=["hospital", "status"], name="idx_asset_hospital_status"),
            models.Index(fields=["serial_number"], name="idx_asset_serial"),
            # Busqueda por subcadena sobre ~3.940 activos (RF-AC-05, RNF-ESC-02).
            #
            # Van sobre Upper(campo), no sobre la columna cruda, porque Django
            # traduce `icontains` a UPPER(col::text) LIKE UPPER(%s): un indice
            # sobre la columna sin envolver se crearia pero el planificador no
            # lo usaria nunca.
            #
            # gin_trgm_ops y no full-text search: tsvector tokeniza por
            # palabras y no encontraria "1234" dentro de un numero de serie,
            # que es justo como se busca un equipo en campo.
            GinIndex(
                OpClass(Upper("name"), name="gin_trgm_ops"),
                name="idx_asset_name_trgm",
            ),
            GinIndex(
                OpClass(Upper("code"), name="gin_trgm_ops"),
                name="idx_asset_code_trgm",
            ),
            GinIndex(
                OpClass(Upper("serial_number"), name="gin_trgm_ops"),
                name="idx_asset_serial_trgm",
            ),
            GinIndex(
                OpClass(Upper("model"), name="gin_trgm_ops"),
                name="idx_asset_model_trgm",
            ),
            GinIndex(
                OpClass(Upper("manufacturer"), name="gin_trgm_ops"),
                name="idx_asset_manuf_trgm",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class AssetCustomField(models.Model):
    """
    Definición de un campo personalizado por tipo de activo (patrón EAV).
    Fracttal: tab Formulario Personalizado.
    """

    class FieldType(models.TextChoices):
        TEXT = "TEXT", "Texto"
        NUMBER = "NUMBER", "Número"
        DATE = "DATE", "Fecha"
        BOOLEAN = "BOOLEAN", "Sí/No"
        SELECT = "SELECT", "Selección"
        TEXTAREA = "TEXTAREA", "Texto largo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_type_name = models.CharField(max_length=100)
    field_name = models.CharField(max_length=200)
    field_type = models.CharField(max_length=10, choices=FieldType.choices)
    is_required = models.BooleanField(default=False)
    options = models.TextField(blank=True, default="")
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets_assetcustomfield"
        ordering = ["asset_type_name", "sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["asset_type_name", "field_name"],
                name="uq_customfield_type_name"
            )
        ]

    def __str__(self):
        return f"{self.asset_type_name}.{self.field_name}"


class AssetCustomFieldValue(models.Model):
    """Valor de un campo personalizado para un activo específico."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        Asset, on_delete=models.PROTECT,
        related_name="custom_field_values"
    )
    field = models.ForeignKey(
        AssetCustomField, on_delete=models.PROTECT,
        related_name="values"
    )
    value = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets_assetcustomfieldvalue"
        ordering = ["asset", "field"]
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "field"],
                name="uq_customfieldvalue_asset_field"
            )
        ]

    def __str__(self):
        return f"{self.asset.code}.{self.field.field_name} = {self.value[:50]}"


class Contract(models.Model):
    """
    Contrato de mantenimiento con un hospital o garantia de equipos.
    Fracttal: Configuracion -> Gestion Documental, con los grupos CONTRATO
    MANTENIMIENTO y GARANTIA EQUIPO (decision del 2026-09-23).

    El contrato cubre un hospital entero o una parte de su arbol (`node`); la
    garantia, una lista de equipos. Un contrato vencido no bloquea nada: el
    hospital queda marcado "sin contrato vigente" y el planificador decide.
    """

    class Kind(models.TextChoices):
        MAINTENANCE = "MAINTENANCE", "Contrato de mantenimiento"
        WARRANTY = "WARRANTY", "Garantía de equipos"

    class Notice(models.TextChoices):
        """Ultimo aviso de vencimiento enviado, para no repetirlo cada dia."""
        NONE = "", "Ninguno"
        DAYS_60 = "60", "60 días"
        DAYS_30 = "30", "30 días"
        EXPIRED = "EXPIRED", "Vencido"

    # Con cuantos dias de anticipacion se avisa y se marca "por vencer".
    EXPIRING_DAYS = 60

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    hospital = models.ForeignKey(
        Hospital, on_delete=models.PROTECT,
        related_name="contracts",
    )
    node = models.ForeignKey(
        AssetNode, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="contracts",
        help_text="Solo contratos: la parte del arbol que cubre. Vacio = todo el hospital.",
    )
    assets = models.ManyToManyField(
        Asset, through="ContractAsset", related_name="contracts", blank=True,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    # Clave en el almacenamiento (S3 o disco), como Photo.file_url.
    file_key = models.CharField(max_length=500, blank=True, default="")
    file_name = models.CharField(max_length=255, blank=True, default="")
    last_notice = models.CharField(
        max_length=8, choices=Notice.choices, blank=True, default=Notice.NONE,
    )
    created_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="contracts_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets_contract"
        ordering = ["-end_date", "name"]
        indexes = [
            models.Index(fields=["hospital", "kind", "end_date"], name="idx_contract_hosp_kind_end"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="ck_contract_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.start_date} → {self.end_date})"

    @staticmethod
    def active_q(on_date):
        return models.Q(start_date__lte=on_date, end_date__gte=on_date)

    def status_on(self, on_date):
        """UPCOMING, ACTIVE, EXPIRING (vigente y vence en 60 dias) o EXPIRED."""
        if self.end_date < on_date:
            return "EXPIRED"
        if self.start_date > on_date:
            return "UPCOMING"
        if (self.end_date - on_date).days <= self.EXPIRING_DAYS:
            return "EXPIRING"
        return "ACTIVE"


class ContractAsset(models.Model):
    """Equipo cubierto por una garantia."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT,
        related_name="asset_links",
    )
    asset = models.ForeignKey(
        Asset, on_delete=models.PROTECT,
        related_name="contract_links",
    )

    class Meta:
        db_table = "assets_contractasset"
        constraints = [
            models.UniqueConstraint(fields=["contract", "asset"], name="uq_contractasset"),
        ]


class MeterUnit(models.Model):
    """
    Unidad de medidor (Fracttal: Catalogos -> unidades de medidor). El cliente
    usa seis: AMPERIOS, HORAS, PRESION (inHg), PRESION (PSI), TEMPERATURA y
    VOLTAJE. `is_counter`: la lectura acumula (el horometro), y sobre ella se
    puede programar "cada N unidades"; las demas son lecturas puntuales.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20)
    is_counter = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assets_meterunit"
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "symbol"], name="uq_meterunit_name_symbol"),
        ]

    def __str__(self):
        return f"{self.name} ({self.symbol})"


class Meter(models.Model):
    """
    Medidor de un equipo: uno por unidad (la bomba de vacio tiene amperios,
    voltaje, horas, temperatura y presion). Se crea solo la primera vez que
    llega una lectura de esa unidad, o a mano desde la ficha.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="meters")
    unit = models.ForeignKey(MeterUnit, on_delete=models.PROTECT, related_name="meters")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assets_meter"
        ordering = ["asset", "unit__sort_order"]
        constraints = [
            models.UniqueConstraint(fields=["asset", "unit"], name="uq_meter_asset_unit"),
        ]

    def __str__(self):
        return f"{self.asset.code} · {self.unit}"


class MeterReading(models.Model):
    """
    Lectura de un medidor: del checklist de una tarea (una por respuesta, que
    se corrige con ella) o registrada a mano.

    `accumulated` solo en contadores: el uso total, que no se rompe cuando el
    horometro se reinicia o se cambia (en Fracttal un reinicio dejo la bomba
    con ultima lectura 582 H y maximo 12.901 H). Una lectura menor que la
    anterior, o marcada como reinicio, cuenta como un contador que arranco de
    cero.
    """

    class Source(models.TextChoices):
        CHECKLIST = "CHECKLIST", "Checklist"
        MANUAL = "MANUAL", "Registro manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meter = models.ForeignKey(Meter, on_delete=models.PROTECT, related_name="readings")
    value = models.DecimalField(max_digits=14, decimal_places=3)
    accumulated = models.DecimalField(max_digits=16, decimal_places=3, null=True, blank=True)
    read_at = models.DateTimeField()
    source = models.CharField(max_length=10, choices=Source.choices)
    field_response = models.OneToOneField(
        "checklists.ChecklistFieldResponse", on_delete=models.PROTECT,
        null=True, blank=True, related_name="meter_reading",
    )
    task = models.ForeignKey(
        "maintenance.Task", on_delete=models.PROTECT,
        null=True, blank=True, related_name="meter_readings",
    )
    is_reset = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True, default="")
    recorded_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        null=True, blank=True, related_name="meter_readings",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assets_meterreading"
        ordering = ["-read_at", "-created_at"]
        indexes = [
            models.Index(fields=["meter", "read_at"], name="idx_reading_meter_date"),
        ]

    def __str__(self):
        return f"{self.meter} = {self.value}"
