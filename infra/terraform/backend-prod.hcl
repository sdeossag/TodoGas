# terraform init -backend-config=backend-prod.hcl -backend-config="bucket=<bucket del bootstrap>"
key          = "prod/terraform.tfstate"
region       = "us-east-1"
encrypt      = true
use_lockfile = true
