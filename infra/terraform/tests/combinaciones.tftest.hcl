# Prueba sin cuenta de AWS: el provider es simulado (mock_provider), asi que
# `terraform test` evalua de verdad las expresiones condicionales (count,
# dynamic, ?:) de las dos combinaciones de los interruptores y de cada .tfvars.
#
#   terraform test -var-file=prod.tfvars
#   terraform test -var-file=staging.tfvars
#
# No toca AWS ni pide credenciales.

mock_provider "aws" {
  mock_data "aws_availability_zones" {
    defaults = {
      names = ["us-east-1a", "us-east-1b", "us-east-1c"]
    }
  }

  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }

  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }

  mock_data "aws_iam_openid_connect_provider" {
    defaults = {
      arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
    }
  }

  mock_data "aws_cloudfront_cache_policy" {
    defaults = {
      id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
    }
  }

  mock_data "aws_cloudfront_response_headers_policy" {
    defaults = {
      id = "67f7725c-6f97-4210-82d7-5512b31e9d03"
    }
  }

  # El provider real conoce estos nombres al apply; el simulado necesita datos.
  mock_resource "aws_acm_certificate" {
    defaults = {
      arn = "arn:aws:acm:us-east-1:123456789012:certificate/x"
      domain_validation_options = [
        {
          domain_name           = "cmms.todogas.com.co"
          resource_record_name  = "_a.cmms.todogas.com.co."
          resource_record_type  = "CNAME"
          resource_record_value = "_a.acm-validations.aws."
        },
        {
          domain_name           = "api.cmms.todogas.com.co"
          resource_record_name  = "_b.api.cmms.todogas.com.co."
          resource_record_type  = "CNAME"
          resource_record_value = "_b.acm-validations.aws."
        },
        {
          domain_name           = "cmms-staging.todogas.com.co"
          resource_record_name  = "_c.cmms-staging.todogas.com.co."
          resource_record_type  = "CNAME"
          resource_record_value = "_c.acm-validations.aws."
        },
        {
          domain_name           = "api.cmms-staging.todogas.com.co"
          resource_record_name  = "_d.api.cmms-staging.todogas.com.co."
          resource_record_type  = "CNAME"
          resource_record_value = "_d.acm-validations.aws."
        },
      ]
    }
  }

  mock_resource "aws_lb" {
    defaults = {
      arn = "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/x/1"
    }
  }

  mock_resource "aws_lb_target_group" {
    defaults = {
      arn = "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/x/1"
    }
  }

  mock_resource "aws_iam_role" {
    defaults = {
      arn = "arn:aws:iam::123456789012:role/x"
    }
  }

  mock_resource "aws_ecr_repository" {
    defaults = {
      arn = "arn:aws:ecr:us-east-1:123456789012:repository/x"
    }
  }

  mock_resource "aws_ecs_cluster" {
    defaults = {
      arn = "arn:aws:ecs:us-east-1:123456789012:cluster/x"
    }
  }

  mock_resource "aws_cloudwatch_log_group" {
    defaults = {
      arn = "arn:aws:logs:us-east-1:123456789012:log-group:x"
    }
  }

  mock_resource "aws_ssm_parameter" {
    defaults = {
      arn = "arn:aws:ssm:us-east-1:123456789012:parameter/x"
    }
  }

  mock_resource "aws_s3_bucket" {
    defaults = {
      arn = "arn:aws:s3:::x"
    }
  }

  mock_resource "aws_cloudfront_distribution" {
    defaults = {
      arn = "arn:aws:cloudfront::123456789012:distribution/E1"
    }
  }

  mock_resource "aws_sesv2_email_identity" {
    defaults = {
      arn = "arn:aws:ses:us-east-1:123456789012:identity/x"
      dkim_signing_attributes = {
        tokens                        = ["t1", "t2", "t3"]
        next_signing_key_length       = "RSA_2048_BIT"
        current_signing_key_length    = "RSA_2048_BIT"
        domain_signing_private_key    = null
        domain_signing_selector       = null
        last_key_generation_timestamp = "2024-01-01T00:00:00Z"
        signing_attributes_origin     = "AWS_SES"
        status                        = "SUCCESS"
      }
    }
  }

  mock_resource "aws_sesv2_configuration_set" {
    defaults = {
      arn = "arn:aws:ses:us-east-1:123456789012:configuration-set/x"
    }
  }

  mock_resource "aws_sns_topic" {
    defaults = {
      arn = "arn:aws:sns:us-east-1:123456789012:x"
    }
  }

  mock_resource "aws_iam_openid_connect_provider" {
    defaults = {
      arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
    }
  }

  mock_resource "aws_db_instance" {
    defaults = {
      arn = "arn:aws:rds:us-east-1:123456789012:db:x"
    }
  }

  mock_resource "aws_acm_certificate_validation" {
    defaults = {
      certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/x"
    }
  }

  mock_resource "aws_ecs_service" {
    defaults = {
      id = "arn:aws:ecs:us-east-1:123456789012:service/cluster/servicio"
    }
  }

  mock_resource "aws_sqs_queue" {
    defaults = {
      arn = "arn:aws:sqs:us-east-1:123456789012:cola"
      url = "https://sqs.us-east-1.amazonaws.com/123456789012/cola"
    }
  }
}

mock_provider "random" {}

run "sqs_con_spot" {
  command = apply

  variables {
    cola           = "sqs"
    worker_en_spot = true
  }

  assert {
    condition     = length(aws_sqs_queue.celery) == 1 && length(aws_sqs_queue.celery_dlq) == 1
    error_message = "Con cola=sqs deben existir la cola y su DLQ."
  }

  assert {
    condition     = length(aws_elasticache_replication_group.principal) == 0 && length(aws_security_group.redis) == 0
    error_message = "Con cola=sqs no debe haber Redis."
  }

  assert {
    condition     = length(aws_cloudwatch_metric_alarm.sqs_dlq) == 1 && length(aws_cloudwatch_metric_alarm.sqs_edad) == 1
    error_message = "Con cola=sqs deben existir las alarmas de SQS."
  }

  assert {
    condition     = one(aws_ecs_service.worker.capacity_provider_strategy).capacity_provider == "FARGATE_SPOT"
    error_message = "worker_en_spot=true debe usar FARGATE_SPOT."
  }

  assert {
    condition     = strcontains(aws_ecs_task_definition.worker.container_definitions, "CELERY_SQS_QUEUE_URL") && !strcontains(aws_ecs_task_definition.worker.container_definitions, "REDIS_URL")
    error_message = "Con sqs el entorno lleva CELERY_SQS_QUEUE_URL y no REDIS_URL."
  }

  assert {
    condition     = strcontains(aws_ecs_task_definition.worker.container_definitions, "\"name\":\"beat\"") && strcontains(aws_ecs_task_definition.worker.container_definitions, "\"name\":\"worker\"")
    error_message = "La tarea del worker lleva los contenedores worker y beat."
  }

  assert {
    condition     = aws_ecs_service.worker.desired_count == 1 && aws_ecs_service.worker.deployment_maximum_percent == 100
    error_message = "El beat es uno: desired_count 1 y nunca dos tareas a la vez."
  }
}

run "redis_sin_spot" {
  command = apply

  variables {
    cola           = "redis"
    worker_en_spot = false
  }

  assert {
    condition     = length(aws_sqs_queue.celery) == 0 && length(aws_sqs_queue.celery_dlq) == 0
    error_message = "Con cola=redis no debe haber SQS."
  }

  assert {
    condition     = length(aws_elasticache_replication_group.principal) == 1 && length(aws_security_group.redis) == 1
    error_message = "Con cola=redis debe existir Redis."
  }

  assert {
    condition     = length(aws_cloudwatch_metric_alarm.sqs_dlq) == 0 && length(aws_cloudwatch_metric_alarm.sqs_edad) == 0
    error_message = "Con cola=redis no hay alarmas de SQS."
  }

  assert {
    condition     = one(aws_ecs_service.worker.capacity_provider_strategy).capacity_provider == "FARGATE"
    error_message = "worker_en_spot=false debe usar FARGATE."
  }

  assert {
    condition     = strcontains(aws_ecs_task_definition.worker.container_definitions, "REDIS_URL") && !strcontains(aws_ecs_task_definition.worker.container_definitions, "CELERY_SQS_QUEUE_URL")
    error_message = "Con redis el entorno lleva REDIS_URL y no CELERY_SQS_QUEUE_URL."
  }
}

# Dependen del .tfvars que se pase con -var-file.
run "segun_el_entorno" {
  command = apply

  assert {
    condition     = aws_db_instance.principal.deletion_protection == var.proteger_datos && aws_db_instance.principal.skip_final_snapshot == !var.proteger_datos
    error_message = "La proteccion de RDS sigue a proteger_datos."
  }

  assert {
    condition     = length(aws_iam_openid_connect_provider.github) == (var.crear_proveedor_oidc ? 1 : 0)
    error_message = "El proveedor OIDC sigue a crear_proveedor_oidc."
  }

  assert {
    condition     = length(aws_budgets_budget.mensual) == (var.crear_presupuesto ? 1 : 0)
    error_message = "El presupuesto sigue a crear_presupuesto."
  }

  assert {
    condition     = aws_s3_bucket.evidencia.object_lock_enabled == true
    error_message = "El bucket de evidencia debe nacer con Object Lock."
  }

  assert {
    condition     = one(one(aws_s3_bucket_object_lock_configuration.evidencia.rule).default_retention).years == var.object_lock_anios
    error_message = "La retencion sigue a object_lock_anios."
  }
}
