# Correo transaccional. Pasos manuales (sandbox, prueba): docs/infra/SES.md.

resource "aws_sesv2_configuration_set" "principal" {
  configuration_set_name = local.prefijo

  reputation_options {
    reputation_metrics_enabled = true
  }

  sending_options {
    sending_enabled = true
  }
}

# Metricas de envio, entrega, rebotes y quejas por conjunto en CloudWatch.
resource "aws_sesv2_configuration_set_event_destination" "cloudwatch" {
  configuration_set_name = aws_sesv2_configuration_set.principal.configuration_set_name
  event_destination_name = "cloudwatch"

  event_destination {
    enabled = true
    matching_event_types = [
      "SEND",
      "DELIVERY",
      "BOUNCE",
      "COMPLAINT",
      "REJECT",
    ]

    cloud_watch_destination {
      dimension_configuration {
        dimension_name          = "conjunto"
        dimension_value_source  = "MESSAGE_TAG"
        default_dimension_value = local.prefijo
      }
    }
  }
}

resource "aws_sesv2_email_identity" "dominio" {
  email_identity         = var.dominio
  configuration_set_name = aws_sesv2_configuration_set.principal.configuration_set_name

  dkim_signing_attributes {
    next_signing_key_length = "RSA_2048_BIT"
  }
}

# MAIL FROM propio: alinea el SPF con el dominio y DMARC pasa por SPF y DKIM.
resource "aws_sesv2_email_identity_mail_from_attributes" "dominio" {
  email_identity         = aws_sesv2_email_identity.dominio.email_identity
  mail_from_domain       = "mail.${var.dominio}"
  behavior_on_mx_failure = "USE_DEFAULT_VALUE"
}

# DKIM: 3 CNAME (el numero lo fija SES).
resource "aws_route53_record" "dkim" {
  count = 3

  zone_id = aws_route53_zone.principal.zone_id
  name    = "${aws_sesv2_email_identity.dominio.dkim_signing_attributes[0].tokens[count.index]}._domainkey.${var.dominio}"
  type    = "CNAME"
  ttl     = 600
  records = ["${aws_sesv2_email_identity.dominio.dkim_signing_attributes[0].tokens[count.index]}.dkim.amazonses.com"]
}

resource "aws_route53_record" "mail_from_mx" {
  zone_id = aws_route53_zone.principal.zone_id
  name    = "mail.${var.dominio}"
  type    = "MX"
  ttl     = 600
  records = ["10 feedback-smtp.${var.region}.amazonses.com"]
}

resource "aws_route53_record" "mail_from_spf" {
  zone_id = aws_route53_zone.principal.zone_id
  name    = "mail.${var.dominio}"
  type    = "TXT"
  ttl     = 600
  records = ["v=spf1 include:amazonses.com ~all"]
}

resource "aws_route53_record" "dmarc" {
  zone_id = aws_route53_zone.principal.zone_id
  name    = "_dmarc.${var.dominio}"
  type    = "TXT"
  ttl     = 600
  records = ["v=DMARC1; p=${var.dmarc_politica}; rua=${var.dmarc_rua}; adkim=s; aspf=s"]
}
