# VPC de 2 zonas. Sin NAT Gateway: las tareas de ECS van en subredes publicas
# con IP publica (los grupos de seguridad son los que las protegen). Las
# subredes privadas no tienen ruta a internet y alojan RDS y Redis.

resource "aws_vpc" "principal" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = local.prefijo }
}

resource "aws_internet_gateway" "principal" {
  vpc_id = aws_vpc.principal.id

  tags = { Name = local.prefijo }
}

resource "aws_subnet" "publica" {
  count = length(local.zonas)

  vpc_id                  = aws_vpc.principal.id
  availability_zone       = local.zonas[count.index]
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  map_public_ip_on_launch = false # cada tarea pide su IP publica al lanzarse

  tags = { Name = "${local.prefijo}-publica-${local.zonas[count.index]}" }
}

resource "aws_subnet" "privada" {
  count = length(local.zonas)

  vpc_id            = aws_vpc.principal.id
  availability_zone = local.zonas[count.index]
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)

  tags = { Name = "${local.prefijo}-privada-${local.zonas[count.index]}" }
}

resource "aws_route_table" "publica" {
  vpc_id = aws_vpc.principal.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.principal.id
  }

  tags = { Name = "${local.prefijo}-publica" }
}

resource "aws_route_table_association" "publica" {
  count = length(local.zonas)

  subnet_id      = aws_subnet.publica[count.index].id
  route_table_id = aws_route_table.publica.id
}

# Tabla privada: solo la ruta local de la VPC.
resource "aws_route_table" "privada" {
  vpc_id = aws_vpc.principal.id

  tags = { Name = "${local.prefijo}-privada" }
}

resource "aws_route_table_association" "privada" {
  count = length(local.zonas)

  subnet_id      = aws_subnet.privada[count.index].id
  route_table_id = aws_route_table.privada.id
}

# Se cierra el grupo de seguridad por defecto de la VPC (sin reglas).
resource "aws_default_security_group" "cerrado" {
  vpc_id = aws_vpc.principal.id

  tags = { Name = "${local.prefijo}-default-cerrado" }
}

# ── Grupos de seguridad ──────────────────────────────────────────────────────
resource "aws_security_group" "alb" {
  name        = "${local.prefijo}-alb"
  description = "ALB: 80 y 443 desde internet"
  vpc_id      = aws_vpc.principal.id

  tags = { Name = "${local.prefijo}-alb" }
}

resource "aws_security_group" "api" {
  name        = "${local.prefijo}-api"
  description = "Tareas de la API: 8000 solo desde el ALB"
  vpc_id      = aws_vpc.principal.id

  tags = { Name = "${local.prefijo}-api" }
}

resource "aws_security_group" "worker" {
  name        = "${local.prefijo}-worker"
  description = "Tareas del worker y beat: sin entrada"
  vpc_id      = aws_vpc.principal.id

  tags = { Name = "${local.prefijo}-worker" }
}

resource "aws_security_group" "rds" {
  name        = "${local.prefijo}-rds"
  description = "RDS: 5432 solo desde las tareas"
  vpc_id      = aws_vpc.principal.id

  tags = { Name = "${local.prefijo}-rds" }
}

resource "aws_security_group" "redis" {
  count = local.usa_redis ? 1 : 0

  name        = "${local.prefijo}-redis"
  description = "Redis: 6379 solo desde las tareas"
  vpc_id      = aws_vpc.principal.id

  tags = { Name = "${local.prefijo}-redis" }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTP (redirige a HTTPS)"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTPS"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "alb_a_api" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Hacia la API"
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.api.id
}

resource "aws_vpc_security_group_ingress_rule" "api_desde_alb" {
  security_group_id            = aws_security_group.api.id
  description                  = "Desde el ALB"
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.alb.id
}

# Las tareas necesitan salir: ECR, SSM, CloudWatch, S3, SQS, SES y Google.
resource "aws_vpc_security_group_egress_rule" "api_salida" {
  security_group_id = aws_security_group.api.id
  description       = "Salida a internet (ECR, SSM, S3, SES, Google)"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "worker_salida" {
  security_group_id = aws_security_group.worker.id
  description       = "Salida a internet (ECR, SSM, S3, SQS, SES)"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "rds_desde_api" {
  security_group_id            = aws_security_group.rds.id
  description                  = "Desde la API y la tarea migrate"
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.api.id
}

resource "aws_vpc_security_group_ingress_rule" "rds_desde_worker" {
  security_group_id            = aws_security_group.rds.id
  description                  = "Desde el worker"
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.worker.id
}

resource "aws_vpc_security_group_ingress_rule" "redis_desde_api" {
  count = local.usa_redis ? 1 : 0

  security_group_id            = aws_security_group.redis[0].id
  description                  = "Desde la API"
  ip_protocol                  = "tcp"
  from_port                    = 6379
  to_port                      = 6379
  referenced_security_group_id = aws_security_group.api.id
}

resource "aws_vpc_security_group_ingress_rule" "redis_desde_worker" {
  count = local.usa_redis ? 1 : 0

  security_group_id            = aws_security_group.redis[0].id
  description                  = "Desde el worker"
  ip_protocol                  = "tcp"
  from_port                    = 6379
  to_port                      = 6379
  referenced_security_group_id = aws_security_group.worker.id
}
