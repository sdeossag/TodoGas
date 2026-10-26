resource "aws_sns_topic" "alertas" {
  name = "${local.prefijo}-alertas"
}

# El destinatario recibe un correo de AWS y debe confirmar la suscripcion.
resource "aws_sns_topic_subscription" "correo" {
  topic_arn = aws_sns_topic.alertas.arn
  protocol  = "email"
  endpoint  = var.correo_alertas
}

locals {
  accion_alarma = [aws_sns_topic.alertas.arn]
}

# ── ALB ──────────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "alb_sin_hosts_sanos" {
  alarm_name          = "${local.prefijo}-alb-sin-hosts-sanos"
  alarm_description   = "La API no tiene ninguna tarea sana detras del ALB desde hace 3 minutos."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HealthyHostCount"
  statistic           = "Minimum"
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  period              = 60
  evaluation_periods  = 3
  treat_missing_data  = "breaching"

  dimensions = {
    LoadBalancer = aws_lb.api.arn_suffix
    TargetGroup  = aws_lb_target_group.api.arn_suffix
  }

  alarm_actions = local.accion_alarma
  ok_actions    = local.accion_alarma
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${local.prefijo}-alb-5xx"
  alarm_description   = "10 o mas errores 5xx en 5 minutos (de la app o del propio ALB)."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 10
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"

  metric_query {
    id          = "total"
    expression  = "FILL(app, 0) + FILL(alb, 0)"
    label       = "5xx"
    return_data = true
  }

  metric_query {
    id = "app"

    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_Target_5XX_Count"
      stat        = "Sum"
      period      = 300

      dimensions = {
        LoadBalancer = aws_lb.api.arn_suffix
      }
    }
  }

  metric_query {
    id = "alb"

    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_ELB_5XX_Count"
      stat        = "Sum"
      period      = 300

      dimensions = {
        LoadBalancer = aws_lb.api.arn_suffix
      }
    }
  }

  alarm_actions = local.accion_alarma
  ok_actions    = local.accion_alarma
}

# ── RDS ──────────────────────────────────────────────────────────────────────
locals {
  rds_dimensiones = { DBInstanceIdentifier = aws_db_instance.principal.identifier }

  alarmas_rds = {
    cpu = {
      metrica     = "CPUUtilization"
      operador    = "GreaterThanThreshold"
      umbral      = 80
      periodos    = 3
      descripcion = "CPU de la base por encima de 80 % durante 15 minutos."
    }
    creditos = {
      metrica     = "CPUCreditBalance"
      operador    = "LessThanThreshold"
      umbral      = 30
      periodos    = 1
      descripcion = "Quedan menos de 30 creditos de CPU (la t4g se frena sin creditos)."
    }
    disco = {
      metrica     = "FreeStorageSpace"
      operador    = "LessThanThreshold"
      umbral      = 2 * 1024 * 1024 * 1024
      periodos    = 1
      descripcion = "Menos de 2 GB libres en el disco de la base."
    }
    memoria = {
      metrica     = "FreeableMemory"
      operador    = "LessThanThreshold"
      umbral      = 100 * 1024 * 1024
      periodos    = 3
      descripcion = "Menos de 100 MB de memoria libre en la base durante 15 minutos."
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "rds" {
  for_each = local.alarmas_rds

  alarm_name          = "${local.prefijo}-rds-${each.key}"
  alarm_description   = each.value.descripcion
  namespace           = "AWS/RDS"
  metric_name         = each.value.metrica
  statistic           = "Average"
  comparison_operator = each.value.operador
  threshold           = each.value.umbral
  period              = 300
  evaluation_periods  = each.value.periodos
  treat_missing_data  = "missing"
  dimensions          = local.rds_dimensiones

  alarm_actions = local.accion_alarma
  ok_actions    = local.accion_alarma
}

# ── SQS (solo con cola = "sqs") ──────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "sqs_dlq" {
  count = local.usa_sqs ? 1 : 0

  alarm_name          = "${local.prefijo}-sqs-dlq-con-mensajes"
  alarm_description   = "Hay mensajes en la cola de fallos: una tarea de Celery fallo 5 veces."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  period              = 300
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"

  dimensions = { QueueName = aws_sqs_queue.celery_dlq[0].name }

  alarm_actions = local.accion_alarma
  ok_actions    = local.accion_alarma
}

resource "aws_cloudwatch_metric_alarm" "sqs_edad" {
  count = local.usa_sqs ? 1 : 0

  alarm_name          = "${local.prefijo}-sqs-mensaje-viejo"
  alarm_description   = "El mensaje mas viejo de la cola lleva mas de 15 minutos: el worker no esta procesando."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateAgeOfOldestMessage"
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 900
  period              = 300
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"

  dimensions = { QueueName = aws_sqs_queue.celery[0].name }

  alarm_actions = local.accion_alarma
  ok_actions    = local.accion_alarma
}

# ── SES: reputacion de la cuenta ─────────────────────────────────────────────
# AWS pone la cuenta en revision al 10 % de rebotes y 0,5 % de quejas; estos
# umbrales avisan antes (5 % y 0,1 %).
resource "aws_cloudwatch_metric_alarm" "ses_rebotes" {
  alarm_name          = "${local.prefijo}-ses-rebotes"
  alarm_description   = "La tasa de rebote de SES supera 5 %."
  namespace           = "AWS/SES"
  metric_name         = "Reputation.BounceRate"
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0.05
  period              = 3600
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"

  alarm_actions = local.accion_alarma
  ok_actions    = local.accion_alarma
}

resource "aws_cloudwatch_metric_alarm" "ses_quejas" {
  alarm_name          = "${local.prefijo}-ses-quejas"
  alarm_description   = "La tasa de quejas de SES supera 0,1 %."
  namespace           = "AWS/SES"
  metric_name         = "Reputation.ComplaintRate"
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0.001
  period              = 3600
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"

  alarm_actions = local.accion_alarma
  ok_actions    = local.accion_alarma
}

# ── Presupuesto (de toda la cuenta; solo en prod) ────────────────────────────
resource "aws_budgets_budget" "mensual" {
  count = var.crear_presupuesto ? 1 : 0

  name         = "${local.prefijo}-mensual"
  budget_type  = "COST"
  limit_amount = tostring(var.presupuesto_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.correo_alertas]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.correo_alertas]
  }
}
