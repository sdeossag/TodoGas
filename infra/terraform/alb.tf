resource "aws_lb" "api" {
  name               = local.prefijo
  load_balancer_type = "application"
  internal           = false
  subnets            = aws_subnet.publica[*].id
  security_groups    = [aws_security_group.alb.id]

  drop_invalid_header_fields = true
  enable_deletion_protection = var.proteger_datos
}

resource "aws_lb_target_group" "api" {
  name        = "${local.prefijo}-api"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.principal.id

  # Que la tarea vieja salga del balanceador rapido al desplegar.
  deregistration_delay = 30

  # El ALB consulta /health/ directo a cada tarea (puerto 8000), sin pasar por
  # el listener ni por sus reglas: no necesita la cabecera secreta.
  health_check {
    path                = "/health/"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

# Solo HTTPS, y solo para CloudFront: el grupo de seguridad (red.tf) deja entrar
# unicamente a las IP de CloudFront, y aqui se exige ademas la cabecera secreta
# de web.tf. Quien llegue sin ella (por ejemplo, directo a api.<dominio>) recibe
# 403 y no toca la API ni se salta el WAF. No hay listener en el puerto 80.
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.principal.certificate_arn

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "Acceso denegado"
      status_code  = "403"
    }
  }
}

resource "aws_lb_listener_rule" "desde_cloudfront" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    http_header {
      http_header_name = local.cabecera_origen
      values           = [random_password.origen_cloudfront.result]
    }
  }
}
