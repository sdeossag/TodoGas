import uuid

from django.db import models
from django.utils import timezone


class ChecklistTemplate(models.Model):
    """
    Plantilla de checklist reutilizable.
    Fracttal: subtareas dentro de una tarea del Plan de Tareas.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
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
    Las OTs completadas quedan ancladas a la versión que usaron.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        ChecklistTemplate, on_delete=models.PROTECT,
        related_name="versions"
    )
    version_number = models.PositiveIntegerField()
    published_at = models.DateTimeField(default=timezone.now)
    published_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="published_checklist_versions"
    )
    is_current = models.BooleanField(default=True)
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

    # `is_current` es el unico campo mutable: al publicar una version nueva hay
    # que bajar la bandera de la anterior. Todo lo demas define QUE preguntaba
    # el checklist, y editarlo reescribiria retroactivamente el contenido de
    # OTs ya cerradas contra esta version. Editar un template crea una version
    # nueva (ver ChecklistTemplateVersionCreateSerializer), nunca modifica esta.
    _MUTABLE_FIELDS = frozenset({"is_current"})

    def save(self, *args, **kwargs):
        if self._state.adding:
            return super().save(*args, **kwargs)

        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            forbidden = set(update_fields) - self._MUTABLE_FIELDS
            if forbidden:
                raise ValueError(
                    "ChecklistTemplateVersion es inmutable. Campos no "
                    f"modificables: {sorted(forbidden)}. Publica una version "
                    "nueva en lugar de editar esta."
                )
            return super().save(*args, **kwargs)

        # Sin update_fields hay que comparar contra lo almacenado, porque un
        # save() completo reescribiria toda la fila.
        stored = type(self).objects.filter(pk=self.pk).values().first()
        if stored is not None:
            changed = {
                name
                for name, value in stored.items()
                if getattr(self, name, value) != value
            }
            forbidden = changed - self._MUTABLE_FIELDS
            if forbidden:
                raise ValueError(
                    "ChecklistTemplateVersion es inmutable. Campos no "
                    f"modificables: {sorted(forbidden)}. Publica una version "
                    "nueva en lugar de editar esta."
                )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(
            "ChecklistTemplateVersion no se elimina: las OTs cerradas quedan "
            "ancladas a la version que usaron."
        )

    def __str__(self):
        return f"{self.template.name} v{self.version_number}"


class ChecklistField(models.Model):
    """
    Campo individual dentro de una versión de checklist.
    Fracttal: subtarea del plan con Tipo, Grupo/Parte, Obligatorio.
    """

    class FieldType(models.TextChoices):
        TEXT = "TEXT", "Texto libre"
        NUMBER = "NUMBER", "Valor numérico"
        BOOLEAN = "BOOLEAN", "Sí/No (checkbox)"
        SELECT = "SELECT", "Selección única"
        MULTI_SELECT = "MULTI_SELECT", "Selección múltiple"
        PHOTO = "PHOTO", "Fotografía"
        SIGNATURE = "SIGNATURE", "Firma digital"
        GPS = "GPS", "Localización GPS"
        METER = "METER", "Lectura de medidor"
        DATE = "DATE", "Fecha"
        DATETIME = "DATETIME", "Fecha y hora"
        TEXTAREA = "TEXTAREA", "Texto largo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey(
        ChecklistTemplateVersion, on_delete=models.PROTECT,
        related_name="fields"
    )
    label = models.CharField(max_length=500)
    field_type = models.CharField(max_length=15, choices=FieldType.choices)
    group = models.CharField(max_length=100, blank=True, default="")
    is_required = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    options_json = models.JSONField(default=list, blank=True)
    help_text = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "checklists_checklistfield"
        ordering = ["version", "sort_order"]

    def save(self, *args, **kwargs):
        # Un campo pertenece a una version publicada y define la pregunta que
        # respondio el tecnico. Editar el label de un campo cambiaria, sobre
        # una OT ya cerrada, que se le pregunto: la respuesta seguiria ahi pero
        # contra otro enunciado. Los campos se crean junto con su version.
        if not self._state.adding:
            raise ValueError(
                "ChecklistField es inmutable. Publica una version nueva del "
                "template en lugar de editar sus campos."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(
            "ChecklistField no se elimina: las respuestas de OTs cerradas "
            "apuntan a el."
        )

    def __str__(self):
        return f"{self.version} → {self.label[:60]}"


class ChecklistResponse(models.Model):
    """
    Respuestas de un checklist asociadas a una OT. Una por OT.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.OneToOneField(
        "work_orders.WorkOrder", on_delete=models.PROTECT,
        related_name="checklist_response",
    )
    version = models.ForeignKey(
        ChecklistTemplateVersion, on_delete=models.PROTECT,
        related_name="responses"
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "users.User", on_delete=models.PROTECT,
        related_name="checklist_responses"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "checklists_checklistresponse"
        # Sin orden estable la paginacion puede repetir u omitir filas entre
        # paginas (UnorderedObjectListWarning).
        ordering = ["-created_at"]

    def __str__(self):
        return f"Respuesta OT {self.work_order.wo_number}"


class ChecklistFieldResponse(models.Model):
    """
    Respuesta a un campo específico del checklist. Inmutable tras completar la OT.
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
    value = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    answered_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "checklists_checklistfieldresponse"
        # El acta agrupa las respuestas con {% regroup %}, que solo agrupa
        # elementos ADYACENTES: sin este orden un mismo grupo sale partido y
        # repetido en el PDF que recibe el cliente. Ademas respeta el orden en
        # que el tecnico vio los campos en la app.
        ordering = ["field__group", "field__sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["response", "field"],
                name="uq_fieldresponse_response_field"
            )
        ]

    def __str__(self):
        return f"{self.field.label[:40]} = {self.value[:40]}"
