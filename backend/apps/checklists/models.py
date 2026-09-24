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
    # Grupos que se repiten, por nombre: el bloque "Toma" de 9 preguntas se
    # define una vez y el plan dice cuantas veces va (PlanTask.block_counts).
    # En Fracttal el bloque se escribe a mano N veces.
    repeatable_groups = models.JSONField(default=list, blank=True)
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

    @property
    def allows_na(self):
        """Un Si/No con "Permite N/A" (decision del 2026-09-24): guarda "na"."""
        opciones = self.options_json if isinstance(self.options_json, dict) else {}
        return self.field_type == self.FieldType.BOOLEAN and bool(opciones.get("allow_na"))

    def __str__(self):
        return f"{self.version} → {self.label[:60]}"


class ChecklistResponse(models.Model):
    """
    Respuestas del checklist de una tarea. Una por tarea: en una OT con varios
    activos, cada uno tiene la suya.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.OneToOneField(
        "maintenance.Task", on_delete=models.PROTECT,
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
        null=True, blank=True,
        related_name="checklist_responses"
    )
    # Cuantas veces se responde cada grupo repetible: {"Toma": 20}. Nace con lo
    # que dice el plan (planned_block_counts) y el tecnico lo ajusta en campo
    # si encuentra otra cantidad; la diferencia se le avisa al administrador.
    block_counts = models.JSONField(default=dict, blank=True)
    planned_block_counts = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "checklists_checklistresponse"
        # Sin orden estable la paginacion puede repetir u omitir filas entre
        # paginas (UnorderedObjectListWarning).
        ordering = ["-created_at"]

    def __str__(self):
        return f"Respuesta de {self.task}"

    def count_for(self, group):
        """Cuantas veces se responde un grupo. Uno que no se repite, una vez."""
        if not group or group not in self.version.repeatable_groups:
            return 1
        return max(1, int(self.block_counts.get(group, 1) or 1))

    def slots(self, fields=None):
        """
        Las respuestas que espera el checklist, como pares (campo, repeticion).

        Un campo que no se repite tiene repeticion 0; uno de un grupo repetible,
        de 1 a N. Es la regla que usan el avance, el cierre y el acta.
        """
        if fields is None:
            fields = self.version.fields.all()
        pares = []
        for campo in fields:
            if campo.group and campo.group in self.version.repeatable_groups:
                pares.extend((campo, n) for n in range(1, self.count_for(campo.group) + 1))
            else:
                pares.append((campo, 0))
        return pares


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
    # 0 en un campo que no se repite; 1..N en uno de un grupo repetible (la
    # toma 1, la toma 2...). El mismo campo se responde una vez por toma.
    repetition = models.PositiveSmallIntegerField(default=0)
    answered_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "checklists_checklistfieldresponse"
        # El acta agrupa las respuestas con {% regroup %}, que solo agrupa
        # elementos ADYACENTES: sin este orden un mismo grupo sale partido y
        # repetido en el PDF que recibe el cliente. Ademas respeta el orden en
        # que el tecnico vio los campos en la app.
        ordering = ["field__group", "repetition", "field__sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["response", "field", "repetition"],
                name="uq_fieldresponse_response_field_rep"
            )
        ]

    def __str__(self):
        return f"{self.field.label[:40]} = {self.value[:40]}"
