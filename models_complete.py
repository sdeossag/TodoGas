"""
===========================================================================
  CMMS TodoGas — Modelo de datos Django completo
  Basado en exploración de Fracttal One (v5.9.00, cuenta TODO GAS S.A.)
  Stack: Django + DRF + PostgreSQL
  Fecha de diseño: 2026-08-10
===========================================================================

DECISIONES DE DISEÑO (las 10 más importantes):

1. HOSPITAL SEPARADO DEL ÁRBOL DE ACTIVOS
   En Fracttal, los hospitales son nodos "Ubicación" en el mismo árbol que
   equipos y áreas. Esto dificulta la gestión de clientes y la asignación
   de OTs. En el nuevo sistema, Hospital es entidad de primer nivel con sus
   propios campos (NIT, contacto, contrato). AssetNode modela la jerarquía
   INTERNA de cada hospital (pisos, áreas, servicios). Asset es el equipo
   con ficha técnica.

2. OT = 1 ACTIVO (simplificación para offline)
   En Fracttal, una OT puede tener múltiples "Tareas" vinculadas a
   diferentes activos. Esto complica la serialización offline. En el nuevo
   sistema: 1 OT = 1 Asset. Si un plan genera trabajo para 15 activos,
   se crean 15 OTs. Cada técnico ve una lista plana de OTs en su móvil.

3. CHECKLIST VERSIONADO E INMUTABLE
   Fracttal embebe las subtareas dentro del plan sin versionamiento claro.
   Nosotros separamos: ChecklistTemplate → ChecklistTemplateVersion →
   ChecklistField. Las respuestas (ChecklistResponse) se vinculan a la
   VERSION, no al template. Si modificas un template, se crea nueva versión.
   Las OTs completadas quedan vinculadas a la versión exacta que se usó.
   Esto es obligatorio para INVIMA/GMP.

4. UUIDs + CÓDIGO LEGIBLE
   Todos los modelos usan UUID como PK (requisito). Pero Asset tiene
   `code` (legible, único) y WorkOrder tiene `wo_number` (auto-incremental
   legible) porque los técnicos en campo necesitan referirse a "la OT 19250",
   no a un UUID.

5. AUDIT LOG APPEND-ONLY
   Cualquier cambio en cualquier modelo se registra en AuditLog. El modelo
   usa `class Meta: managed = True` pero la app debe prohibir UPDATE/DELETE
   a nivel de código (override de save/delete en el modelo + permisos DRF).

6. ESTADOS DE OT CON HISTORIAL
   Los 4 estados de Fracttal (Pendiente, En Proceso, En Revisión, Finalizada)
   más Cancelada. Cada cambio de estado se registra en WorkOrderStatusHistory
   con timestamp, usuario, y comentario. Esto da trazabilidad completa.

7. CAMPOS PERSONALIZADOS (EAV PATTERN)
   Fracttal tiene "Formulario Personalizado" por activo con campos dinámicos.
   Implementamos esto con AssetCustomField (define el campo por tipo de
   activo) + AssetCustomFieldValue (valor por activo). Esto permite que
   "Columna de Soporte Vital" tenga campos diferentes a "Manifold de O2"
   sin cambiar el esquema.

8. PLAN DE MANTENIMIENTO CON TRIGGER TEMPORAL
   En Fracttal, los "Activadores" definen la frecuencia (cada N días/meses).
   Modelamos esto con campos de frecuencia en MaintenancePlan. Un job
   periódico (celery beat) evalúa los triggers y genera OTs automáticamente.

9. EVIDENCIA CON GPS Y HASH
   Fracttal almacena adjuntos genéricos. Nosotros tipamos la evidencia:
   Photo (con lat/lon del GPS del teléfono y timestamp EXIF) y Signature
   (firma digital con hash SHA-256 para no-repudio). Ambos son inmutables
   una vez creados.

10. PROTECT EN TODOS LOS FK
    Nunca CASCADE. Si intentas borrar un Hospital que tiene activos,
    Django lanza ProtectedError. Esto previene pérdida de datos históricos.
    Los "borrados" se hacen con soft-delete (campo is_active/habilitado).

===========================================================================
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


# =========================================================================
#  APP: users
# =========================================================================

class UserManager(BaseUserManager):
    """Manager personalizado que usa email como identificador único."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Usuario del sistema. Extiende AbstractBaseUser para usar email
    como login (no username). Mapea a Fracttal: Recursos Humanos +
    sistema de cuentas.

    Fracttal tiene: Nombres, Apellidos, Código (cédula), Email,
    Clasificación 1 (cargo), Habilitado, Cuenta (Sí/No).
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        SUP = "SUP", "Supervisor"
        TEC = "TEC", "Técnico"
        CLI = "CLI", "Cliente externo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150)  # Fracttal: Nombres
    last_name = models.CharField(max_length=150)   # Fracttal: Apellidos
    role = models.CharField(max_length=5, choices=Role.choices, default=Role.TEC)
    employee_code = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Cédula o código de empleado. Fracttal: Código"
    )
    phone = models.CharField(max_length=20, blank=True, default="")
    is_active = models.BooleanField(default=True)   # Fracttal: Habilitado
    is_staff = models.BooleanField(default=False)

    # Un técnico o cliente puede estar vinculado a un hospital
    hospital = models.ForeignKey(
        "Hospital", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="users",
        help_text="Hospital asignado (obligatorio para rol CLI, opcional para TEC)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users_user"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"


# =========================================================================
#  APP: assets
# =========================================================================

class Hospital(models.Model):
    """
    Cliente / Hospital. Entidad de primer nivel.

    En Fracttal: NO existe como entidad separada. Los hospitales son nodos
    de tipo "Ubicación" en el árbol de activos (nivel 1 del tree).
    En Terceros solo hay 5 registros y no representan los ~140 hospitales.

    Decisión: Separar Hospital como entidad propia con campos de negocio
    (NIT, contrato, contacto) que en Fracttal no existían o estaban en
    el nombre del nodo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        help_text="Fracttal: nombre del nodo Ubicación nivel 1. Ej: CLINICA VITHA"
    )
    code = models.CharField(
        max_length=50, unique=True,
        help_text="Código interno único. Ej: VITHA, HMUA"
    )
    nit = models.CharField(
        max_length=20, blank=True, default="",
        help_text="NIT del hospital. Fracttal: a veces en campo Código del nodo"
    )
    address = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    department = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Departamento colombiano"
    )
    contact_name = models.CharField(max_length=200, blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Fracttal: Habilitado"
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets_hospital"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AssetNode(models.Model):
    """
    Nodo de la jerarquía interna del hospital (pisos, áreas, servicios).
    Autorreferencial para permitir N niveles.

    Fracttal: Los nodos de tipo "Ubicación" en niveles 2+ del árbol.
    Ej: CLINICA VITHA → UCI ADULTOS, CUARTO DE GASES.
    La ruta se expresaba como: // CLINICA VITHA/ UCI ADULTOS/

    En el nuevo sistema el nivel 1 (hospital) es la entidad Hospital,
    y AssetNode modela del nivel 2 en adelante.
    """

    class NodeType(models.TextChoices):
        AREA = "AREA", "Área / Servicio"         # Ej: UCI ADULTOS
        FLOOR = "FLOOR", "Piso"                  # Ej: 2DO PISO
        BUILDING = "BUILDING", "Edificio/Torre"  # Ej: TORRE SUR
        ROOM = "ROOM", "Habitación/Sala"         # Ej: CUBICULO 21
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
    name = models.CharField(max_length=255)  # Fracttal: nombre del nodo
    node_type = models.CharField(
        max_length=10, choices=NodeType.choices, default=NodeType.AREA
    )
    code = models.CharField(
        max_length=50, blank=True, default="",
        help_text="Código del nodo. Fracttal: campo Código"
    )
    # Ruta materializada para queries eficientes y sync offline
    # Se regenera al mover nodos. Ej: "UCI ADULTOS/CUBICULO 21"
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

    def __str__(self):
        return f"{self.hospital.code}/{self.path or self.name}"


class Asset(models.Model):
    """
    Equipo específico con ficha técnica. Hoja del árbol.

    Fracttal: Nodo tipo "Equipo" en el árbol de activos (nivel 3).
    Campos mapeados directamente desde la ficha técnica observada.

    Ejemplo observado:
      Nombre: COLUMNA DE SOPORTE VITAL / CUBICULO 21
      Fabricante: /MARCA: BMI/
      Modelo: /BPE-1/BF1-X/
      Serial: /SN: 697581624231006031/
      Prioridad: Baja
      Clasificación 1: GARANTIA
      Clasificación 2: PENDANT
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
        related_name="assets",
        help_text="Hospital al que pertenece el equipo"
    )
    node = models.ForeignKey(
        AssetNode, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="assets",
        help_text="Nodo del árbol donde está ubicado. Fracttal: Ubicado en ó es Parte de"
    )
    name = models.CharField(
        max_length=255,
        help_text="Fracttal: Nombre"
    )
    code = models.CharField(
        max_length=50, unique=True,
        help_text="Código único del equipo. Fracttal: Código (a veces vacío, "
                  "necesita generarse en migración)"
    )
    # --- Ficha técnica (campos observados en Fracttal) ---
    manufacturer = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Fracttal: Fabricante. Ej: /MARCA: BMI/"
    )
    model = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Fracttal: Modelo. Ej: /BPE-1/BF1-X/"
    )
    serial_number = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Fracttal: Número de Serial"
    )
    equipment_location = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Fracttal: Ubicación de Equipo (texto libre adicional)"
    )
    barcode = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Fracttal: Código de Barras / NFC"
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM,
        help_text="Fracttal: Prioridad (Baja/Media/Alta)"
    )
    asset_type = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Fracttal: Tipo (dropdown configurable)"
    )
    classification_1 = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Fracttal: Clasificación 1. Ej: GARANTIA"
    )
    classification_2 = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Fracttal: Clasificación 2. Ej: PENDANT"
    )
    supplier = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Fracttal: Proveedor"
    )
    purchase_date = models.DateField(
        null=True, blank=True,
        help_text="Fracttal: Fecha de Compra"
    )
    avg_daily_usage_hours = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Fracttal: Horas de uso promedio diario. Ej: 24.00"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE,
        help_text="Fracttal: combinación de Habilitado + Fuera de servicio"
    )
    notes = models.TextField(
        blank=True, default="",
        help_text="Fracttal: Notas"
    )
    qr_code = models.CharField(
        max_length=255, blank=True, default="",
        help_text="URL del QR público del equipo"
    )
    photo_url = models.CharField(
        max_length=500, blank=True, default="",
        help_text="URL de la foto principal del activo (S3)"
    )
    # --- Campos no presentes en Fracttal, requeridos por el negocio ---
    installation_date = models.DateField(
        null=True, blank=True,
        help_text="Fecha de instalación en el hospital"
    )
    warranty_expiry = models.DateField(
        null=True, blank=True,
        help_text="Fecha de vencimiento de garantía"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets_asset"
        ordering = ["hospital", "name"]
        indexes = [
            models.Index(fields=["hospital", "status"], name="idx_asset_hospital_status"),
            models.Index(fields=["serial_number"], name="idx_asset_serial"),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class AssetCustomField(models.Model):
    """
    Definición de un campo personalizado por tipo de activo.

    Fracttal: Tab "Formulario Personalizado" en la ficha del activo.
    Se selecciona un formulario (template) y aparecen campos dinámicos.
    Implementamos con patrón EAV (Entity-Attribute-Value).
    """

    class FieldType(models.TextChoices):
        TEXT = "TEXT", "Texto"
        NUMBER = "NUMBER", "Número"
        DATE = "DATE", "Fecha"
        BOOLEAN = "BOOLEAN", "Sí/No"
        SELECT = "SELECT", "Selección"
        TEXTAREA = "TEXTAREA", "Texto largo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Agrupa campos por tipo de activo (ej: "Columna de Soporte Vital")
    asset_type_name = models.CharField(
        max_length=100,
        help_text="Tipo de activo al que aplica este campo. "
                  "Fracttal: nombre del Formulario Personalizado"
    )
    field_name = models.CharField(max_length=200)
    field_type = models.CharField(max_length=10, choices=FieldType.choices)
    is_required = models.BooleanField(default=False)
    # Para FieldType.SELECT: opciones separadas por pipe "|"
    options = models.TextField(
        blank=True, default="",
        help_text="Para tipo SELECT: opciones separadas por |"
    )
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
    """
    Valor de un campo personalizado para un activo específico.
    Fracttal: datos guardados en el Formulario Personalizado de cada activo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        Asset, on_delete=models.PROTECT,
        related_name="custom_field_values"
    )
    field = models.ForeignKey(
        AssetCustomField, on_delete=models.PROTECT,
        related_name="values"
    )
    value = models.TextField(
        blank=True, default="",
        help_text="Valor almacenado como texto. La app convierte según field_type."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets_assetcustomfieldvalue"
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "field"],
                name="uq_customfieldvalue_asset_field"
            )
        ]

    def __str__(self):
        return f"{self.asset.code}.{self.field.field_name} = {self.value[:50]}"


# =========================================================================
#  APP: checklists
# =========================================================================

class ChecklistTemplate(models.Model):
    """
    Plantilla de checklist reutilizable.

    Fracttal: Las "SubTareas" dentro de una tarea del Plan de Tareas.
    No tienen versionamiento explícito en Fracttal.

    En el nuevo sistema, el template es la entidad madre. Cada modificación
    crea una nueva ChecklistTemplateVersion. Las OTs completadas quedan
    vinculadas a la versión exacta (inmutable para INVIMA/GMP).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255, unique=True,
        help_text="Nombre descriptivo. Ej: 'Mantenimiento Planta Generadora Aire'"
    )
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "checklists_checklisttemplate"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ChecklistTemplateVersion(models.Model):
    """
    Versión inmutable de un template de checklist.

    Cada vez que se modifican los campos de un template, se crea nueva
    versión. Las OTs completadas quedan ancladas a la versión que usaron.
    Esto garantiza trazabilidad regulatoria: puedes reconstruir exactamente
    qué preguntas respondió el técnico.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        ChecklistTemplate, on_delete=models.PROTECT,
        related_name="versions"
    )
    version_number = models.PositiveIntegerField(
        help_text="Auto-incremental dentro del template. 1, 2, 3..."
    )
    published_at = models.DateTimeField(default=timezone.now)
    published_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="published_checklist_versions"
    )
    is_current = models.BooleanField(
        default=True,
        help_text="Solo una versión puede ser current por template"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "checklists_checklisttemplateversion"
        ordering = ["template", "-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "version_number"],
                name="uq_checklist_version"
            )
        ]

    def __str__(self):
        return f"{self.template.name} v{self.version_number}"


class ChecklistField(models.Model):
    """
    Campo individual dentro de una versión de checklist.

    Fracttal: Cada subtarea del plan tiene Tipo, Grupo/Parte, Obligatorio,
    Iteraciones. Tipos observados:
    - Localización GPS
    - Una lectura del medidor (numérico)
    - Procedimiento (texto libre)
    Probablemente existen más (foto, checkbox, selección) pero no fueron
    visibles en la exploración.
    """

    class FieldType(models.TextChoices):
        TEXT = "TEXT", "Texto libre"
        NUMBER = "NUMBER", "Valor numérico"
        BOOLEAN = "BOOLEAN", "Sí/No (checkbox)"
        SELECT = "SELECT", "Selección única"
        MULTI_SELECT = "MULTI_SELECT", "Selección múltiple"
        PHOTO = "PHOTO", "Fotografía"
        SIGNATURE = "SIGNATURE", "Firma digital"
        GPS = "GPS", "Localización GPS"        # Fracttal: Localización GPS
        METER = "METER", "Lectura de medidor"  # Fracttal: Una lectura del medidor
        DATE = "DATE", "Fecha"
        DATETIME = "DATETIME", "Fecha y hora"
        TEXTAREA = "TEXTAREA", "Texto largo"   # Fracttal: Procedimiento

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey(
        ChecklistTemplateVersion, on_delete=models.PROTECT,
        related_name="fields"
    )
    label = models.CharField(
        max_length=500,
        help_text="Texto del campo. Fracttal: descripción de la subtarea. "
                  "Ej: 'CONSUMO DE CORRIENTE EN AMPERIOS LINEA 1'"
    )
    field_type = models.CharField(max_length=15, choices=FieldType.choices)
    group = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Grupo/sección. Fracttal: Grupo/Parte. Ej: 'MOTOR 1'"
    )
    is_required = models.BooleanField(
        default=False,
        help_text="Fracttal: Obligatorio (Sí/No)"
    )
    sort_order = models.IntegerField(
        default=0,
        help_text="Orden de aparición (1, 2, 3...)"
    )
    # Para SELECT/MULTI_SELECT: opciones en JSON
    options_json = models.JSONField(
        default=list, blank=True,
        help_text='Para selección: ["opción1","opción2"]. Para METER: '
                  '{"unit":"A","min":0,"max":100}'
    )
    help_text = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Texto de ayuda para el técnico"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "checklists_checklistfield"
        ordering = ["version", "sort_order"]

    def __str__(self):
        return f"{self.version} → {self.label[:60]}"


class ChecklistResponse(models.Model):
    """
    Respuestas de un checklist asociadas a una OT.
    Una por OT. Contiene metadatos de la sesión de llenado.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.OneToOneField(
        "WorkOrder", on_delete=models.PROTECT,
        related_name="checklist_response"
    )
    version = models.ForeignKey(
        ChecklistTemplateVersion, on_delete=models.PROTECT,
        related_name="responses",
        help_text="Versión exacta del checklist que se respondió"
    )
    started_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Cuándo empezó el técnico a llenar el checklist"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Cuándo terminó de llenar"
    )
    completed_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name="checklist_responses"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "checklists_checklistresponse"

    def __str__(self):
        return f"Respuesta OT {self.work_order.wo_number}"


class ChecklistFieldResponse(models.Model):
    """
    Respuesta a un campo específico del checklist.
    Inmutable una vez que la OT se completa.

    El valor se almacena como texto en `value`. Para tipos especiales:
    - GPS: "lat,lon" ej: "6.2476,-75.5658"
    - PHOTO: UUID de la entidad Photo
    - SIGNATURE: UUID de la entidad Signature
    - METER: valor numérico como texto
    - BOOLEAN: "true" o "false"
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    response = models.ForeignKey(
        ChecklistResponse, on_delete=models.PROTECT,
        related_name="field_responses"
    )
    field = models.ForeignKey(
        ChecklistField, on_delete=models.PROTECT,
        related_name="responses"
    )
    value = models.TextField(
        blank=True, default="",
        help_text="Valor de la respuesta. Formato depende del field_type."
    )
    notes = models.TextField(
        blank=True, default="",
        help_text="Observaciones adicionales del técnico para este campo"
    )
    answered_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "checklists_checklistfieldresponse"
        constraints = [
            models.UniqueConstraint(
                fields=["response", "field"],
                name="uq_fieldresponse_response_field"
            )
        ]

    def __str__(self):
        return f"{self.field.label[:40]} = {self.value[:40]}"


# =========================================================================
#  APP: work_orders
# =========================================================================

class WorkOrder(models.Model):
    """
    Orden de Trabajo.

    Fracttal: Entidad "Orden de Trabajo" con número auto-incremental.
    Vista Kanban con estados: Pendiente → En Proceso → En Revisión →
    Finalizada.

    Campos observados: número, técnico, fecha, duración, calificación,
    progreso, costo, nota, creador. Cada OT contenía "Tareas" (1..N)
    vinculadas a activos. Simplificamos a 1 OT = 1 Asset.

    Tipos de tarea observados: CORRECTIVO, PREVENTIVO, VERIFICACION.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"             # Fracttal: Tareas Pendientes
        IN_PROGRESS = "IN_PROGRESS", "En Proceso"    # Fracttal: OTs en Proceso
        IN_REVIEW = "IN_REVIEW", "En Revisión"       # Fracttal: OTs en Revisión
        COMPLETED = "COMPLETED", "Finalizada"        # Fracttal: OTs Finalizadas
        CANCELLED = "CANCELLED", "Cancelada"         # No observado en Fracttal pero necesario

    class TaskType(models.TextChoices):
        PREVENTIVE = "PREVENTIVE", "Preventivo"         # Fracttal: PREVENTIVO
        CORRECTIVE = "CORRECTIVE", "Correctivo"         # Fracttal: CORRECTIVO
        VERIFICATION = "VERIFICATION", "Verificación"   # Fracttal: VERIFICACION
        INSTALLATION = "INSTALLATION", "Instalación"    # Requerido por negocio
        DELIVERY = "DELIVERY", "Entrega"                # Fracttal: ACTA DE ENTREGA

    class ProgressMeasure(models.TextChoices):
        SUBTASKS = "SUBTASKS", "Todas las subtareas"  # Fracttal: "Todas las subtareas"
        MANUAL = "MANUAL", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wo_number = models.PositiveIntegerField(
        unique=True,
        help_text="Número legible auto-incremental. Fracttal: 19190, 19197, etc."
    )
    asset = models.ForeignKey(
        Asset, on_delete=models.PROTECT,
        related_name="work_orders",
        help_text="Equipo al que aplica esta OT. Fracttal: Activo vinculado a la Tarea"
    )
    # --- Tipo y clasificación (observados en Fracttal) ---
    task_type = models.CharField(
        max_length=15, choices=TaskType.choices,
        help_text="Fracttal: Tipo de Tarea"
    )
    title = models.CharField(
        max_length=500,
        help_text="Fracttal: nombre de la tarea. Ej: 'MANTENIMIENTO DE PLANTA GENERADORA'"
    )
    description = models.TextField(
        blank=True, default="",
        help_text="Fracttal: campo Procedimiento en SubTareas"
    )
    classification_1 = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Fracttal: Clasificación 1. Ej: CONTRATO DE MANTENIMIENTO"
    )
    classification_2 = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Fracttal: Clasificación 2. Ej: SALIDA DE GAS MEDICINAL"
    )
    # --- Estado y progreso ---
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING,
        db_index=True
    )
    priority = models.CharField(
        max_length=10,
        choices=Asset.Priority.choices,
        default=Asset.Priority.MEDIUM,
        help_text="Fracttal: Prioridad (Alta/Media/Baja)"
    )
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Fracttal: porcentaje de progreso 0-100"
    )
    progress_measure = models.CharField(
        max_length=10, choices=ProgressMeasure.choices,
        default=ProgressMeasure.SUBTASKS,
        help_text="Fracttal: Medición de avance"
    )
    # --- Asignación ---
    assigned_to = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name="assigned_work_orders",
        null=True, blank=True,
        help_text="Fracttal: técnico asignado en la tarjeta Kanban"
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name="created_work_orders",
        help_text="Fracttal: 'Creada por DIRECCIÓN MANTENIMIENTO'"
    )
    # --- Fechas ---
    scheduled_date = models.DateField(
        help_text="Fracttal: Fecha Programada"
    )
    started_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Momento en que el técnico inició la OT"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Momento de finalización"
    )
    # --- Tiempos ---
    estimated_duration = models.DurationField(
        null=True, blank=True,
        help_text="Fracttal: Duración Estimada. Ej: 02H 10mins"
    )
    actual_duration = models.DurationField(
        null=True, blank=True,
        help_text="Fracttal: tiempo real registrado por cronómetro"
    )
    downtime = models.DurationField(
        null=True, blank=True,
        help_text="Fracttal: Tiempo de Paro por Mantenimiento"
    )
    # --- Costo y evaluación ---
    total_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Fracttal: coste Total ($ COP)"
    )
    rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Fracttal: calificación 1-5 estrellas"
    )
    notes = models.TextField(
        blank=True, default="",
        help_text="Fracttal: campo Nota"
    )
    # --- Vínculo al plan que la generó (si aplica) ---
    maintenance_plan = models.ForeignKey(
        "MaintenancePlan", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="generated_work_orders",
        help_text="Plan que generó esta OT automáticamente (null si es manual/correctiva)"
    )
    # --- Vínculo a solicitud de trabajo (si aplica) ---
    request_number = models.IntegerField(
        null=True, blank=True,
        help_text="Fracttal: Nro. Solicitud. Ej: 157"
    )
    # --- Checklist ---
    checklist_version = models.ForeignKey(
        ChecklistTemplateVersion, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="work_orders",
        help_text="Versión del checklist asignada a esta OT"
    )
    # --- Offline sync ---
    synced_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp del último sync desde la app móvil"
    )
    offline_uuid = models.UUIDField(
        null=True, blank=True, unique=True,
        help_text="UUID generado por el móvil offline para evitar duplicados en sync"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "work_orders_workorder"
        ordering = ["-wo_number"]
        indexes = [
            models.Index(fields=["status", "assigned_to"], name="idx_wo_status_assignee"),
            models.Index(fields=["asset", "status"], name="idx_wo_asset_status"),
            models.Index(fields=["scheduled_date"], name="idx_wo_scheduled_date"),
        ]

    def __str__(self):
        return f"OT-{self.wo_number} [{self.status}]"


class WorkOrderStatusHistory(models.Model):
    """
    Log de cambios de estado de una OT. Append-only.

    No existe como entidad explícita en Fracttal (los cambios de estado
    se infieren del Kanban). En el nuevo sistema, cada movimiento entre
    columnas se registra con timestamp y usuario.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT,
        related_name="status_history"
    )
    from_status = models.CharField(
        max_length=15, choices=WorkOrder.Status.choices,
        blank=True, default=""
    )
    to_status = models.CharField(
        max_length=15, choices=WorkOrder.Status.choices
    )
    changed_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name="wo_status_changes"
    )
    comment = models.TextField(blank=True, default="")
    changed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "work_orders_workorderstatushistory"
        ordering = ["work_order", "changed_at"]

    def __str__(self):
        return f"OT-{self.work_order.wo_number}: {self.from_status} → {self.to_status}"


# =========================================================================
#  APP: maintenance
# =========================================================================

class MaintenancePlan(models.Model):
    """
    Plan de mantenimiento. Genera OTs automáticamente según frecuencia.

    Fracttal: Entidad "Plan de Tareas" (174 planes observados).
    Campos: Descripción, Localización, Tareas asociadas, Activos Vinculados.

    La frecuencia (Activadores) en Fracttal estaba DENTRO de cada tarea
    del plan. Aquí la simplificamos a nivel del plan porque en el negocio
    de TodoGas todos los activos de un plan comparten la misma frecuencia.
    """

    class FrequencyUnit(models.TextChoices):
        DAYS = "DAYS", "Días"
        WEEKS = "WEEKS", "Semanas"
        MONTHS = "MONTHS", "Meses"       # Fracttal: "Cada 6 Meses"
        YEARS = "YEARS", "Años"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255, unique=True,
        help_text="Fracttal: Descripción del plan. "
                  "Ej: 'MANTENIMIENTO PLANTA GENERADORA DE AIRE MEDICINAL'"
    )
    description = models.TextField(blank=True, default="")
    task_type = models.CharField(
        max_length=15,
        choices=WorkOrder.TaskType.choices,
        default=WorkOrder.TaskType.PREVENTIVE,
        help_text="Fracttal: Tipo de Tarea (PREVENTIVO, VERIFICACION, etc.)"
    )
    classification_1 = models.CharField(max_length=100, blank=True, default="")
    classification_2 = models.CharField(max_length=100, blank=True, default="")
    priority = models.CharField(
        max_length=10,
        choices=Asset.Priority.choices,
        default=Asset.Priority.MEDIUM
    )
    estimated_duration = models.DurationField(
        null=True, blank=True,
        help_text="Fracttal: Duración Estimada"
    )
    downtime_duration = models.DurationField(
        null=True, blank=True,
        help_text="Fracttal: Tiempo de Paro por Mantenimiento"
    )
    # --- Frecuencia / Activador ---
    frequency_value = models.PositiveIntegerField(
        default=6,
        help_text="Valor numérico de la frecuencia. Ej: 6"
    )
    frequency_unit = models.CharField(
        max_length=6, choices=FrequencyUnit.choices,
        default=FrequencyUnit.MONTHS,
        help_text="Fracttal: Activadores → Fecha → 'Cada 6 Meses'"
    )
    # --- Checklist vinculado ---
    checklist_template = models.ForeignKey(
        ChecklistTemplate, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="maintenance_plans",
        help_text="Template de checklist que se usará en las OTs generadas"
    )
    # --- Activos vinculados (M2M) ---
    assets = models.ManyToManyField(
        Asset, blank=True,
        related_name="maintenance_plans",
        help_text="Fracttal: Activos Vinculados (tab del plan)"
    )
    # --- Ubicación / acceso ---
    restrict_to_hospital = models.ForeignKey(
        Hospital, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="maintenance_plans",
        help_text="Fracttal: Limitar Acceso a Esta Localización"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Fracttal: toggle habilitado/deshabilitado en cada tarea"
    )
    last_generated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Última vez que se generaron OTs desde este plan"
    )
    next_due_date = models.DateField(
        null=True, blank=True,
        help_text="Próxima fecha en que se deben generar OTs"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "maintenance_maintenanceplan"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (cada {self.frequency_value} {self.get_frequency_unit_display()})"


class MaintenancePlanExecution(models.Model):
    """
    Registro de cada ejecución del plan (cada vez que se generan OTs).
    No existe en Fracttal como entidad explícita.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        MaintenancePlan, on_delete=models.PROTECT,
        related_name="executions"
    )
    executed_at = models.DateTimeField(default=timezone.now)
    executed_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="plan_executions",
        help_text="Usuario que disparó la generación (null si fue automática)"
    )
    work_orders_created = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad de OTs generadas en esta ejecución"
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "maintenance_maintenanceplanexecution"
        ordering = ["-executed_at"]

    def __str__(self):
        return f"{self.plan.name} — {self.executed_at:%Y-%m-%d}"


# =========================================================================
#  APP: evidence
# =========================================================================

class Photo(models.Model):
    """
    Evidencia fotográfica vinculada a una OT, con metadatos GPS.

    Fracttal: Tab "Adjuntos" en la tarea de la OT (se observaron 3
    adjuntos en OT 19190). No distingue entre fotos y otros archivos.

    En el nuevo sistema tipamos la evidencia: Photo tiene lat/lon y
    timestamp obligatorios para trazabilidad regulatoria.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT,
        related_name="photos"
    )
    file_url = models.CharField(
        max_length=500,
        help_text="URL del archivo en S3/storage"
    )
    thumbnail_url = models.CharField(
        max_length=500, blank=True, default="",
        help_text="URL del thumbnail para carga rápida en móvil"
    )
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        help_text="Latitud GPS del dispositivo al tomar la foto"
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        help_text="Longitud GPS del dispositivo al tomar la foto"
    )
    taken_at = models.DateTimeField(
        help_text="Timestamp EXIF o del dispositivo al tomar la foto"
    )
    caption = models.CharField(max_length=500, blank=True, default="")
    file_hash = models.CharField(
        max_length=64, blank=True, default="",
        help_text="SHA-256 del archivo original para verificar integridad"
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name="uploaded_photos"
    )
    # Offline sync
    offline_uuid = models.UUIDField(
        null=True, blank=True, unique=True,
        help_text="UUID generado offline para deduplicación en sync"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evidence_photo"
        ordering = ["work_order", "taken_at"]

    def __str__(self):
        return f"Foto OT-{self.work_order.wo_number} ({self.taken_at:%H:%M})"


class Signature(models.Model):
    """
    Firma digital vinculada a una OT. Inmutable.

    No existe en Fracttal como entidad. Es requisito del nuevo sistema
    para certificar que el técnico completó el trabajo y el cliente
    (hospital) recibió conforme.
    """

    class SignatureType(models.TextChoices):
        TECHNICIAN = "TECHNICIAN", "Firma del técnico"
        CLIENT = "CLIENT", "Firma del cliente"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT,
        related_name="signatures"
    )
    signature_type = models.CharField(max_length=12, choices=SignatureType.choices)
    file_url = models.CharField(
        max_length=500,
        help_text="URL de la imagen de firma en S3"
    )
    signer_name = models.CharField(
        max_length=200,
        help_text="Nombre completo de quien firma"
    )
    signer_role = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Cargo de quien firma"
    )
    file_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 de la imagen de firma para no-repudio"
    )
    signed_at = models.DateTimeField(default=timezone.now)
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evidence_signature"
        constraints = [
            models.UniqueConstraint(
                fields=["work_order", "signature_type"],
                name="uq_signature_wo_type"
            )
        ]

    def __str__(self):
        return f"Firma {self.signature_type} OT-{self.work_order.wo_number}"


# =========================================================================
#  APP: inventory
# =========================================================================

class InventoryItem(models.Model):
    """
    Repuesto o insumo del inventario.

    Fracttal: Módulo "Almacenes" — VACÍO (0 registros). También existe
    "Repuestos y Suministros" como tipo de activo y como tab en la ficha
    del equipo, pero sin datos.

    Diseñado desde cero según requisitos del negocio.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, default="")
    unit_of_measure = models.CharField(
        max_length=20, default="und",
        help_text="Unidad: und, mt, kg, litro, etc."
    )
    current_stock = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Stock actual. Se actualiza automáticamente con movimientos."
    )
    min_stock = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Stock mínimo para alerta de reorden"
    )
    unit_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Costo unitario en COP"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_inventoryitem"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class StockMovement(models.Model):
    """
    Movimiento de inventario (entrada o salida).
    Las salidas se vinculan a una OT.
    """

    class MovementType(models.TextChoices):
        IN = "IN", "Entrada"
        OUT = "OUT", "Salida"
        ADJUSTMENT = "ADJUSTMENT", "Ajuste"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        InventoryItem, on_delete=models.PROTECT,
        related_name="movements"
    )
    movement_type = models.CharField(max_length=10, choices=MovementType.choices)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Cantidad (siempre positiva; el tipo indica dirección)"
    )
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="stock_movements",
        help_text="OT que consumió el repuesto (solo para salidas)"
    )
    reference = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Referencia externa (factura, remisión, etc.)"
    )
    notes = models.TextField(blank=True, default="")
    performed_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name="stock_movements"
    )
    performed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_stockmovement"
        ordering = ["-performed_at"]

    def __str__(self):
        return f"{self.movement_type} {self.quantity} × {self.item.code}"


# =========================================================================
#  APP: audit
# =========================================================================

class AuditLog(models.Model):
    """
    Log de auditoría inmutable (append-only).
    Registra cualquier cambio en cualquier entidad del sistema.

    No existe en Fracttal como entidad explícita (Fracttal tiene
    "Historiales" dentro de cada activo/OT pero no un log centralizado).

    REGLAS:
    - Este modelo NO debe permitir UPDATE ni DELETE.
    - Implementar a nivel de model manager y middleware.
    - Cada registro captura: quién, cuándo, qué entidad, qué acción,
      y el diff de los datos cambiados.
    """

    class Action(models.TextChoices):
        CREATE = "CREATE", "Crear"
        UPDATE = "UPDATE", "Actualizar"
        DELETE = "DELETE", "Eliminar"       # Soft-delete
        STATUS_CHANGE = "STATUS_CHANGE", "Cambio de estado"
        LOGIN = "LOGIN", "Inicio de sesión"
        SYNC = "SYNC", "Sincronización offline"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="audit_logs",
        help_text="Usuario que realizó la acción (null para acciones del sistema)"
    )
    action = models.CharField(max_length=15, choices=Action.choices)
    entity_type = models.CharField(
        max_length=100,
        help_text="Nombre del modelo. Ej: 'WorkOrder', 'Asset'"
    )
    entity_id = models.UUIDField(
        help_text="PK de la entidad afectada"
    )
    changes = models.JSONField(
        default=dict, blank=True,
        help_text='Diff: {"field": {"old": "X", "new": "Y"}}'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, default="")
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_auditlog"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(
                fields=["entity_type", "entity_id"],
                name="idx_audit_entity"
            ),
            models.Index(fields=["user", "timestamp"], name="idx_audit_user_time"),
        ]

    def save(self, *args, **kwargs):
        """Prohibir updates: solo INSERT."""
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("AuditLog es append-only. No se permite UPDATE.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prohibir deletes."""
        raise ValueError("AuditLog es append-only. No se permite DELETE.")

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.action} {self.entity_type} por {self.user}"


# =========================================================================
#  APP: reports
# =========================================================================

class GeneratedReport(models.Model):
    """
    PDF generado automáticamente al completar una OT.
    Incluye: datos del activo, checklist respondido, fotos, firmas.

    No existe en Fracttal como entidad (los reportes se generan bajo
    demanda desde el módulo de Inteligencia de Negocio).
    """

    class ReportType(models.TextChoices):
        WORK_ORDER = "WORK_ORDER", "Reporte de OT"
        MAINTENANCE = "MAINTENANCE", "Reporte de mantenimiento"
        DELIVERY = "DELIVERY", "Acta de entrega"
        CUSTOM = "CUSTOM", "Personalizado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="reports"
    )
    report_type = models.CharField(max_length=15, choices=ReportType.choices)
    title = models.CharField(max_length=255)
    file_url = models.CharField(
        max_length=500,
        help_text="URL del PDF en S3"
    )
    file_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 del PDF para verificar integridad"
    )
    generated_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="generated_reports"
    )
    generated_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports_generatedreport"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.report_type}: {self.title}"


class ReportSendLog(models.Model):
    """
    Registro de envío de reportes por correo electrónico.
    Trazabilidad de quién recibió qué reporte y cuándo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        GeneratedReport, on_delete=models.PROTECT,
        related_name="send_logs"
    )
    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=200, blank=True, default="")
    sent_at = models.DateTimeField(default=timezone.now)
    was_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports_reportsendlog"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.report.title} → {self.recipient_email}"


# =========================================================================
#  APP: notifications
# =========================================================================

class NotificationLog(models.Model):
    """
    Registro de notificaciones enviadas.

    Fracttal: Tiene un panel de notificaciones (observado en el header
    del dashboard) pero sin módulo de gestión visible.
    """

    class Channel(models.TextChoices):
        PUSH = "PUSH", "Push notification"
        EMAIL = "EMAIL", "Correo electrónico"
        SMS = "SMS", "SMS"
        IN_APP = "IN_APP", "Notificación in-app"

    class NotificationType(models.TextChoices):
        WO_ASSIGNED = "WO_ASSIGNED", "OT asignada"
        WO_COMPLETED = "WO_COMPLETED", "OT completada"
        WO_OVERDUE = "WO_OVERDUE", "OT vencida"
        PLAN_GENERATED = "PLAN_GENERATED", "Plan generó OTs"
        STOCK_LOW = "STOCK_LOW", "Stock bajo"
        GENERAL = "GENERAL", "General"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name="notifications"
    )
    channel = models.CharField(max_length=6, choices=Channel.choices)
    notification_type = models.CharField(max_length=15, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    body = models.TextField()
    # Referencia a la entidad que generó la notificación
    entity_type = models.CharField(max_length=100, blank=True, default="")
    entity_id = models.UUIDField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications_notificationlog"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(
                fields=["user", "is_read", "sent_at"],
                name="idx_notif_user_read"
            ),
        ]

    def __str__(self):
        return f"{self.notification_type} → {self.user.email}"
"""
===========================================================================
  CMMS TodoGas — Diagrama de Relaciones + Mapeo de Migración
===========================================================================

═══════════════════════════════════════════════════════════════════════════
  4. DIAGRAMA DE RELACIONES (todas las FK y M2M del sistema)
═══════════════════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────────────────┐
  │                        APP: users                              │
  └─────────────────────────────────────────────────────────────────┘

  Hospital (1) ──────< User (N)
      └─ user.hospital → Hospital  [PROTECT, nullable]


  ┌─────────────────────────────────────────────────────────────────┐
  │                        APP: assets                             │
  └─────────────────────────────────────────────────────────────────┘

  Hospital (1) ──────< AssetNode (N)
      └─ assetnode.hospital → Hospital  [PROTECT]

  AssetNode (1) ─────< AssetNode (N)       ← autorreferencial
      └─ assetnode.parent → AssetNode  [PROTECT, nullable]

  Hospital (1) ──────< Asset (N)
      └─ asset.hospital → Hospital  [PROTECT]

  AssetNode (1) ─────< Asset (N)
      └─ asset.node → AssetNode  [PROTECT, nullable]

  AssetCustomField (1) ──< AssetCustomFieldValue (N)
      └─ value.field → AssetCustomField  [PROTECT]

  Asset (1) ─────────< AssetCustomFieldValue (N)
      └─ value.asset → Asset  [PROTECT]


  ┌─────────────────────────────────────────────────────────────────┐
  │                       APP: checklists                          │
  └─────────────────────────────────────────────────────────────────┘

  ChecklistTemplate (1) ──< ChecklistTemplateVersion (N)
      └─ version.template → ChecklistTemplate  [PROTECT]

  User (1) ──────────────< ChecklistTemplateVersion (N)
      └─ version.published_by → User  [PROTECT, nullable]

  ChecklistTemplateVersion (1) ──< ChecklistField (N)
      └─ field.version → ChecklistTemplateVersion  [PROTECT]

  WorkOrder (1) ─────────(1) ChecklistResponse
      └─ response.work_order → WorkOrder  [PROTECT, OneToOne]

  ChecklistTemplateVersion (1) ──< ChecklistResponse (N)
      └─ response.version → ChecklistTemplateVersion  [PROTECT]

  User (1) ──────────────< ChecklistResponse (N)
      └─ response.completed_by → User  [PROTECT]

  ChecklistResponse (1) ──< ChecklistFieldResponse (N)
      └─ field_response.response → ChecklistResponse  [PROTECT]

  ChecklistField (1) ────< ChecklistFieldResponse (N)
      └─ field_response.field → ChecklistField  [PROTECT]


  ┌─────────────────────────────────────────────────────────────────┐
  │                     APP: work_orders                           │
  └─────────────────────────────────────────────────────────────────┘

  Asset (1) ─────────────< WorkOrder (N)
      └─ wo.asset → Asset  [PROTECT]

  User (1) ──────────────< WorkOrder (N)  [asignado]
      └─ wo.assigned_to → User  [PROTECT, nullable]

  User (1) ──────────────< WorkOrder (N)  [creador]
      └─ wo.created_by → User  [PROTECT]

  MaintenancePlan (1) ───< WorkOrder (N)
      └─ wo.maintenance_plan → MaintenancePlan  [PROTECT, nullable]

  ChecklistTemplateVersion (1) ──< WorkOrder (N)
      └─ wo.checklist_version → ChecklistTemplateVersion  [PROTECT, nullable]

  WorkOrder (1) ─────────< WorkOrderStatusHistory (N)
      └─ history.work_order → WorkOrder  [PROTECT]

  User (1) ──────────────< WorkOrderStatusHistory (N)
      └─ history.changed_by → User  [PROTECT]


  ┌─────────────────────────────────────────────────────────────────┐
  │                     APP: maintenance                           │
  └─────────────────────────────────────────────────────────────────┘

  ChecklistTemplate (1) ──< MaintenancePlan (N)
      └─ plan.checklist_template → ChecklistTemplate  [PROTECT, nullable]

  Hospital (1) ──────────< MaintenancePlan (N)
      └─ plan.restrict_to_hospital → Hospital  [PROTECT, nullable]

  MaintenancePlan (N) >──< Asset (N)       ← ManyToMany
      └─ plan.assets  [through table auto]

  MaintenancePlan (1) ───< MaintenancePlanExecution (N)
      └─ execution.plan → MaintenancePlan  [PROTECT]

  User (1) ──────────────< MaintenancePlanExecution (N)
      └─ execution.executed_by → User  [PROTECT, nullable]


  ┌─────────────────────────────────────────────────────────────────┐
  │                      APP: evidence                             │
  └─────────────────────────────────────────────────────────────────┘

  WorkOrder (1) ─────────< Photo (N)
      └─ photo.work_order → WorkOrder  [PROTECT]

  User (1) ──────────────< Photo (N)
      └─ photo.uploaded_by → User  [PROTECT]

  WorkOrder (1) ─────────< Signature (N)   [max 2: técnico + cliente]
      └─ signature.work_order → WorkOrder  [PROTECT]


  ┌─────────────────────────────────────────────────────────────────┐
  │                      APP: inventory                            │
  └─────────────────────────────────────────────────────────────────┘

  InventoryItem (1) ─────< StockMovement (N)
      └─ movement.item → InventoryItem  [PROTECT]

  WorkOrder (1) ─────────< StockMovement (N)
      └─ movement.work_order → WorkOrder  [PROTECT, nullable]

  User (1) ──────────────< StockMovement (N)
      └─ movement.performed_by → User  [PROTECT]


  ┌─────────────────────────────────────────────────────────────────┐
  │                       APP: audit                               │
  └─────────────────────────────────────────────────────────────────┘

  User (1) ──────────────< AuditLog (N)
      └─ log.user → User  [PROTECT, nullable]

  (entity_type + entity_id = referencia genérica a cualquier modelo)


  ┌─────────────────────────────────────────────────────────────────┐
  │                      APP: reports                              │
  └─────────────────────────────────────────────────────────────────┘

  WorkOrder (1) ─────────< GeneratedReport (N)
      └─ report.work_order → WorkOrder  [PROTECT, nullable]

  User (1) ──────────────< GeneratedReport (N)
      └─ report.generated_by → User  [PROTECT, nullable]

  GeneratedReport (1) ───< ReportSendLog (N)
      └─ send_log.report → GeneratedReport  [PROTECT]


  ┌─────────────────────────────────────────────────────────────────┐
  │                    APP: notifications                          │
  └─────────────────────────────────────────────────────────────────┘

  User (1) ──────────────< NotificationLog (N)
      └─ notification.user → User  [PROTECT]


═══════════════════════════════════════════════════════════════════════════
  RESUMEN DE CONTEO
═══════════════════════════════════════════════════════════════════════════

  Total de modelos:           21
  Total de relaciones FK:     28
  Total de relaciones M2M:     1  (MaintenancePlan.assets)
  Total de OneToOne:           1  (ChecklistResponse → WorkOrder)

  Por app:
    users          →  1 modelo  (User)
    assets         →  4 modelos (Hospital, AssetNode, Asset, AssetCustomField,
                                 AssetCustomFieldValue)
    checklists     →  5 modelos (ChecklistTemplate, ChecklistTemplateVersion,
                                 ChecklistField, ChecklistResponse,
                                 ChecklistFieldResponse)
    work_orders    →  2 modelos (WorkOrder, WorkOrderStatusHistory)
    maintenance    →  2 modelos (MaintenancePlan, MaintenancePlanExecution)
    evidence       →  2 modelos (Photo, Signature)
    inventory      →  2 modelos (InventoryItem, StockMovement)
    audit          →  1 modelo  (AuditLog)
    reports        →  2 modelos (GeneratedReport, ReportSendLog)
    notifications  →  1 modelo  (NotificationLog)


═══════════════════════════════════════════════════════════════════════════
  5. CAMPOS CRÍTICOS PARA MIGRACIÓN (Fracttal → CMMS TodoGas)
═══════════════════════════════════════════════════════════════════════════

A. MAPEO DE ENTIDADES
─────────────────────────────────────────────────────────────────────────
  Fracttal                          →  Nuevo Sistema
─────────────────────────────────────────────────────────────────────────
  Nodo Ubicación (nivel 1 árbol)    →  Hospital
  Nodo Ubicación (niveles 2+)       →  AssetNode
  Nodo Equipo (hoja del árbol)      →  Asset
  Terceros (tipo=Cliente)           →  Hospital (merge manual requerido)
  Terceros (tipo=Proveedor/Fab)     →  Campo Asset.supplier (denormalizado)
  Recursos Humanos + Cuenta         →  User
  Plan de Tareas                    →  MaintenancePlan
  Tarea (dentro del plan)           →  Campos de MaintenancePlan (simplificado)
  SubTareas (dentro de tarea)       →  ChecklistTemplate + ChecklistField
  Activadores (trigger)             →  MaintenancePlan.frequency_*
  Orden de Trabajo                  →  WorkOrder
  Tarea dentro de OT                →  WorkOrder (1:1 en nuevo sistema)
  Adjuntos                          →  Photo + files genéricos
  Formulario Personalizado          →  AssetCustomField + AssetCustomFieldValue
  Solicitud de Trabajo              →  WorkOrder.request_number (referencia)
  Almacenes                         →  InventoryItem (sin datos que migrar)
─────────────────────────────────────────────────────────────────────────

B. CAMPOS QUE REQUIEREN MAPEO ESPECIAL
─────────────────────────────────────────────────────────────────────────

  1. RUTA JERÁRQUICA DEL ACTIVO
     Fracttal: "// CLINICA VITHA/ UCI ADULTOS/"
     Nuevo: Se descompone en Hospital.name + AssetNode.path
     Riesgo: Parsing de strings con formato inconsistente (//, /)

  2. NOMBRE DEL ACTIVO (contiene metadata embebida)
     Fracttal: "COLUMNA DE SOPORTE VITAL / CUBICULO 21"
     El nombre en Fracttal a veces incluye la ubicación dentro del nombre.
     Nuevo: Asset.name debe limpiarse, y la ubicación va en AssetNode.
     Riesgo: Pérdida de contexto al separar nombre de ubicación.

  3. FABRICANTE / MODELO / SERIAL (formato con delimitadores)
     Fracttal: "/MARCA: BMI/", "/BPE-1/BF1-X/", "/SN: 697581624231006031/"
     Nuevo: Asset.manufacturer, model, serial_number (texto limpio)
     Acción: Script de limpieza que quite /MARCA:/, /SN:/, y los /.../ 

  4. CÓDIGO DEL ACTIVO (frecuentemente vacío)
     Fracttal: Campo "Código" vacío en muchos activos.
     Nuevo: Asset.code es UNIQUE y OBLIGATORIO.
     Acción: Generar código automático durante migración para los que
     no tengan. Formato sugerido: {HOSPITAL_CODE}-{TIPO}-{SEQ}
     Ej: VITHA-CSV-001

  5. CLASIFICACIÓN 1 y 2 (polimórficas)
     Fracttal: Los mismos campos "Clasificación 1/2" se usan en activos,
     tareas, OTs y personal, pero con listas de valores diferentes:
       - Activos: GARANTIA, PENDANT
       - Tareas: CONTRATO DE MANTENIMIENTO, GESTION FARMACO...
       - Personal: INGENIERO, COORDINADOR, TECNOLOGO
     Nuevo: Campos de texto libre por modelo. Considerar normalizar a
     catálogos separados en el futuro.

  6. TIPOS DE TAREA
     Fracttal: CORRECTIVO, PREVENTIVO, VERIFICACION (observados)
     Nuevo: PREVENTIVE, CORRECTIVE, VERIFICATION, INSTALLATION, DELIVERY
     Acción: Mapeo 1:1 + dos tipos nuevos (INSTALLATION, DELIVERY)
     que corresponden a "ACTA DE ENTREGA" observado en planes.

  7. ESTADOS DE OT
     Fracttal: Tareas Pendientes, OTs en Proceso, OTs en Revisión, 
               OTs Finalizadas (4 estados en Kanban)
     Nuevo: PENDING, IN_PROGRESS, IN_REVIEW, COMPLETED, CANCELLED
     Acción: Mapeo 1:1 + estado CANCELLED nuevo.
     Riesgo: En Fracttal no queda claro si hay subestados.

  8. NÚMERO DE OT
     Fracttal: Auto-incremental global (19188, 19190, 19197...)
     Nuevo: WorkOrder.wo_number (PositiveIntegerField, unique)
     Acción: Preservar numeración de Fracttal. Continuar la secuencia
     desde el último número migrado.

  9. DURACIÓN (formato no estándar)
     Fracttal: "02H 10mins", "01H 00mins", "00:10"
     Nuevo: DurationField (timedelta de Python)
     Acción: Parser que convierta los formatos de Fracttal a timedelta.

  10. PLAN DE TAREAS → OT (relación N-M aplanada a 1-1)
      Fracttal: Un Plan tiene N Tareas, cada Tarea tiene N SubTareas,
      y una OT puede tener N Tareas de diferentes planes.
      Nuevo: 1 OT = 1 Asset + 1 Plan opcional. Si un plan genera
      trabajo para 15 activos, se crean 15 OTs individuales.
      Riesgo: OTs históricas con múltiples activos deben dividirse
      en N registros (uno por activo) durante migración.

  11. SUBTAREAS → CHECKLIST (reestructuración)
      Fracttal: SubTareas dentro de Tarea del Plan, con tipos:
      "Localización GPS", "Una lectura del medidor", "Procedimiento"
      Nuevo: ChecklistTemplate → Version → Field con tipos tipados
      Acción: Cada conjunto de subtareas de un plan se convierte en
      un ChecklistTemplate + Version v1 + N ChecklistFields.
      Riesgo: Mapeo de tipos:
        - "Localización GPS" → FieldType.GPS
        - "Una lectura del medidor" → FieldType.METER
        - "Procedimiento" (texto libre) → FieldType.TEXTAREA
        - Otros tipos no observados: investigar antes de migrar.

  12. USUARIO → ROL (simplificación)
      Fracttal: Clasificación 1 como descriptor de cargo (INGENIERO,
      COORDINADOR, TECNOLOGO) + sistema de permisos no visible.
      Nuevo: 4 roles fijos (ADMIN, SUP, TEC, CLI).
      Acción: Mapeo manual:
        - COORDINADOR → SUP
        - TECNOLOGO → TEC
        - INGENIERO → SUP o TEC (decidir caso por caso)
        - Cuentas de hospital (si existen) → CLI


C. CAMPOS DE FRACTTAL QUE PODRÍAN PERDERSE
─────────────────────────────────────────────────────────────────────────

  1. Otro 2: Campo genérico sin uso claro. Verificar si tiene datos en
     algún activo antes de descartarlo.

  2. Horas de uso promedio diario: Se preserva en Asset.avg_daily_usage_hours
     pero el formato "24:00" necesita parsearse a decimal (24.00).

  3. Proveedor como entidad: En Fracttal, Terceros es una entidad con
     Sucursales, Contactos, Servicios. En el nuevo sistema se simplifica
     a un campo de texto en Asset. Si se necesita catálogo de proveedores,
     crear modelo Supplier en el futuro.

  4. QR Público: El formato https://one.fracttal.com/qr/xxx no servirá
     en el nuevo sistema. Se deben regenerar QRs con URLs del nuevo dominio.

  5. Formulario Personalizado: Los templates y respuestas de formularios
     personalizados deben exportarse de Fracttal y mapearse a
     AssetCustomField + AssetCustomFieldValue. Si los datos están vacíos
     (como en el activo observado), no hay qué migrar.

  6. Solicitudes de Trabajo: Fracttal tiene módulo "Solicitudes" con su
     propio flujo. En el nuevo sistema solo se guarda el número de
     referencia (WorkOrder.request_number). Las solicitudes activas deben
     convertirse en OTs de tipo CORRECTIVE.

  7. Historiales del activo: Fracttal tiene tab "Historiales" en cada
     activo con el historial de OTs, cambios, etc. En el nuevo sistema
     esto se reconstruye a partir de WorkOrder + AuditLog. Los historiales
     previos deben importarse como registros de AuditLog con action=CREATE
     y timestamp original.

  8. Gestión Documental: Tab "Gestión Documental" en activos y terceros.
     No se modela como entidad separada; los documentos se almacenan como
     adjuntos genéricos o en el Disco Virtual (fuera de scope).

  9. Calificación (★★★★★): Fracttal muestra 5 estrellas en la OT.
     Preservado en WorkOrder.rating. Migrar valores históricos.

  10. Temporizador / Cronómetro: Fracttal tiene un cronómetro en vivo
      en la OT (observado "00:00" con ícono de play). En el nuevo sistema
      se calcula como diferencia entre started_at y completed_at.
      El valor del cronómetro de Fracttal se migra a actual_duration.


D. DATOS QUE NO NECESITAN MIGRACIÓN
─────────────────────────────────────────────────────────────────────────

  - Almacenes: vacío (0 registros)
  - Fracttal AI: funcionalidad propia de Fracttal
  - Disco Virtual: almacenamiento genérico, fuera de scope del CMMS
  - Monitoreo: IoT/sensores, fuera de scope inicial
  - Automatizador: reglas que se reimplementarán como Celery tasks
  - Inteligencia de Negocio: dashboards que se reconstruirán
  - Notificaciones: las notificaciones históricas no se migran

"""
