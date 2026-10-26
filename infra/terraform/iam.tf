locals {
  ssm_parametros = [
    aws_ssm_parameter.secret_key.arn,
    aws_ssm_parameter.db_password.arn,
    aws_ssm_parameter.google_maps_api_key.arn,
    aws_ssm_parameter.sentry_dsn.arn,
  ]

  ecs_assume = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = { "aws:SourceAccount" = local.cuenta_id }
      }
    }]
  })
}

# ── Rol de ejecucion: lo usa ECS para arrancar la tarea ──────────────────────
resource "aws_iam_role" "ejecucion" {
  name               = "${local.prefijo}-ecs-ejecucion"
  assume_role_policy = local.ecs_assume
}

data "aws_iam_policy_document" "ejecucion" {
  statement {
    sid       = "ECRToken"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "ECRPull"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
    ]
    resources = [aws_ecr_repository.backend.arn]
  }

  statement {
    sid     = "Logs"
    actions = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = [
      for g in aws_cloudwatch_log_group.tarea : "${g.arn}:*"
    ]
  }

  statement {
    sid       = "LeerParametros"
    actions   = ["ssm:GetParameters"]
    resources = local.ssm_parametros
  }
}

resource "aws_iam_role_policy" "ejecucion" {
  name   = "ejecucion"
  role   = aws_iam_role.ejecucion.id
  policy = data.aws_iam_policy_document.ejecucion.json
}

# ── Rol de tarea: lo que la app puede hacer en AWS ───────────────────────────
resource "aws_iam_role" "tarea" {
  name               = "${local.prefijo}-ecs-tarea"
  assume_role_policy = local.ecs_assume
}

data "aws_iam_policy_document" "tarea" {
  statement {
    sid       = "EvidenciaObjetos"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:GetObjectVersion"]
    resources = ["${aws_s3_bucket.evidencia.arn}/*"]
  }

  statement {
    sid       = "EvidenciaListar"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.evidencia.arn]
  }

  dynamic "statement" {
    for_each = local.usa_sqs ? [1] : []

    content {
      sid = "ColaCelery"
      actions = [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:ChangeMessageVisibility",
        "sqs:GetQueueAttributes",
      ]
      resources = [aws_sqs_queue.celery[0].arn]
    }
  }

  statement {
    sid     = "CorreoSES"
    actions = ["ses:SendRawEmail", "ses:SendEmail"]
    resources = [
      aws_sesv2_email_identity.dominio.arn,
      aws_sesv2_configuration_set.principal.arn,
    ]
  }
}

resource "aws_iam_role_policy" "tarea" {
  name   = "tarea"
  role   = aws_iam_role.tarea.id
  policy = data.aws_iam_policy_document.tarea.json
}

# ── GitHub Actions por OIDC ──────────────────────────────────────────────────
resource "aws_iam_openid_connect_provider" "github" {
  count = var.crear_proveedor_oidc ? 1 : 0

  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  # AWS ya valida la cadena de confianza de GitHub; el valor se exige por formato.
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

data "aws_iam_openid_connect_provider" "github" {
  count = var.crear_proveedor_oidc ? 0 : 1

  url = "https://token.actions.githubusercontent.com"
}

locals {
  oidc_arn = var.crear_proveedor_oidc ? aws_iam_openid_connect_provider.github[0].arn : data.aws_iam_openid_connect_provider.github[0].arn
}

# Solo el repositorio, solo jobs del environment indicado. Que ese environment
# solo se pueda usar desde main se fija en GitHub (Settings > Environments >
# Deployment branches): el token OIDC de un job con environment lleva el
# environment en el `sub`, no la rama.
data "aws_iam_policy_document" "github_confianza" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.oidc_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:environment:${var.github_environment}"]
    }
  }
}

resource "aws_iam_role" "github" {
  name               = "${local.prefijo}-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_confianza.json
}

data "aws_iam_policy_document" "github" {
  statement {
    sid       = "ECRToken"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "ECRPush"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = [aws_ecr_repository.backend.arn]
  }

  # Estas dos acciones de ECS no admiten recurso especifico.
  statement {
    sid       = "ECSDefinicionesDeTarea"
    actions   = ["ecs:DescribeTaskDefinition", "ecs:RegisterTaskDefinition"]
    resources = ["*"]
  }

  statement {
    sid     = "ECSServicios"
    actions = ["ecs:UpdateService", "ecs:DescribeServices"]
    resources = [
      aws_ecs_service.api.id,
      aws_ecs_service.worker.id,
    ]
  }

  statement {
    sid       = "ECSCorrerMigrate"
    actions   = ["ecs:RunTask"]
    resources = ["arn:aws:ecs:${var.region}:${local.cuenta_id}:task-definition/${aws_ecs_task_definition.migrate.family}:*"]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [aws_ecs_cluster.principal.arn]
    }
  }

  statement {
    sid       = "ECSVerTareas"
    actions   = ["ecs:DescribeTasks"]
    resources = ["arn:aws:ecs:${var.region}:${local.cuenta_id}:task/${aws_ecs_cluster.principal.name}/*"]
  }

  statement {
    sid       = "PasarRoles"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.ejecucion.arn, aws_iam_role.tarea.arn]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }

  statement {
    sid       = "LogsDeMigrate"
    actions   = ["logs:GetLogEvents"]
    resources = ["${aws_cloudwatch_log_group.tarea["migrate"].arn}:*"]
  }

  statement {
    sid       = "WebListar"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.web.arn]
  }

  statement {
    sid       = "WebObjetos"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.web.arn}/*"]
  }

  statement {
    sid       = "InvalidarCloudFront"
    actions   = ["cloudfront:CreateInvalidation", "cloudfront:GetInvalidation"]
    resources = [aws_cloudfront_distribution.web.arn]
  }
}

resource "aws_iam_role_policy" "github" {
  name   = "deploy"
  role   = aws_iam_role.github.id
  policy = data.aws_iam_policy_document.github.json
}
