entorno = "prod"
dominio = "cmms.todogas.com.co"

# Decisiones a confirmar con el cliente.
cola           = "sqs"
worker_en_spot = true

object_lock_mode  = "GOVERNANCE"
object_lock_anios = 5

multi_az        = false
proteger_datos  = true
presupuesto_usd = 90

correo_alertas = "CAMBIAR@todogas.com.co"
dmarc_rua      = "mailto:dmarc@todogas.com.co"
