# Broker de Celery cuando cola = "redis": ElastiCache Valkey de un solo nodo.
# Sin cifrado en transito para que REDIS_URL sea redis:// (la app no esta
# configurada para rediss://); queda en subredes privadas y solo las tareas
# llegan al puerto 6379.

resource "aws_elasticache_subnet_group" "principal" {
  count = local.usa_redis ? 1 : 0

  name       = local.prefijo
  subnet_ids = aws_subnet.privada[*].id
}

resource "aws_elasticache_replication_group" "principal" {
  count = local.usa_redis ? 1 : 0

  replication_group_id = "${local.prefijo}-redis"
  description          = "Broker de Celery y cache de TodoGas (${var.entorno})"

  engine               = "valkey"
  engine_version       = "8.0"
  parameter_group_name = "default.valkey8"
  node_type            = "cache.t4g.micro"
  port                 = 6379

  num_cache_clusters         = 1
  automatic_failover_enabled = false
  multi_az_enabled           = false

  subnet_group_name  = aws_elasticache_subnet_group.principal[0].name
  security_group_ids = [aws_security_group.redis[0].id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = false

  snapshot_retention_limit   = 0
  auto_minor_version_upgrade = true
  apply_immediately          = true
}
