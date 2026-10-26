terraform {
  # use_lockfile (bloqueo del estado en S3 sin DynamoDB) necesita 1.10 o mas.
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.82"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Configuracion parcial: bucket, key y region llegan con
  # -backend-config (ver backend-prod.hcl y backend-staging.hcl).
  backend "s3" {}
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Proyecto   = "TodoGas"
      Entorno    = var.entorno
      GestionPor = "terraform"
    }
  }
}
