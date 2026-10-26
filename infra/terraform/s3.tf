# Bucket de evidencia (fotos, firmas, PDFs de actas).
#
# object_lock_enabled SOLO se puede activar al crear el bucket. Cambiarlo
# despues obliga a destruirlo (y con la retencion puesta, no se puede vaciar).

resource "aws_s3_bucket" "evidencia" {
  bucket              = "${local.prefijo}-evidencia"
  object_lock_enabled = true
  force_destroy       = !var.proteger_datos
}

resource "aws_s3_bucket_versioning" "evidencia" {
  bucket = aws_s3_bucket.evidencia.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_object_lock_configuration" "evidencia" {
  bucket = aws_s3_bucket.evidencia.id

  rule {
    default_retention {
      mode  = var.object_lock_mode
      years = var.object_lock_anios
    }
  }

  depends_on = [aws_s3_bucket_versioning.evidencia]
}

resource "aws_s3_bucket_public_access_block" "evidencia" {
  bucket = aws_s3_bucket.evidencia.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidencia" {
  bucket = aws_s3_bucket.evidencia.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "evidencia" {
  bucket = aws_s3_bucket.evidencia.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "evidencia" {
  bucket = aws_s3_bucket.evidencia.id

  rule {
    id     = "intelligent-tiering"
    status = "Enabled"

    filter {}

    transition {
      days          = 0
      storage_class = "INTELLIGENT_TIERING"
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.evidencia]
}

# Solo HTTPS.
data "aws_iam_policy_document" "evidencia_solo_tls" {
  statement {
    sid       = "SoloTLS"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.evidencia.arn, "${aws_s3_bucket.evidencia.arn}/*"]

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

resource "aws_s3_bucket_policy" "evidencia" {
  bucket = aws_s3_bucket.evidencia.id
  policy = data.aws_iam_policy_document.evidencia_solo_tls.json

  depends_on = [aws_s3_bucket_public_access_block.evidencia]
}
