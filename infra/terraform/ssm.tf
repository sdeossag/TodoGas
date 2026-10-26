# Parameter Store (SecureString, clave aws/ssm) en vez de Secrets Manager: sin
# costo por secreto. ECS los inyecta como `secrets` al arrancar la tarea.

resource "random_password" "db" {
  length  = 32
  special = false # va en URLs y en comandos de shell: solo letras y numeros
}

resource "random_password" "secret_key" {
  length  = 64
  special = false
}

resource "aws_ssm_parameter" "secret_key" {
  name        = "/${local.prefijo}/SECRET_KEY"
  description = "SECRET_KEY de Django"
  type        = "SecureString"
  value       = random_password.secret_key.result
}

resource "aws_ssm_parameter" "db_password" {
  name        = "/${local.prefijo}/DB_PASSWORD"
  description = "Contrasena del usuario de la base de datos"
  type        = "SecureString"
  value       = random_password.db.result
}

# Los dos siguientes se llenan a mano (ver infra/README.md). Parameter Store no
# admite valores vacios, asi que llevan un valor de relleno que la app tolera:
# - GOOGLE_MAPS_API_KEY: con una clave invalida Google no responde y la app
#   sigue sin mapas ni geocodificacion.
# - SENTRY_DSN: el backend trata "sin-configurar" como vacio
#   (config_opcional en settings/base.py), asi que Sentry queda apagado.
resource "aws_ssm_parameter" "google_maps_api_key" {
  name        = "/${local.prefijo}/GOOGLE_MAPS_API_KEY"
  description = "Llenar a mano con la clave de Google Maps"
  type        = "SecureString"
  value       = "sin-configurar"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "sentry_dsn" {
  name        = "/${local.prefijo}/SENTRY_DSN"
  description = "Llenar a mano con el DSN de Sentry"
  type        = "SecureString"
  value       = "sin-configurar"

  lifecycle {
    ignore_changes = [value]
  }
}
