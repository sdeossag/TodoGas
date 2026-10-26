data "aws_caller_identity" "actual" {}

data "aws_availability_zones" "disponibles" {
  state = "available"

  # Solo zonas normales de la region (sin Local Zones ni Wavelength).
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

locals {
  prefijo     = "todogas-${var.entorno}"
  dominio_api = "api.${var.dominio}"
  correo_from = "TodoGas CMMS <notificaciones@${var.dominio}>"
  cuenta_id   = data.aws_caller_identity.actual.account_id

  usa_sqs   = var.cola == "sqs"
  usa_redis = var.cola == "redis"

  zonas = slice(data.aws_availability_zones.disponibles.names, 0, 2)
}
