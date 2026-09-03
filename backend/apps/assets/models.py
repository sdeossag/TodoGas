import uuid

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
