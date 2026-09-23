import base64
import hashlib
import uuid
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import serializers

from apps.maintenance.models import Task
from apps.work_orders.device_time import device_time
from apps.work_orders.models import Finding, WorkOrder

from .models import Photo, Signature

MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_EXTS = {"jpg", "jpeg", "png", "webp"}


def _storage_url(path):
    """Genera URL (pre-firmada en S3, local en dev) para una clave de storage."""
    if not path:
        return None
    if path.startswith("http"):
        return path
    return default_storage.url(path)


def _coordenada(value):
    """Grados con 7 decimales (~1 cm), lo que guarda el modelo."""
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.0000001"))


# ── Photo ──────────────────────────────────────────────────────────────────────

class PhotoSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    uploaded_by = serializers.SerializerMethodField()
    task_asset = serializers.SerializerMethodField()

    class Meta:
        model = Photo
        fields = [
            "id", "work_order", "task", "task_asset", "finding", "file_url", "thumbnail_url",
            "latitude", "longitude", "taken_at", "caption",
            "file_hash", "uploaded_by", "offline_uuid", "created_at",
        ]

    def get_file_url(self, obj):
        return _storage_url(obj.file_url)

    def get_task_asset(self, obj):
        """De que activo es la foto, cuando el tecnico lo indico."""
        if not obj.task_id:
            return None
        a = obj.task.asset
        return {"id": str(a.id), "code": a.code, "name": a.name}

    def get_uploaded_by(self, obj):
        if not obj.uploaded_by_id:
            return None
        u = obj.uploaded_by
        return {"id": str(u.id), "full_name": f"{u.first_name} {u.last_name}".strip()}


class PhotoCreateSerializer(serializers.Serializer):
    work_order = serializers.PrimaryKeyRelatedField(queryset=WorkOrder.objects.all())
    # Opcional: el activo de la OT al que corresponde la foto. En el acta las
    # fotos se agrupan por activo; sin tarea van como fotos de la visita.
    task = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(), required=False, allow_null=True
    )
    # Opcional: el hallazgo al que pertenece la foto (bloque E).
    finding = serializers.PrimaryKeyRelatedField(
        queryset=Finding.objects.all(), required=False, allow_null=True
    )
    file = serializers.FileField()
    # Coordenadas como llegan del GPS del telefono (37.421998333333335) y
    # redondeadas a 7 decimales en _coordenada: un DecimalField rechazaba el
    # valor por "mas de 12 digitos" antes de poder redondearlo, y la foto o la
    # firma con GPS no subia nunca.
    latitude = serializers.FloatField(required=False, allow_null=True, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, allow_null=True, min_value=-180, max_value=180)
    taken_at = serializers.DateTimeField()
    caption = serializers.CharField(max_length=500, required=False, default="", allow_blank=True)
    offline_uuid = serializers.UUIDField(required=False, allow_null=True)

    def validate_latitude(self, value):
        return _coordenada(value)

    def validate_longitude(self, value):
        return _coordenada(value)

    def validate(self, attrs):
        tarea = attrs.get("task")
        if tarea is not None and tarea.work_order_id != attrs["work_order"].id:
            raise serializers.ValidationError({"task": "La tarea no es de esta OT."})
        hallazgo = attrs.get("finding")
        if hallazgo is not None:
            if hallazgo.work_order_id != attrs["work_order"].id:
                raise serializers.ValidationError({"finding": "El hallazgo no es de esta OT."})
            # Sin tarea, va con la del equipo del hallazgo: en el acta sale en su bloque.
            if tarea is None:
                attrs["task"] = attrs["work_order"].tasks.filter(
                    asset_id=hallazgo.asset_id
                ).exclude(status="CANCELLED").first()
        return attrs

    def validate_file(self, file):
        if file.size > MAX_PHOTO_BYTES:
            raise serializers.ValidationError(
                f"El archivo supera el limite de {MAX_PHOTO_BYTES // (1024 * 1024)} MB."
            )
        name = getattr(file, "name", "") or ""
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in ALLOWED_IMAGE_EXTS:
            raise serializers.ValidationError(
                "Solo se aceptan imagenes JPEG, PNG o WEBP."
            )
        # Calcular hash antes de seek(0) para reutilizar el puntero en create()
        content = file.read()
        file.seek(0)
        file._sha256 = hashlib.sha256(content).hexdigest()
        return file

    def create(self, validated_data):
        uploaded_by = validated_data.pop("uploaded_by")
        file = validated_data.pop("file")
        work_order = validated_data["work_order"]

        content = file.read()
        file_hash = getattr(file, "_sha256", hashlib.sha256(content).hexdigest())
        name = getattr(file, "name", "photo") or "photo"
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else "jpg"
        s3_key = f"evidence/photos/{work_order.id}/{uuid.uuid4().hex}.{ext}"
        saved_key = default_storage.save(s3_key, ContentFile(content))
        file_url = default_storage.url(saved_key)

        return Photo.objects.create(
            work_order=work_order,
            file_url=saved_key,          # guardamos la clave S3, no la URL firmada
            file_hash=file_hash,
            latitude=validated_data.get("latitude"),
            longitude=validated_data.get("longitude"),
            taken_at=validated_data["taken_at"],
            caption=validated_data.get("caption", ""),
            offline_uuid=validated_data.get("offline_uuid"),
            uploaded_by=uploaded_by,
            task=validated_data.get("task"),
            finding=validated_data.get("finding"),
        )


# ── Signature ──────────────────────────────────────────────────────────────────

class SignatureSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    hash_sha256 = serializers.CharField(source="file_hash", read_only=True)

    class Meta:
        model = Signature
        fields = [
            "id", "work_order", "signature_type", "file_url",
            "signer_name", "signer_role", "hash_sha256",
            "signed_at", "latitude", "longitude", "created_at",
        ]

    def get_file_url(self, obj):
        return _storage_url(obj.file_url)


class SignatureCreateSerializer(serializers.Serializer):
    work_order = serializers.PrimaryKeyRelatedField(queryset=WorkOrder.objects.all())
    image_data = serializers.CharField()
    signer_name = serializers.CharField(max_length=200)
    signer_role = serializers.CharField(max_length=100, required=False, default="", allow_blank=True)
    signature_type = serializers.ChoiceField(
        choices=Signature.SignatureType.choices,
        default=Signature.SignatureType.TECHNICIAN,
        required=False,
    )
    # Coordenadas como llegan del GPS del telefono (37.421998333333335) y
    # redondeadas a 7 decimales en _coordenada: un DecimalField rechazaba el
    # valor por "mas de 12 digitos" antes de poder redondearlo, y la foto o la
    # firma con GPS no subia nunca.
    latitude = serializers.FloatField(required=False, allow_null=True, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, allow_null=True, min_value=-180, max_value=180)
    # Hora en que se firmo en el telefono; la manda la cola offline.
    signed_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_latitude(self, value):
        return _coordenada(value)

    def validate_longitude(self, value):
        return _coordenada(value)

    def validate_image_data(self, value):
        # Strip data URI prefix if present (frontend may or may not strip it)
        if "," in value:
            value = value.split(",", 1)[1]
        try:
            base64.b64decode(value, validate=True)
        except Exception:
            raise serializers.ValidationError("image_data no es un base64 valido.")
        return value  # devolvemos ya sin prefijo

    def validate(self, data):
        work_order = data["work_order"]
        sig_type = data.get("signature_type", Signature.SignatureType.TECHNICIAN)
        if Signature.objects.filter(work_order=work_order, signature_type=sig_type).exists():
            raise serializers.ValidationError(
                f"Ya existe una firma de tipo '{sig_type}' para esta OT."
            )
        return data

    def create(self, validated_data):
        image_data = validated_data["image_data"]
        img_bytes = base64.b64decode(image_data)
        file_hash = hashlib.sha256(img_bytes).hexdigest()

        work_order = validated_data["work_order"]
        sig_type = validated_data.get("signature_type", Signature.SignatureType.TECHNICIAN)
        s3_key = f"evidence/signatures/{work_order.id}/{sig_type}_{uuid.uuid4().hex}.png"
        saved_key = default_storage.save(s3_key, ContentFile(img_bytes))

        return Signature.objects.create(
            work_order=work_order,
            signature_type=sig_type,
            file_url=saved_key,          # clave S3, URL se genera al serializar
            signer_name=validated_data["signer_name"],
            signer_role=validated_data.get("signer_role", ""),
            file_hash=file_hash,
            signed_at=device_time(validated_data.get("signed_at"), work_order),
            latitude=validated_data.get("latitude"),
            longitude=validated_data.get("longitude"),
        )
