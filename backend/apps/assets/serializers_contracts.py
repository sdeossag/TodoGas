import uuid

from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import serializers

from apps.users.scope import ScopedFieldsMixin

from .contracts import hoy
from .models import Asset, Contract, ContractAsset

MAX_CONTRACT_BYTES = 20 * 1024 * 1024  # 20 MB
ALLOWED_CONTRACT_EXTS = {"pdf", "doc", "docx", "jpg", "jpeg", "png"}


class ContractSerializer(ScopedFieldsMixin, serializers.ModelSerializer):
    """
    El archivo sube como multipart en `file`; `remove_file` lo quita. En la
    respuesta va `file_url`, firmada en S3 como las fotos.
    """

    scoped_fields = {"hospital": "hospitals", "node": "nodes", "asset_ids": "assets"}

    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    node_path = serializers.CharField(source="node.path", read_only=True, default=None)
    asset_ids = serializers.PrimaryKeyRelatedField(
        source="assets", queryset=Asset.objects.all(), many=True, required=False,
    )
    assets_info = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    days_left = serializers.SerializerMethodField()
    file = serializers.FileField(write_only=True, required=False)
    remove_file = serializers.BooleanField(write_only=True, required=False, default=False)
    file_url = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            "id", "kind", "kind_display", "name", "description",
            "hospital", "hospital_name", "node", "node_path",
            "asset_ids", "assets_info",
            "start_date", "end_date", "status", "days_left",
            "file", "remove_file", "file_url", "file_name",
            "created_by_name", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "file_name", "created_at", "updated_at"]

    def _hoy(self):
        if "hoy" not in self.context:
            self.context["hoy"] = hoy()
        return self.context["hoy"]

    def get_assets_info(self, obj):
        return [{"id": str(a.id), "code": a.code, "name": a.name} for a in obj.assets.all()]

    def get_status(self, obj):
        return obj.status_on(self._hoy())

    def get_days_left(self, obj):
        return (obj.end_date - self._hoy()).days

    def get_file_url(self, obj):
        return default_storage.url(obj.file_key) if obj.file_key else None

    def get_created_by_name(self, obj):
        u = obj.created_by
        if u is None:
            return None
        return f"{u.first_name} {u.last_name}".strip() or u.email

    def validate_file(self, file):
        if file.size > MAX_CONTRACT_BYTES:
            raise serializers.ValidationError(
                f"El archivo supera el limite de {MAX_CONTRACT_BYTES // (1024 * 1024)} MB."
            )
        name = getattr(file, "name", "") or ""
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in ALLOWED_CONTRACT_EXTS:
            raise serializers.ValidationError("Solo se aceptan PDF, Word o imagenes JPG y PNG.")
        return file

    def validate(self, attrs):
        def valor(campo):
            if campo in attrs:
                return attrs[campo]
            return getattr(self.instance, campo, None) if self.instance else None

        if self.instance is not None and "kind" in attrs and attrs["kind"] != self.instance.kind:
            raise serializers.ValidationError({"kind": "No se puede cambiar el tipo de un documento."})
        kind, hospital = valor("kind"), valor("hospital")
        inicio, fin = valor("start_date"), valor("end_date")
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError({"end_date": "El fin de la vigencia es anterior al inicio."})

        node = valor("node")
        if node is not None and hospital is not None and node.hospital_id != hospital.id:
            raise serializers.ValidationError({"node": "La ubicacion no es de ese hospital."})

        if "assets" in attrs:
            equipos = attrs["assets"]
        elif self.instance is not None:
            equipos = list(self.instance.assets.all())
        else:
            equipos = []
        if kind == Contract.Kind.WARRANTY:
            if node is not None:
                raise serializers.ValidationError({"node": "La garantia cubre equipos, no una ubicacion."})
            if not equipos:
                raise serializers.ValidationError({"asset_ids": "Elige los equipos que cubre la garantia."})
            ajenos = [a.code for a in equipos if hospital is not None and a.hospital_id != hospital.id]
            if ajenos:
                raise serializers.ValidationError(
                    {"asset_ids": f"No son de ese hospital: {', '.join(ajenos)}."}
                )
        elif equipos:
            raise serializers.ValidationError(
                {"asset_ids": "Un contrato cubre el hospital o una ubicacion, no equipos sueltos."}
            )
        return attrs

    def _guardar_archivo(self, contract, file):
        name = getattr(file, "name", "") or "documento"
        ext = name.rsplit(".", 1)[-1].lower()
        contract.file_key = default_storage.save(
            f"contracts/{contract.id}/{uuid.uuid4().hex}.{ext}", file
        )
        contract.file_name = name[-255:]
        contract.save(update_fields=["file_key", "file_name", "updated_at"])

    def create(self, validated_data):
        file = validated_data.pop("file", None)
        validated_data.pop("remove_file", None)
        equipos = validated_data.pop("assets", [])
        with transaction.atomic():
            contract = Contract.objects.create(**validated_data)
            ContractAsset.objects.bulk_create(
                [ContractAsset(contract=contract, asset=a) for a in equipos]
            )
            if file is not None:
                self._guardar_archivo(contract, file)
        return contract

    def update(self, instance, validated_data):
        file = validated_data.pop("file", None)
        quitar = validated_data.pop("remove_file", False)
        equipos = validated_data.pop("assets", None)
        # Si cambia el fin (una prorroga), los avisos vuelven a empezar.
        if "end_date" in validated_data and validated_data["end_date"] != instance.end_date:
            instance.last_notice = Contract.Notice.NONE
        with transaction.atomic():
            for campo, valor in validated_data.items():
                setattr(instance, campo, valor)
            instance.save()
            if equipos is not None:
                nuevos = {a.id for a in equipos}
                instance.asset_links.exclude(asset_id__in=nuevos).delete()
                ya = set(instance.asset_links.values_list("asset_id", flat=True))
                ContractAsset.objects.bulk_create(
                    [ContractAsset(contract=instance, asset=a) for a in equipos if a.id not in ya]
                )
            if file is not None:
                self._guardar_archivo(instance, file)
            elif quitar and instance.file_key:
                # El archivo anterior queda en el almacenamiento: solo se desliga.
                instance.file_key = ""
                instance.file_name = ""
                instance.save(update_fields=["file_key", "file_name", "updated_at"])
        return instance
