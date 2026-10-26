resource "aws_db_subnet_group" "principal" {
  name       = local.prefijo
  subnet_ids = aws_subnet.privada[*].id
}

resource "aws_db_parameter_group" "postgres16" {
  name   = "${local.prefijo}-postgres16"
  family = "postgres16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
}

resource "aws_db_instance" "principal" {
  identifier     = local.prefijo
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_clase

  db_name  = "todogas"
  username = "todogas"
  password = random_password.db.result
  port     = 5432

  allocated_storage     = var.db_almacenamiento_gb
  max_allocated_storage = var.db_almacenamiento_max_gb
  storage_type          = "gp3"
  storage_encrypted     = true

  multi_az               = var.multi_az
  publicly_accessible    = false
  db_subnet_group_name   = aws_db_subnet_group.principal.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.postgres16.name

  backup_retention_period    = var.backup_retention_dias
  backup_window              = "07:00-08:00" # 02:00 hora de Colombia
  maintenance_window         = "sun:08:30-sun:09:30"
  auto_minor_version_upgrade = true
  copy_tags_to_snapshot      = true

  deletion_protection       = var.proteger_datos
  skip_final_snapshot       = !var.proteger_datos
  final_snapshot_identifier = var.proteger_datos ? "${local.prefijo}-final" : null

  performance_insights_enabled = false

  lifecycle {
    # RDS sube la menor sola (16.x); Terraform no debe revertirla.
    ignore_changes = [engine_version]
  }
}
