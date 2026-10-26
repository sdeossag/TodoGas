output "servidores_ns" {
  description = "Los 4 NS de la zona: se los das al administrador de GoDaddy (4 registros NS para el subdominio)."
  value       = aws_route53_zone.principal.name_servers
}

output "ecr_url" {
  description = "URL del repositorio de ECR."
  value       = aws_ecr_repository.backend.repository_url
}

output "rol_github_arn" {
  description = "ARN del rol que asume GitHub Actions por OIDC."
  value       = aws_iam_role.github.arn
}

output "cola_url" {
  description = "URL de la cola de SQS (null con cola = redis)."
  value       = one(aws_sqs_queue.celery[*].url)
}

output "cluster" {
  description = "Nombre del cluster de ECS."
  value       = aws_ecs_cluster.principal.name
}

output "servicio_api" {
  value = aws_ecs_service.api.name
}

output "servicio_worker" {
  value = aws_ecs_service.worker.name
}

output "cloudfront_id" {
  description = "ID de la distribucion de CloudFront de la web."
  value       = aws_cloudfront_distribution.web.id
}

output "bucket_web" {
  description = "Bucket donde el deploy sube la web."
  value       = aws_s3_bucket.web.bucket
}

output "bucket_evidencia" {
  value = aws_s3_bucket.evidencia.bucket
}

output "db_endpoint" {
  value = aws_db_instance.principal.address
}

# Todo lo que el workflow de despliegue lee como variable del environment.
output "variables_github" {
  description = "Variables del environment de GitHub (Settings > Environments > Variables). Ver infra/README.md."
  value = {
    AWS_REGION             = var.region
    AWS_ROLE_ARN           = aws_iam_role.github.arn
    ECR_REPOSITORY         = aws_ecr_repository.backend.name
    ECS_CLUSTER            = aws_ecs_cluster.principal.name
    ECS_SERVICE_API        = aws_ecs_service.api.name
    ECS_SERVICE_WORKER     = aws_ecs_service.worker.name
    TASK_FAMILY_API        = aws_ecs_task_definition.api.family
    TASK_FAMILY_WORKER     = aws_ecs_task_definition.worker.family
    TASK_FAMILY_MIGRATE    = aws_ecs_task_definition.migrate.family
    MIGRATE_SUBNETS        = join(",", aws_subnet.publica[*].id)
    MIGRATE_SECURITY_GROUP = aws_security_group.api.id
    WEB_BUCKET             = aws_s3_bucket.web.bucket
    CLOUDFRONT_ID          = aws_cloudfront_distribution.web.id
    API_URL                = "https://${local.dominio_api}"
  }
}
