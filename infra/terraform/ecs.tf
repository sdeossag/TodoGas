resource "aws_ecr_repository" "backend" {
  name = "${local.prefijo}-backend"
  # El deploy sube solo etiquetas con el SHA del commit, pero volver a correr
  # un workflow fallido vuelve a subir el mismo SHA: por eso mutable.
  image_tag_mutability = "MUTABLE"
  force_delete         = !var.proteger_datos

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Conservar las ultimas 10 imagenes"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_cloudwatch_log_group" "tarea" {
  for_each = toset(["api", "worker", "beat", "migrate"])

  name              = "/ecs/${local.prefijo}/${each.key}"
  retention_in_days = var.log_retencion_dias
}

resource "aws_ecs_cluster" "principal" {
  name = local.prefijo

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "principal" {
  cluster_name       = aws_ecs_cluster.principal.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
}

# ── Entorno de los contenedores (contrato: docs/infra/VARIABLES.md) ──────────
locals {
  # La imagen real la pone el deploy (registra una revision nueva con el SHA).
  # Esta etiqueta solo existe para crear la primera definicion.
  imagen_inicial = "${aws_ecr_repository.backend.repository_url}:inicial"

  env_base = {
    DJANGO_SETTINGS_MODULE    = "config.settings.production"
    DB_NAME                   = aws_db_instance.principal.db_name
    DB_USER                   = aws_db_instance.principal.username
    DB_HOST                   = aws_db_instance.principal.address
    DB_PORT                   = tostring(aws_db_instance.principal.port)
    DB_SSLMODE                = "require"
    DB_CONN_MAX_AGE           = "60"
    DJANGO_ALLOWED_HOSTS      = local.dominio_api
    FRONTEND_URL              = "https://${var.dominio}"
    BACKEND_URL               = "https://${local.dominio_api}"
    TRUSTED_PROXY_COUNT       = "1"
    AWS_STORAGE_BUCKET_NAME   = aws_s3_bucket.evidencia.bucket
    AWS_S3_REGION_NAME        = var.region
    AWS_REGION                = var.region
    CELERY_BROKER             = var.cola
    SENTRY_ENVIRONMENT        = var.entorno == "prod" ? "production" : var.entorno
    SENTRY_TRACES_SAMPLE_RATE = "0"
    EMAIL_BACKEND             = "django_ses.SESBackend"
    AWS_SES_REGION_NAME       = var.region
    DEFAULT_FROM_EMAIL        = local.correo_from
    AWS_SES_CONFIGURATION_SET = aws_sesv2_configuration_set.principal.configuration_set_name
    GUNICORN_WORKERS          = "2"
    GUNICORN_THREADS          = "4"
    GUNICORN_TIMEOUT          = "60"
  }

  env_broker = local.usa_sqs ? {
    CELERY_SQS_QUEUE_URL = one(aws_sqs_queue.celery[*].url)
    } : {
    REDIS_URL = "redis://${one(aws_elasticache_replication_group.principal[*].primary_endpoint_address)}:6379/0"
  }

  entorno_contenedor = [
    for k, v in merge(local.env_base, local.env_broker) : { name = k, value = v }
  ]

  secretos_contenedor = [
    { name = "SECRET_KEY", valueFrom = aws_ssm_parameter.secret_key.arn },
    { name = "DB_PASSWORD", valueFrom = aws_ssm_parameter.db_password.arn },
    { name = "GOOGLE_MAPS_API_KEY", valueFrom = aws_ssm_parameter.google_maps_api_key.arn },
    { name = "SENTRY_DSN", valueFrom = aws_ssm_parameter.sentry_dsn.arn },
  ]

  # name es el nombre del contenedor y del grupo de logs.
  contenedores = {
    api = {
      name    = "api"
      command = null # el CMD de la imagen: gunicorn con gunicorn.conf.py
      puertos = [{ containerPort = 8000, protocol = "tcp" }]
      parar   = 30
    }
    worker = {
      name    = "worker"
      command = ["celery", "-A", "config", "worker", "-l", "info", "--concurrency", "2"]
      puertos = []
      parar   = 120 # el maximo de Fargate: deja terminar el acta que se esta generando
    }
    beat = {
      name    = "beat"
      command = ["celery", "-A", "config", "beat", "-l", "info"]
      puertos = []
      parar   = 30
    }
    migrate = {
      name    = "migrate"
      command = ["sh", "-c", "python manage.py migrate --noinput && python manage.py createcachetable"]
      puertos = []
      parar   = 30
    }
  }

  definiciones = {
    for k, c in local.contenedores : k => merge(
      {
        name         = c.name
        image        = local.imagen_inicial
        essential    = true
        portMappings = c.puertos
        stopTimeout  = c.parar
        environment  = local.entorno_contenedor
        secrets      = local.secretos_contenedor
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            "awslogs-group"         = aws_cloudwatch_log_group.tarea[k].name
            "awslogs-region"        = var.region
            "awslogs-stream-prefix" = c.name
          }
        }
      },
      c.command == null ? {} : { command = c.command }
    )
  }
}

# ── Definiciones de tarea ────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "api" {
  family                   = "${local.prefijo}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ejecucion.arn
  task_role_arn            = aws_iam_role.tarea.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([local.definiciones["api"]])
}

# Dos contenedores en la misma tarea: el worker y el beat. Beat debe ser uno
# solo, asi que el servicio tiene desired_count 1 fijo y nunca dos tareas a la vez.
resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.prefijo}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 2048
  execution_role_arn       = aws_iam_role.ejecucion.arn
  task_role_arn            = aws_iam_role.tarea.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([local.definiciones["worker"], local.definiciones["beat"]])
}

# Tarea de una vez: el deploy la corre antes de actualizar los servicios.
resource "aws_ecs_task_definition" "migrate" {
  family                   = "${local.prefijo}-migrate"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ejecucion.arn
  task_role_arn            = aws_iam_role.tarea.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([local.definiciones["migrate"]])
}

# ── Servicios ────────────────────────────────────────────────────────────────
# El deploy de GitHub registra revisiones nuevas de la definicion y actualiza el
# servicio: Terraform no debe volver atras (ignore_changes en task_definition).
resource "aws_ecs_service" "api" {
  name            = "${local.prefijo}-api"
  cluster         = aws_ecs_cluster.principal.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }

  health_check_grace_period_seconds = 60

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.publica[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.https, aws_ecs_cluster_capacity_providers.principal]

  lifecycle {
    ignore_changes = [task_definition]
  }
}

resource "aws_ecs_service" "worker" {
  name            = "${local.prefijo}-worker"
  cluster         = aws_ecs_cluster.principal.id
  task_definition = aws_ecs_task_definition.worker.arn

  # Fijo en 1: el beat dentro de la tarea no puede duplicarse.
  desired_count = 1

  # Al desplegar, para la tarea vieja antes de arrancar la nueva (nunca dos beat).
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  capacity_provider_strategy {
    capacity_provider = var.worker_en_spot ? "FARGATE_SPOT" : "FARGATE"
    weight            = 1
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.publica[*].id
    security_groups  = [aws_security_group.worker.id]
    assign_public_ip = true
  }

  depends_on = [aws_ecs_cluster_capacity_providers.principal]

  lifecycle {
    ignore_changes = [task_definition]
  }
}
