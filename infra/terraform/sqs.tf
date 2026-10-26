# Cola de Celery cuando cola = "sqs". El visibility timeout (900 s) es el mismo
# que SQS_VISIBILITY_TIMEOUT de backend/config/broker.py.

resource "aws_sqs_queue" "celery_dlq" {
  count = local.usa_sqs ? 1 : 0

  name                      = "${local.prefijo}-celery-dlq"
  message_retention_seconds = 14 * 24 * 3600
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "celery" {
  count = local.usa_sqs ? 1 : 0

  name                       = "${local.prefijo}-celery"
  visibility_timeout_seconds = 900
  message_retention_seconds  = 4 * 24 * 3600
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.celery_dlq[0].arn
    maxReceiveCount     = 5
  })
}

resource "aws_sqs_queue_redrive_allow_policy" "celery_dlq" {
  count = local.usa_sqs ? 1 : 0

  queue_url = aws_sqs_queue.celery_dlq[0].id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.celery[0].arn]
  })
}
