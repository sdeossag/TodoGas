variable "entorno" {
  description = "Nombre del entorno: prod o staging. Va en los nombres y en la etiqueta Entorno."
  type        = string

  validation {
    condition     = contains(["prod", "staging"], var.entorno)
    error_message = "entorno debe ser \"prod\" o \"staging\"."
  }
}

variable "region" {
  description = "Region de AWS."
  type        = string
  default     = "us-east-1"
}

variable "dominio" {
  description = "Subdominio delegado a Route 53. La web vive aqui y la API en api.<dominio>."
  type        = string
  default     = "cmms.todogas.com.co"
}

# ── Decisiones con el cliente ────────────────────────────────────────────────
variable "cola" {
  description = "Broker de Celery: \"sqs\" (barato) o \"redis\" (ElastiCache Valkey)."
  type        = string
  default     = "sqs"

  validation {
    condition     = contains(["sqs", "redis"], var.cola)
    error_message = "cola debe ser \"sqs\" o \"redis\"."
  }
}

variable "worker_en_spot" {
  description = "El worker (y el beat, que va en su tarea) corre en FARGATE_SPOT. AWS puede interrumpirlo con 2 minutos de aviso."
  type        = bool
  default     = true
}

variable "object_lock_mode" {
  description = "Modo de la retencion por defecto del bucket de evidencia: GOVERNANCE (se puede saltar con permiso especial) o COMPLIANCE (nadie, ni root, hasta que venza)."
  type        = string
  default     = "GOVERNANCE"

  validation {
    condition     = contains(["GOVERNANCE", "COMPLIANCE"], var.object_lock_mode)
    error_message = "object_lock_mode debe ser GOVERNANCE o COMPLIANCE."
  }
}

variable "object_lock_anios" {
  description = "Anios de retencion por defecto de cada objeto de evidencia. Confirmar con el sistema de calidad del cliente."
  type        = number
  default     = 5

  validation {
    condition     = var.object_lock_anios >= 1 && floor(var.object_lock_anios) == var.object_lock_anios
    error_message = "object_lock_anios debe ser un entero >= 1."
  }
}

# ── Base de datos ────────────────────────────────────────────────────────────
variable "multi_az" {
  description = "RDS con replica en otra zona (duplica el costo de la base)."
  type        = bool
  default     = false
}

variable "db_clase" {
  description = "Clase de instancia de RDS."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_almacenamiento_gb" {
  description = "Disco inicial de RDS (gp3)."
  type        = number
  default     = 20
}

variable "db_almacenamiento_max_gb" {
  description = "Tope del autoescalado del disco de RDS."
  type        = number
  default     = 100
}

variable "backup_retention_dias" {
  description = "Dias de respaldos automaticos de RDS."
  type        = number
  default     = 30
}

variable "proteger_datos" {
  description = "true = RDS con deletion_protection y snapshot final, ALB protegido, y el bucket de evidencia no se vacia al destruir. false solo para staging."
  type        = bool
  default     = true
}

# ── Operacion ────────────────────────────────────────────────────────────────
variable "log_retencion_dias" {
  description = "Retencion de los logs en CloudWatch."
  type        = number
  default     = 30
}

variable "vpc_cidr" {
  description = "CIDR de la VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "correo_alertas" {
  description = "Correo que recibe las alarmas (SNS) y los avisos del presupuesto. SNS le manda un correo de confirmacion."
  type        = string
}

variable "presupuesto_usd" {
  description = "Presupuesto mensual en USD (AWS Budgets)."
  type        = number
  default     = 90
}

variable "crear_presupuesto" {
  description = "Crea el presupuesto de AWS Budgets. Es de toda la cuenta: crearlo solo en prod."
  type        = bool
  default     = true
}

# ── Correo ───────────────────────────────────────────────────────────────────
variable "dmarc_rua" {
  description = "Direccion de los reportes agregados de DMARC, con mailto: (p. ej. mailto:dmarc@todogas.com.co)."
  type        = string
}

variable "dmarc_politica" {
  description = "Politica DMARC: none al empezar, luego quarantine y reject (ver docs/infra/SES.md)."
  type        = string
  default     = "none"

  validation {
    condition     = contains(["none", "quarantine", "reject"], var.dmarc_politica)
    error_message = "dmarc_politica debe ser none, quarantine o reject."
  }
}

# ── GitHub ───────────────────────────────────────────────────────────────────
variable "github_repo" {
  description = "Repositorio que puede desplegar (owner/nombre)."
  type        = string
  default     = "sdeossag/TodoGas"
}

variable "github_environment" {
  description = "Environment de GitHub que puede asumir el rol de despliegue. Restringirlo a la rama main en Settings > Environments."
  type        = string
  default     = "production"
}

variable "crear_proveedor_oidc" {
  description = "Crea el proveedor OIDC de GitHub. Solo existe uno por cuenta: en staging (misma cuenta) va en false."
  type        = bool
  default     = true
}
