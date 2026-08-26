import secrets
import string

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .emails import send_password_reset_email, send_welcome_email
from .models import User
from .permissions import IsAdmin, IsAdminOrSup, IsOwnerOrAdmin
from .serializers import (
    ChangePasswordSerializer,
    ResetPasswordRequestSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from .throttling import LoginRateThrottle


def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        # Garantiza que cumpla StrongPasswordValidator
        if (
            any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%" for c in pwd)
        ):
            return pwd


_throttle = LoginRateThrottle()


class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: {email, password}
    Devuelve: {access, refresh, user}
    """

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").lower().strip()
        password = request.data.get("password", "")

        if not email or not password:
            return Response(
                {"detail": "Email y contraseña son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if _throttle.is_blocked(email):
            return Response(
                {"detail": "Cuenta bloqueada temporalmente. Intenta de nuevo en 30 minutos."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            _throttle.register_failed_attempt(email)
            return Response({"detail": "Credenciales inválidas."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            remaining = _throttle.register_failed_attempt(email)
            detail = f"Credenciales inválidas. Intentos restantes: {remaining}."
            return Response({"detail": detail}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"detail": "Cuenta desactivada."}, status=status.HTTP_403_FORBIDDEN)

        _throttle.reset_attempts(email)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Body: {refresh}
    Invalida el refresh token en la blacklist.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        token_str = request.data.get("refresh")
        if not token_str:
            return Response({"detail": "Se requiere el refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(token_str)
            token.blacklist()
        except TokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Body: {current_password, new_password, new_password_confirm}
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({"detail": "Contraseña actualizada correctamente."}, status=status.HTTP_200_OK)


class MeView(APIView):
    """GET /api/auth/me/ — datos del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD de usuarios.
    - list / retrieve: ADMIN o SUP
    - create / update / destroy: solo ADMIN
    - deactivate: ADMIN
    - reset_password: ADMIN
    """

    queryset = User.objects.select_related("hospital").order_by("last_name", "first_name")
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAdminOrSup()]
        if self.action in ("deactivate", "reset_password", "create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        user = serializer.save()
        # La contraseña ya fue seteada en UserCreateSerializer.create()
        # Aquí enviamos el email de bienvenida (el campo 'password' ya no está disponible,
        # así que el admin debe conocerla antes de invocar la API o usamos temp_password separado).
        # Para el flujo API: el admin envía la contraseña en el body y la API la reenvía por email.
        password = self.request.data.get("password", "")
        if password:
            try:
                send_welcome_email(user, password)
            except Exception:
                pass  # No falla si el email falla

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        """POST /api/users/{id}/deactivate/ — desactiva un usuario."""
        user = self.get_object()
        if user == request.user:
            return Response({"detail": "No puedes desactivarte a ti mismo."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        return Response({"detail": f"Usuario {user.email} desactivado."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        """POST /api/users/{id}/reset-password/ — genera contraseña temporal y la envía por email."""
        user = self.get_object()
        temp_password = _generate_temp_password()
        try:
            validate_password(temp_password, user)
        except DjangoValidationError:
            temp_password = _generate_temp_password(14)
        user.set_password(temp_password)
        user.must_change_password = True
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        try:
            send_password_reset_email(user, temp_password)
        except Exception:
            pass
        return Response({"detail": f"Contraseña restablecida. Email enviado a {user.email}."}, status=status.HTTP_200_OK)
