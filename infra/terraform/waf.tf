# WAF de CloudFront (web y API). Scope CLOUDFRONT: el recurso vive en
# us-east-1, que es la region del proveedor.
#
# El plan de tarifa fija Free de CloudFront incluye el WAF pero admite como
# maximo 5 reglas y no admite grupos de reglas propios (los administrados de
# AWS si). Por eso son exactamente 5: cuatro grupos administrados y un limite de
# peticiones. No agregar mas sin pasar al plan Pro (ver infra/README.md).
#
# Cada regla publica su metrica en CloudWatch (namespace AWS/WAFV2, region
# us-east-1): sirven para ver que bloquea o cuenta cada una.

locals {
  # Peticiones a /api/auth/ por IP en una ventana de 5 minutos. El front solo
  # llama a /api/auth/refresh/ cuando una peticion recibe 401 (no en bucle) y a
  # /api/auth/me/ al abrir la app, asi que un usuario normal hace pocas. 100
  # deja pasar a un hospital entero detras de una sola IP (NAT) iniciando sesion
  # a la vez y frena la fuerza bruta de contrasenas.
  limite_auth       = 100
  ventana_auth_segs = 300
}

resource "aws_wafv2_web_acl" "principal" {
  name        = "${local.prefijo}-cloudfront"
  description = "WAF de la web y la API de TodoGas CMMS (${var.entorno})"
  scope       = "CLOUDFRONT"

  default_action {
    allow {}
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.prefijo}-waf"
    sampled_requests_enabled   = true
  }

  # 1. IPs con mala reputacion (botnets, escaneos) segun AWS.
  rule {
    name     = "ReputacionDeIP"
    priority = 10

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.prefijo}-waf-reputacion-ip"
      sampled_requests_enabled   = true
    }
  }

  # 2. Limite de intentos de login y similares por IP.
  rule {
    name     = "LimiteAuth"
    priority = 20

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit                 = local.limite_auth
        evaluation_window_sec = local.ventana_auth_segs
        aggregate_key_type    = "IP"

        scope_down_statement {
          byte_match_statement {
            search_string         = "/api/auth/"
            positional_constraint = "STARTS_WITH"

            field_to_match {
              uri_path {}
            }

            text_transformation {
              priority = 0
              type     = "LOWERCASE"
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.prefijo}-waf-limite-auth"
      sampled_requests_enabled   = true
    }
  }

  # 3. Entradas conocidas como maliciosas (Log4j, deserializacion Java, etc.).
  rule {
    name     = "EntradasMaliciosas"
    priority = 30

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.prefijo}-waf-entradas-maliciosas"
      sampled_requests_enabled   = true
    }
  }

  # 4. Reglas generales de AWS (XSS, LFI/RFI, tamanos, etc.). Dos reglas del
  # grupo pasan a "count" (se cuentan y se dejan pasar) porque bloquearian
  # trafico legitimo de la app:
  #
  # - SizeRestrictions_BODY: bloquea cuerpos de mas de 8 KB. Las fotos (hasta
  #   10 MB, apps/evidence) y las firmas suben como multipart por la API, y los
  #   JSON del checklist y de la sincronizacion offline tambien pasan de 8 KB.
  #   El limite real lo pone Django (MAX_PHOTO_BYTES).
  # - CrossSiteScripting_BODY: mira el cuerpo en busca de HTML o JavaScript.
  #   Los checklists y los hallazgos llevan texto libre de los tecnicos (y las
  #   respuestas viajan en JSON grandes); un comentario con etiquetas o con
  #   "onclick=" bastaria para perder el guardado de una OT en campo. El riesgo
  #   que queda es bajo: React escapa todo lo que muestra y el admin de Django
  #   tambien. Las variantes de XSS en URL, query y cookies siguen bloqueando.
  #
  # El resto del grupo bloquea. Si alguna regla bloquea de mas, aparece en la
  # metrica del grupo; se pasa a count aqui con otro rule_action_override.
  rule {
    name     = "ReglasGenerales"
    priority = 40

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        rule_action_override {
          name = "SizeRestrictions_BODY"

          action_to_use {
            count {}
          }
        }

        rule_action_override {
          name = "CrossSiteScripting_BODY"

          action_to_use {
            count {}
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.prefijo}-waf-reglas-generales"
      sampled_requests_enabled   = true
    }
  }

  # 5. Inyeccion SQL.
  rule {
    name     = "InyeccionSQL"
    priority = 50

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.prefijo}-waf-sqli"
      sampled_requests_enabled   = true
    }
  }
}
