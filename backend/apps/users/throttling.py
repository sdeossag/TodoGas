from django.core.cache import cache

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 60 * 30  # 30 minutos


class LoginRateThrottle:
    """
    Bloquea una cuenta tras MAX_ATTEMPTS intentos fallidos de login.
    Usa Redis (Django cache) con clave: login_attempts_{email}.
    El bloqueo dura LOCKOUT_SECONDS segundos.
    """

    @staticmethod
    def _key(email: str) -> str:
        return f"login_attempts_{email.lower().strip()}"

    def is_blocked(self, email: str) -> bool:
        return cache.get(self._key(email), 0) >= MAX_ATTEMPTS

    def register_failed_attempt(self, email: str) -> int:
        key = self._key(email)
        attempts = cache.get(key, 0) + 1
        cache.set(key, attempts, LOCKOUT_SECONDS)
        return attempts

    def reset_attempts(self, email: str) -> None:
        cache.delete(self._key(email))

    def remaining_attempts(self, email: str) -> int:
        return max(0, MAX_ATTEMPTS - cache.get(self._key(email), 0))
