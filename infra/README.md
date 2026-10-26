# Infraestructura en AWS

Terraform de TodoGas CMMS en `infra/terraform/` y workflow de despliegue en
`.github/workflows/deploy.yml`. Contrato de variables de entorno y procesos:
`docs/infra/VARIABLES.md`. Correo: `docs/infra/SES.md`.

```
Internet ──> Route 53 ──> CloudFront ──> S3 (web)            cmms.todogas.com.co
                     └──> ALB (80->443) ──> ECS api          api.cmms.todogas.com.co
                                              ECS worker+beat ──> SQS (o Valkey)
                                              RDS PostgreSQL 16 (subredes privadas)
                                              S3 evidencia (Object Lock) · SES · SSM
```

Región `us-east-1`, contenedores ARM64 (Graviton), sin NAT Gateway: las tareas
van en subredes públicas con IP pública y los grupos de seguridad las protegen
(API solo desde el ALB, worker sin entrada, RDS y Redis solo desde las tareas).

## Requisitos

- Terraform **>= 1.10** (el bloqueo del estado con `use_lockfile` no existe antes).
- AWS CLI con credenciales de un administrador de la cuenta (solo para correr
  Terraform a mano; el despliegue de la app usa OIDC, sin claves).
- Acceso al DNS de `todogas.com.co` en GoDaddy.
- Repo `sdeossag/TodoGas` en GitHub, con permiso para crear environments.

Sin instalar Terraform, con Docker:

```bash
docker run --rm -it -v "$PWD:/w" -w /w -e AWS_PROFILE -e AWS_REGION=us-east-1 \
  -v "$HOME/.aws:/root/.aws:ro" hashicorp/terraform:1.10.5 <comando>
```

## 1. Bootstrap del estado (una sola vez)

Crea el bucket S3 del estado de Terraform (versionado, cifrado, privado). Usa
estado local; el archivo `terraform.tfstate` de ese directorio no se sube a git.

```bash
cd infra/terraform/bootstrap
terraform init
terraform apply
terraform output bucket_estado     # todogas-tfstate-<cuenta>
```

Un solo bucket sirve a prod y staging; cada uno usa su propia key.

## 2. Inicializar y aplicar prod

Edita `prod.tfvars` y pon el `correo_alertas` real. Después:

```bash
cd infra/terraform
terraform init -backend-config=backend-prod.hcl -backend-config="bucket=<bucket_estado>"
terraform plan  -var-file=prod.tfvars -out=prod.plan
```

### Primer apply en dos pasos (por la delegación DNS)

El certificado de ACM solo se valida cuando GoDaddy ya delega el subdominio; si
se aplica todo de una vez, el apply se queda esperando. Primero la zona:

```bash
terraform apply -var-file=prod.tfvars -target=aws_route53_zone.principal
terraform output servidores_ns
```

Delega en GoDaddy (siguiente sección), espera unos minutos y aplica todo:

```bash
terraform apply -var-file=prod.tfvars
```

La validación del certificado, la creación de CloudFront y de RDS tardan; el
apply completo ronda los 20-30 minutos.

## 3. Delegar el subdominio en GoDaddy

El dominio `todogas.com.co` sigue en GoDaddy; solo el subdominio `cmms` pasa a
Route 53. Pídele al administrador de GoDaddy **4 registros NS**:

| Tipo | Nombre / Host | Valor |
|---|---|---|
| NS | `cmms` | primer servidor de `servidores_ns` |
| NS | `cmms` | segundo |
| NS | `cmms` | tercero |
| NS | `cmms` | cuarto |

(Sin punto final si GoDaddy lo rechaza.) Comprobar: `nslookup -type=NS cmms.todogas.com.co`
debe devolver los 4 de AWS. Los registros A, MX y TXT del dominio principal no se tocan.

## 4. Parámetros que se llenan a mano

Terraform crea `SECRET_KEY` y `DB_PASSWORD` solos. Estos dos llevan un valor de
relleno (Parameter Store no admite vacíos) y Terraform ignora su valor:

```bash
aws ssm put-parameter --name /todogas-prod/GOOGLE_MAPS_API_KEY \
  --type SecureString --overwrite --value '<clave de Google Maps>'
aws ssm put-parameter --name /todogas-prod/SENTRY_DSN \
  --type SecureString --overwrite --value '<DSN de Sentry>'
```

Las tareas leen los parámetros al arrancar: después de cambiarlos, reinicia
los servicios:

```bash
aws ecs update-service --cluster todogas-prod --service todogas-prod-api    --force-new-deployment
aws ecs update-service --cluster todogas-prod --service todogas-prod-worker --force-new-deployment
```

Mientras el valor sea el relleno `sin-configurar`, el backend lo trata como
vacío: Sentry queda apagado y el servidor no usa Google Maps. La clave de Maps del front (`VITE_GOOGLE_MAPS_API_KEY`)
es otra cosa: va como variable del environment de GitHub (abajo).

## 5. Salir del sandbox de SES

Terraform crea la identidad del dominio con DKIM, el MAIL FROM `mail.cmms.todogas.com.co`
(MX y SPF), DMARC y el conjunto de configuración. Falta pedir a AWS que saque la
cuenta del sandbox y comprobar la entrega: sigue `docs/infra/SES.md`, pasos 4 y 5.
`dmarc_politica` empieza en `none`; súbela a `quarantine` y luego `reject` en
`prod.tfvars` tras 2-4 semanas sin fallos legítimos.

Además, confirma la suscripción: SNS manda un correo a `correo_alertas`
("AWS Notification - Subscription Confirmation") y AWS Budgets avisa al mismo correo.

## 6. GitHub: environment y variables

En el repo: Settings > Environments > New environment `production`.

- **Required reviewers**: quien aprueba cada despliegue.
- **Deployment branches**: solo `main`. Es lo que limita el rol de AWS a esa
  rama (el rol confía en `repo:sdeossag/TodoGas:environment:production`).

Variables del environment (Variables, no Secrets: no hay ninguna clave).
`terraform output -json variables_github` las imprime todas:

| Variable | De dónde sale |
|---|---|
| `AWS_REGION` | `us-east-1` |
| `AWS_ROLE_ARN` | output `rol_github_arn` |
| `ECR_REPOSITORY` | nombre del repo: `todogas-prod-backend` |
| `ECS_CLUSTER` | output `cluster` |
| `ECS_SERVICE_API` / `ECS_SERVICE_WORKER` | outputs `servicio_api` y `servicio_worker` |
| `TASK_FAMILY_API` / `TASK_FAMILY_WORKER` / `TASK_FAMILY_MIGRATE` | `todogas-prod-api`, `-worker`, `-migrate` |
| `MIGRATE_SUBNETS` | IDs de las 2 subredes públicas, separados por coma |
| `MIGRATE_SECURITY_GROUP` | ID del grupo de seguridad de la API |
| `WEB_BUCKET` | output `bucket_web` |
| `CLOUDFRONT_ID` | output `cloudfront_id` |
| `API_URL` | `https://api.cmms.todogas.com.co` (opcional; ese es el valor por defecto) |
| `VITE_GOOGLE_MAPS_API_KEY` | opcional, clave de Maps para el front |

## Qué hace el primer despliegue

Al crear la infraestructura, las tareas de ECS apuntan a la imagen
`<ecr>:inicial`, que no existe: los servicios `api` y `worker` quedan sin
arrancar (es normal; el circuit breaker los reintenta) hasta el primer deploy.
Para lanzarlo: push a `main` (o Actions > Deploy > Run workflow) y aprobar el
environment. El workflow:

1. asume el rol de AWS por OIDC;
2. construye la imagen **arm64** (QEMU + buildx) y la sube a ECR con el SHA del commit;
3. toma la última revisión de las familias `api`, `worker` y `migrate`, cambia la
   imagen y registra una revisión nueva de cada una;
4. corre la tarea `migrate` (`migrate --noinput && createcachetable`) y espera:
   si termina con código distinto de 0, el job falla **antes** de tocar los servicios;
5. actualiza `api` y `worker` y espera a que queden estables;
6. construye la web (`npm ci && npm run build`, con `VITE_API_BASE_URL`), la
   sube a S3 y crea una invalidación de CloudFront.

Los servicios ignoran `task_definition` en Terraform: lo que cambie el deploy
no lo revierte un `apply`. En cambio, si cambias el entorno de los contenedores
en Terraform (variables, secretos), `apply` registra una revisión nueva de la
familia y **hay que correr un deploy** (o `update-service`) para que la use.

El worker se actualiza parando la tarea vieja antes de arrancar la nueva
(`deployment_minimum_healthy_percent = 0`): hay unos segundos sin worker, pero
nunca dos beat a la vez.

## Cambiar `cola` o `worker_en_spot`

Son decisiones a confirmar con el cliente. Se cambian en `prod.tfvars` (o con
`-var`) y se aplican:

```bash
terraform plan  -var-file=prod.tfvars -var cola=redis -var worker_en_spot=false
```

- `worker_en_spot`: cambia solo el capacity provider del servicio del worker
  (FARGATE <-> FARGATE_SPOT). Con spot, AWS puede interrumpir la tarea con 2
  minutos de aviso; el servicio la vuelve a lanzar. Cuesta ~US$12/mes menos.
- `cola`: crea Valkey (`cache.t4g.micro`) y borra SQS, o al revés. **Los
  mensajes pendientes de la cola vieja se pierden**: haz el cambio en una
  ventana sin envíos, y corre un deploy después del `apply` (la definición de
  tarea cambia `CELERY_BROKER` y `CELERY_SQS_QUEUE_URL`/`REDIS_URL`). Con Redis
  el caché de Django también pasa a Redis.

## Bucket de evidencia (Object Lock)

`object_lock_enabled` se fija **al crear el bucket**; no se puede activar después.
La retención por defecto (`object_lock_mode`, `object_lock_anios`) sí se puede
cambiar luego, pero solo afecta a objetos nuevos. Confirmar con el sistema de
calidad del cliente antes del primer apply:

- `GOVERNANCE` (por defecto): se puede saltar con el permiso `s3:BypassGovernanceRetention`.
- `COMPLIANCE`: nadie, ni root, puede borrar antes de que venza. Irreversible.

Con la retención puesta, un archivo subido por error no se puede borrar hasta
que venza (en `GOVERNANCE`, solo con el bypass).

## Staging: crear y destruir

Staging usa otro dominio (`cmms-staging.todogas.com.co`; delégalo igual con 4 NS
propios), el mismo bucket de estado con otra key y `proteger_datos = false`
(sin deletion protection, sin snapshot final). No crea el proveedor OIDC ni el
presupuesto: son de toda la cuenta y los crea prod, así que **aplica prod primero**.

```bash
cd infra/terraform
terraform init -reconfigure -backend-config=backend-staging.hcl -backend-config="bucket=<bucket_estado>"
terraform apply -var-file=staging.tfvars -target=aws_route53_zone.principal   # delegar y luego:
terraform apply -var-file=staging.tfvars

terraform destroy -var-file=staging.tfvars
```

Para desplegar a staging, crea un environment `staging` en GitHub con sus propias
variables (`terraform output -json variables_github` de ese estado, y `API_URL`)
y lanza el workflow a mano eligiendo `staging`. El bucket de evidencia de staging
tiene retención de 1 año en `GOVERNANCE`; el destroy lo vacía con el bypass
(`force_destroy`), por lo que quien lo ejecuta necesita `s3:BypassGovernanceRetention`.
Al volver a `prod` ejecuta `terraform init -reconfigure -backend-config=backend-prod.hcl ...`.

## Alarmas y presupuesto

SNS `todogas-<entorno>-alertas` (correo a `correo_alertas`): ALB sin hosts sanos
3 minutos y 5xx; RDS CPU, CPUCreditBalance, FreeStorageSpace y FreeableMemory;
SQS mensajes en la DLQ y mensaje más viejo > 15 min; SES tasa de rebote (5 %) y
de quejas (0,1 %). AWS Budgets: `presupuesto_usd` mensual (90 por defecto), aviso
al 80 % real y al 100 % pronosticado.

## Pruebas sin cuenta de AWS

```bash
terraform fmt -check -recursive
terraform init -backend=false && terraform validate
terraform test -var-file=prod.tfvars       # provider simulado: evalua cola/spot de verdad
terraform test -var-file=staging.tfvars
```

## Costos esperados (us-east-1, sin IVA, por mes)

| | `sqs` + spot | `redis` + sin spot |
|---|---|---|
| Fargate API (0,5 vCPU / 1 GB, ARM) | 14 | 14 |
| Fargate worker (0,5 vCPU / 2 GB, ARM) | 5 (spot) | 17 |
| ALB | 18 | 18 |
| IPv4 públicas (ALB y tareas) | 15 | 15 |
| RDS db.t4g.micro + 20 GB gp3 | 14 | 14 |
| Valkey cache.t4g.micro | - | 9 |
| CloudWatch, Route 53, CloudFront, S3, SQS, SES, ECR | ~5 | ~4 |
| **Total aproximado** | **~US$71** | **~US$95** |

Crece con el almacenamiento de evidencia (S3 Intelligent-Tiering), el disco de
RDS (autoescala hasta 100 GB) y los logs. Multi-AZ en RDS (`multi_az = true`)
duplica la parte de la base. No incluye el presupuesto de staging mientras
esté destruido.
