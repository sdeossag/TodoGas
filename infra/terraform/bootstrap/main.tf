# Crea el bucket del estado de Terraform. Se corre UNA vez, con estado local
# (terraform.tfstate en este directorio, que no se sube a git). Un solo bucket
# sirve a prod y staging: cada uno usa su propia key.

terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.82"
    }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Proyecto   = "TodoGas"
      Entorno    = "compartido"
      GestionPor = "terraform-bootstrap"
    }
  }
}

data "aws_caller_identity" "actual" {}

resource "aws_s3_bucket" "estado" {
  bucket = "todogas-tfstate-${data.aws_caller_identity.actual.account_id}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "estado" {
  bucket = aws_s3_bucket.estado.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "estado" {
  bucket = aws_s3_bucket.estado.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "estado" {
  bucket = aws_s3_bucket.estado.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "estado" {
  bucket = aws_s3_bucket.estado.id

  rule {
    id     = "versiones-viejas"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.estado]
}

data "aws_iam_policy_document" "estado" {
  statement {
    sid       = "SoloTLS"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.estado.arn, "${aws_s3_bucket.estado.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "estado" {
  bucket = aws_s3_bucket.estado.id
  policy = data.aws_iam_policy_document.estado.json

  depends_on = [aws_s3_bucket_public_access_block.estado]
}

output "bucket_estado" {
  description = "Nombre para -backend-config=\"bucket=...\" en terraform init."
  value       = aws_s3_bucket.estado.bucket
}
