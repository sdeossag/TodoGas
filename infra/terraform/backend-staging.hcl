# terraform init -reconfigure -backend-config=backend-staging.hcl -backend-config="bucket=<bucket del bootstrap>"
key          = "staging/terraform.tfstate"
region       = "us-east-1"
encrypt      = true
use_lockfile = true
