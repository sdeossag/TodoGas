# Staging se crea y se destruye cuando hace falta (ver infra/README.md).
entorno = "staging"
dominio = "cmms-staging.todogas.com.co"

cola           = "sqs"
worker_en_spot = true

# Retencion minima y datos descartables: permite terraform destroy.
object_lock_mode  = "GOVERNANCE"
object_lock_anios = 1

multi_az              = false
proteger_datos        = false
backup_retention_dias = 1
log_retencion_dias    = 7

# Estos dos son de la cuenta, no del entorno: los crea prod.
crear_proveedor_oidc = false
crear_presupuesto    = false

github_environment = "staging"

correo_alertas = "CAMBIAR@todogas.com.co"
dmarc_rua      = "mailto:dmarc@todogas.com.co"
