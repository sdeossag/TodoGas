# Zona de Route 53 del subdominio. GoDaddy delega el subdominio con 4 registros
# NS (output servidores_ns); el resto del dominio sigue en GoDaddy.

resource "aws_route53_zone" "principal" {
  name    = var.dominio
  comment = "TodoGas CMMS (${var.entorno})"
}

# Un certificado para CloudFront (dominio principal) y para el ALB
# (api.<dominio>, el origen de CloudFront); los dos viven en us-east-1, que es
# donde CloudFront exige el certificado.
resource "aws_acm_certificate" "principal" {
  domain_name               = var.dominio
  subject_alternative_names = [local.dominio_api]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# Las claves son fijas (los dos nombres); solo los valores salen de ACM. Asi
# for_each se conoce al planear.
resource "aws_route53_record" "validacion_acm" {
  for_each = toset([var.dominio, local.dominio_api])

  zone_id = aws_route53_zone.principal.zone_id
  name = one([
    for o in aws_acm_certificate.principal.domain_validation_options : o.resource_record_name if o.domain_name == each.key
  ])
  type = one([
    for o in aws_acm_certificate.principal.domain_validation_options : o.resource_record_type if o.domain_name == each.key
  ])
  records = [one([
    for o in aws_acm_certificate.principal.domain_validation_options : o.resource_record_value if o.domain_name == each.key
  ])]
  ttl             = 60
  allow_overwrite = true
}

# Espera a que ACM valide: solo ocurre cuando GoDaddy ya delego el subdominio.
resource "aws_acm_certificate_validation" "principal" {
  certificate_arn         = aws_acm_certificate.principal.arn
  validation_record_fqdns = [for r in aws_route53_record.validacion_acm : r.fqdn]
}

# Nombre del ALB para que CloudFront lo use como origen (con certificado
# valido). El ALB solo contesta a CloudFront: directo da 403.
resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.principal.zone_id
  name    = local.dominio_api
  type    = "A"

  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "web" {
  zone_id = aws_route53_zone.principal.zone_id
  name    = var.dominio
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.web.domain_name
    zone_id                = aws_cloudfront_distribution.web.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "web_ipv6" {
  zone_id = aws_route53_zone.principal.zone_id
  name    = var.dominio
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.web.domain_name
    zone_id                = aws_cloudfront_distribution.web.hosted_zone_id
    evaluate_target_health = false
  }
}
