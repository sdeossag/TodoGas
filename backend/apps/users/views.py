import logging
import secrets
import string

from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.services import LoginOutcome, log_login_attempt

from . import permisos, privacy
from .emails import (
    send_password_reset_email,
    send_self_service_reset_email,
    send_welcome_email,
)
from .models import User
from .permissions import IsAdmin, TienePermiso
from .serializers import (
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
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


logger = logging.getLogger(__name__)

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

        # Cada desenlace se audita aqui y no en AuditMiddleware: la peticion de
        # login llega anonima, asi que el middleware no puede saber quien entro.
        if not email or not password:
            log_login_attempt(request, email=email, outcome=LoginOutcome.INCOMPLETE)
            return Response(
                {"detail": "Email y contraseña son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if _throttle.is_blocked(email):
            log_login_attempt(request, email=email, outcome=LoginOutcome.THROTTLED)
            return Response(
                {"detail": "Cuenta bloqueada temporalmente. Intenta de nuevo en 30 minutos."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            _throttle.register_failed_attempt(email)
            log_login_attempt(request, email=email, outcome=LoginOutcome.UNKNOWN_EMAIL)
            return Response({"detail": "Credenciales inválidas."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            remaining = _throttle.register_failed_attempt(email)
            log_login_attempt(
                request, email=email, outcome=LoginOutcome.BAD_CREDENTIALS, target=user
            )
            detail = f"Credenciales inválidas. Intentos restantes: {remaining}."
            return Response({"detail": detail}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            log_login_attempt(
                request, email=email, outcome=LoginOutcome.INACTIVE, target=user
            )
            return Response({"detail": "Cuenta desactivada."}, status=status.HTTP_403_FORBIDDEN)

        _throttle.reset_attempts(email)
        log_login_attempt(
            request, email=email, outcome=LoginOutcome.SUCCESS, user=user
        )
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


PASSWORD_RESET_SENT = (
    "Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña."
)
PASSWORD_RESET_INVALID = (
    "El enlace no es válido o ya venció. Solicita uno nuevo desde «¿Olvidaste tu contraseña?»."
)


class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password-reset/
    Body: {email}
    Responde siempre 200 con el mismo mensaje, exista o no la cuenta, para no
    revelar qué correos están registrados.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = ResetPasswordRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user and user.has_usable_password() and user.deactivated_at is None:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                try:
                    send_self_service_reset_email(user, uid, token)
                except Exception:
                    # Mismo 200 aunque falle el correo: otra respuesta delataría la cuenta.
                    logger.exception("No se pudo enviar el correo de restablecimiento")
        return Response({"detail": PASSWORD_RESET_SENT}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/password-reset/confirm/
    Body: {uid, token, new_password}
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_confirm"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data

        invalid = Response({"detail": PASSWORD_RESET_INVALID}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(data["uid"])))
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, DjangoValidationError):
            return invalid
        if (
            not user.is_active
            or user.deactivated_at is not None
            or not default_token_generator.check_token(user, data["token"])
        ):
            return invalid

        try:
            validate_password(data["new_password"], user)
        except DjangoValidationError as exc:
            return Response({"new_password": exc.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        _throttle.reset_attempts(user.email)
        # La auditoria queda en AuditMiddleware, que ya registra todo POST bajo /api/auth/.
        return Response(
            {"detail": "Contraseña actualizada. Ya puedes iniciar sesión."},
            status=status.HTTP_200_OK,
        )


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

    queryset = (
        User.objects.select_related("hospital", "scope_node")
        .prefetch_related("permisos_extra")
        .order_by("last_name", "first_name")
    )
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            # Quien asigna OT necesita ver a quien puede ejecutarlas; admin y
            # supervisor lo traen por rol, a un tecnico se le suma con el permiso.
            return [TienePermiso("ot.asignar", "ot.crear_manual")()]
        if self.action in (
            "deactivate", "reset_password", "create", "update", "partial_update", "destroy",
            "permissions", "permissions_catalog", "personal_data_of", "anonymize",
        ):
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

    @action(detail=False, methods=["get"], url_path="permissions-catalog")
    def permissions_catalog(self, request):
        """GET /api/users/permissions-catalog/ — las casillas de permisos adicionales."""
        return Response(permisos.catalogo_para_api())

    @action(detail=False, methods=["get", "post"], url_path="me/privacy-consent")
    def privacy_consent(self, request):
        """
        GET /api/users/me/privacy-consent/ — {required, version, accepted_at, policy_url}.
        POST registra la aceptacion de la version vigente del aviso de privacidad.
        """
        if request.method == "POST":
            return Response(privacy.accept_consent(request.user, request), status=status.HTTP_200_OK)
        return Response(privacy.consent_status(request.user))

    @action(detail=False, methods=["get"], url_path="me/personal-data")
    def personal_data(self, request):
        """GET /api/users/me/personal-data/ — los datos personales del propio usuario."""
        return Response(privacy.personal_data(request.user))

    @action(detail=True, methods=["get"], url_path="personal-data")
    def personal_data_of(self, request, pk=None):
        """GET /api/users/{id}/personal-data/ — ADMIN exporta los datos de otro usuario."""
        target = self.get_object()
        privacy.log_export(target, request.user, request)
        return Response(privacy.personal_data(target))

    @action(detail=True, methods=["post"], url_path="anonymize")
    def anonymize(self, request, pk=None):
        """POST /api/users/{id}/anonymize/ — solo ADMIN, cuenta inactiva hace mas de 2 anos."""
        target = self.get_object()
        if target == request.user:
            return Response({"detail": "No puedes anonimizarte a ti mismo."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            privacy.anonymize(target, request.user, request)
        except privacy.AnonymizeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(User.objects.get(pk=target.pk)).data)

    @action(detail=True, methods=["get", "put"], url_path="permissions")
    def permissions(self, request, pk=None):
        """
        GET/PUT /api/users/{id}/permissions/ — permisos adicionales del usuario.
        PUT {"permisos_extra": [codigos]} los deja exactamente asi; lo que el rol
        ya trae no se guarda y una cuenta de hospital no puede recibir ninguno.
        """
        user = self.get_object()
        if request.method == "PUT":
            codigos = request.data.get("permisos_extra")
            if not isinstance(codigos, list):
                return Response(
                    {"permisos_extra": "Manda la lista de permisos."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                permisos.establecer(user, codigos, por=request.user, request=request)
            except ValueError as exc:
                return Response({"permisos_extra": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            user = User.objects.get(pk=user.pk)
        return Response({
            "permisos_extra": permisos.extras_de(user),
            "permisos": sorted(permisos.permisos_efectivos(user)),
        })

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        """POST /api/users/{id}/deactivate/ — desactiva un usuario."""
        user = self.get_object()
        if user == request.user:
            return Response({"detail": "No puedes desactivarte a ti mismo."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.deactivated_at = timezone.now()
        user.save(update_fields=["is_active", "deactivated_at", "updated_at"])
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
