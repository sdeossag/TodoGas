# Web (React + Vite): bucket privado + CloudFront con OAC. El deploy sube dist/
# con `aws s3 sync` e invalida la distribucion. La misma distribucion lleva la
# API (origen "api" = el ALB) y el WAF (waf.tf).

resource "aws_s3_bucket" "web" {
  bucket        = "${local.prefijo}-web"
  force_destroy = true # son archivos generados por el build: se pueden recrear
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket = aws_s3_bucket.web.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "web" {
  bucket = aws_s3_bucket.web.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "web" {
  bucket = aws_s3_bucket.web.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "web" {
  bucket = aws_s3_bucket.web.id

  rule {
    id     = "limpieza"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_cloudfront_origin_access_control" "web" {
  name                              = "${local.prefijo}-web"
  description                       = "Acceso de CloudFront al bucket de la web"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

data "aws_cloudfront_cache_policy" "optimizada" {
  name = "Managed-CachingOptimized"
}

# Plan de tarifa fija de CloudFront: solo admite politicas administradas
# (Managed-*), no las propias.
data "aws_cloudfront_cache_policy" "sin_cache" {
  name = "Managed-CachingDisabled"
}

# Reenvia todo lo del visitante, incluidos Authorization y Host: Django ve
# Host = el dominio principal y el JWT llega intacto.
data "aws_cloudfront_origin_request_policy" "todo_el_visitante" {
  name = "Managed-AllViewer"
}

data "aws_cloudfront_response_headers_policy" "seguridad" {
  name = "Managed-SecurityHeadersPolicy"
}

# Valor secreto que CloudFront manda al ALB en cada peticion. El ALB solo
# reenvia a la API si lo trae (ver alb.tf); asi nadie salta CloudFront y su WAF
# aunque llegue a la IP del ALB. Sin simbolos para que sirva en una cabecera.
resource "random_password" "origen_cloudfront" {
  length  = 48
  special = false
}

# SPA: las rutas del front (React Router, p. ej. /ordenes/123) no existen en el
# bucket. Antes lo resolvian los custom_error_response 403/404 -> index.html,
# pero esos afectan a TODA la distribucion y taparian los 403/404 reales de la
# API (/api/*), que el front necesita ver tal cual. Esta funcion corre solo en
# el behavior por defecto (el bucket) y reescribe a /index.html las rutas cuyo
# ultimo segmento no tiene extension de archivo. Los archivos reales
# (assets/app.js, favicon.ico) pasan sin cambios.
resource "aws_cloudfront_function" "spa" {
  name    = "${local.prefijo}-spa"
  comment = "Rutas del front sin extension -> /index.html"
  runtime = "cloudfront-js-2.0"
  publish = true

  code = <<-EOT
    function handler(event) {
      var request = event.request;
      var uri = request.uri;

      // /admin sin barra final caeria en el bucket: se manda al panel de Django.
      if (uri === '/admin') {
        return {
          statusCode: 301,
          statusDescription: 'Moved Permanently',
          headers: { location: { value: '/admin/' } }
        };
      }

      var ultimo = uri.substring(uri.lastIndexOf('/') + 1);
      if (ultimo.indexOf('.') === -1) {
        request.uri = '/index.html';
      }
      return request;
    }
  EOT
}

# Una sola distribucion para la web y la API (mismo origen: sin CORS en el
# navegador y un unico WAF). El default va al bucket; /api/*, /admin/* y
# /static/* (estaticos del admin, los sirve whitenoise) van al ALB. Son 4
# behaviors contando el default; el plan Free admite 5.
resource "aws_cloudfront_distribution" "web" {
  enabled             = true
  is_ipv6_enabled     = true
  http_version        = "http2and3"
  comment             = "TodoGas CMMS web y API (${var.entorno})"
  default_root_object = "index.html"
  aliases             = [var.dominio]
  price_class         = "PriceClass_100"
  web_acl_id          = aws_wafv2_web_acl.principal.arn

  origin {
    domain_name              = aws_s3_bucket.web.bucket_regional_domain_name
    origin_id                = "web"
    origin_access_control_id = aws_cloudfront_origin_access_control.web.id
  }

  # El nombre api.<dominio> apunta al ALB (dns.tf) y esta en el certificado del
  # ALB, asi que el TLS hacia el origen valida. Los visitantes nunca lo usan.
  origin {
    domain_name = local.dominio_api
    origin_id   = "api"

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "https-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 60 # los PDF de reportes pueden tardar
      origin_keepalive_timeout = 5
    }

    custom_header {
      name  = local.cabecera_origen
      value = random_password.origen_cloudfront.result
    }
  }

  default_cache_behavior {
    target_origin_id           = "web"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.optimizada.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.seguridad.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa.arn
    }
  }

  dynamic "ordered_cache_behavior" {
    for_each = local.rutas_api

    content {
      path_pattern             = ordered_cache_behavior.value
      target_origin_id         = "api"
      viewer_protocol_policy   = "redirect-to-https"
      allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods           = ["GET", "HEAD"]
      compress                 = false # sin cache no hay compresion en CloudFront
      cache_policy_id          = data.aws_cloudfront_cache_policy.sin_cache.id
      origin_request_policy_id = data.aws_cloudfront_origin_request_policy.todo_el_visitante.id
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.principal.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

data "aws_iam_policy_document" "web" {
  statement {
    sid       = "LecturaDesdeCloudFront"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.web.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.web.arn]
    }
  }

  statement {
    sid       = "SoloTLS"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.web.arn, "${aws_s3_bucket.web.arn}/*"]

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

resource "aws_s3_bucket_policy" "web" {
  bucket = aws_s3_bucket.web.id
  policy = data.aws_iam_policy_document.web.json

  depends_on = [aws_s3_bucket_public_access_block.web]
}
