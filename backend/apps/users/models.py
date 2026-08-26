import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


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
    Usuario del sistema. Usa email como login.
    Mapea a Fracttal: Recursos Humanos + sistema de cuentas.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        SUP = "SUP", "Supervisor"
        TEC = "TEC", "Técnico"
        CLI = "CLI", "Cliente externo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=5, choices=Role.choices, default=Role.TEC)
    employee_code = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Cédula o código de empleado. Fracttal: Código"
    )
    phone = models.CharField(max_length=20, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    must_change_password = models.BooleanField(
        default=False,
        help_text="Obliga al usuario a cambiar la contraseña en el próximo login."
    )

    hospital = models.ForeignKey(
        "assets.Hospital", on_delete=models.PROTECT,
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
