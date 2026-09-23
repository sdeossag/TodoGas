from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User


def _validar_alcance(attrs, instance=None):
    """
    Hospital y parte del arbol a los que se limita el usuario (apps.users.scope).
    El cliente siempre tiene hospital; el administrador nunca se limita (no
    puede quedar fuera de su propio sistema); el nodo es de ese hospital.
    """
    def actual(campo):
        return attrs[campo] if campo in attrs else getattr(instance, campo, None)

    rol = actual("role")
    hospital = actual("hospital")
    nodo = actual("scope_node")
    if rol == User.Role.ADMIN:
        attrs["hospital"] = None
        attrs["scope_node"] = None
        return attrs
    if rol == User.Role.CLI and hospital is None:
        raise serializers.ValidationError(
            {"hospital": "Una cuenta de hospital necesita su hospital."}
        )
    if nodo is not None:
        if hospital is None:
            raise serializers.ValidationError(
                {"scope_node": "Para limitar a una ubicación, primero elige el hospital."}
            )
        if nodo.hospital_id != hospital.pk:
            raise serializers.ValidationError(
                {"scope_node": "La ubicación es de otro hospital."}
            )
    return attrs


class UserSerializer(serializers.ModelSerializer):
    """Lectura pública de un usuario. No expone datos sensibles."""

    full_name = serializers.SerializerMethodField()
    scope_node_path = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "role", "employee_code", "phone", "is_active",
            "must_change_password", "hospital", "scope_node", "scope_node_path",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "email", "created_at", "updated_at"]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_scope_node_path(self, obj):
        return obj.scope_node.path if obj.scope_node_id else None


class UserCreateSerializer(serializers.ModelSerializer):
    """Crea un usuario nuevo. Solo ADMIN puede usar este serializer."""

    password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "email", "first_name", "last_name", "role",
            "employee_code", "phone", "hospital", "scope_node", "password",
        ]

    def validate(self, attrs):
        return _validar_alcance(attrs)

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.must_change_password = True
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Actualización parcial de un usuario existente (ADMIN o propio perfil)."""

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "phone", "employee_code",
            "hospital", "scope_node", "is_active",
        ]

    def validate(self, attrs):
        # Cambiar de hospital sin decir el nodo lo suelta: el viejo es de otro.
        if "hospital" in attrs and "scope_node" not in attrs and self.instance and (
            self.instance.scope_node_id
            and getattr(attrs["hospital"], "pk", None) != self.instance.hospital_id
        ):
            attrs["scope_node"] = None
        return _validar_alcance(attrs, self.instance)

    def validate_is_active(self, value):
        # No existe una acción `activate`, así que reactivar sólo es posible por
        # PATCH. Se replica aquí el resguardo de la acción `deactivate`: un
        # admin no puede dejarse a sí mismo fuera del sistema.
        request = self.context.get("request")
        if value is False and request is not None and self.instance == request.user:
            raise serializers.ValidationError("No puedes desactivarte a ti mismo.")
        return value

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Cambio de contraseña autenticado (el propio usuario)."""

    current_password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})
    new_password_confirm = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Las contraseñas no coinciden."})
        try:
            validate_password(attrs["new_password"], self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": exc.messages}) from exc
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        return user


class ResetPasswordRequestSerializer(serializers.Serializer):
    """Solicitud de reset de contraseña (no requiere autenticación)."""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return value.lower().strip()
