###############################################################################
# SCLC Patient Journey Dashboard - Root Terraform Configuration
###############################################################################

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  backend "s3" {
    bucket         = "sclc-terraform-state-${data.aws_caller_identity.current.account_id}"
    key            = "sclc-dashboard/${var.environment}/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "sclc-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Provider for CloudFront ACM certificates (must be us-east-1)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

###############################################################################
# Data Sources
###############################################################################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

###############################################################################
# Module: VPC
###############################################################################

module "vpc" {
  source = "./modules/vpc"

  vpc_cidr     = var.vpc_cidr
  environment  = var.environment
  project_name = var.project_name
  tags         = var.tags
}

###############################################################################
# Module: Security (KMS, Cognito, CloudTrail, Config)
###############################################################################

module "security" {
  source = "./modules/security"

  environment        = var.environment
  project_name       = var.project_name
  data_lake_bucket_arn = module.s3.data_lake_bucket_arn
  tags               = var.tags

  depends_on = [module.s3]
}

###############################################################################
# Module: S3 (Data Lake + Frontend)
###############################################################################

module "s3" {
  source = "./modules/s3"

  environment      = var.environment
  project_name     = var.project_name
  kms_key_arn      = module.security.kms_key_arn
  cloudfront_oac_arn = module.cloudfront.oac_arn
  tags             = var.tags
}

###############################################################################
# Module: Redshift Serverless
###############################################################################

module "redshift" {
  source = "./modules/redshift"

  environment      = var.environment
  project_name     = var.project_name
  vpc_id           = module.vpc.vpc_id
  data_subnet_ids  = module.vpc.data_subnet_ids
  sg_redshift_id   = module.vpc.sg_redshift_id
  kms_key_arn      = module.security.kms_key_arn
  s3_data_lake_arn = module.s3.data_lake_bucket_arn
  admin_username   = var.redshift_admin_username
  tags             = var.tags

  depends_on = [module.vpc, module.security, module.s3]
}

###############################################################################
# Module: Lambda + API Gateway
###############################################################################

module "lambda" {
  source = "./modules/lambda"

  environment         = var.environment
  project_name        = var.project_name
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  sg_lambda_id        = module.vpc.sg_lambda_id
  redshift_workgroup  = module.redshift.workgroup_name
  redshift_database   = "${var.project_name}_${var.environment}"
  cognito_user_pool_arn = module.security.cognito_user_pool_arn
  kms_key_arn         = module.security.kms_key_arn
  tags                = var.tags

  depends_on = [module.vpc, module.redshift, module.security]
}

###############################################################################
# Module: CloudFront + WAF
###############################################################################

module "cloudfront" {
  source = "./modules/cloudfront"

  environment          = var.environment
  project_name         = var.project_name
  frontend_bucket_domain = module.s3.frontend_bucket_domain
  frontend_bucket_arn  = module.s3.frontend_bucket_arn
  frontend_bucket_name = module.s3.frontend_bucket_name
  domain_name          = var.domain_name
  acm_certificate_arn  = var.domain_name != "" ? var.acm_certificate_arn : ""
  tags                 = var.tags
}

###############################################################################
# Module: Monitoring (CloudWatch, SNS)
###############################################################################

module "monitoring" {
  source = "./modules/monitoring"

  environment          = var.environment
  project_name         = var.project_name
  api_gateway_name     = module.lambda.api_gateway_id
  lambda_function_names = keys(module.lambda.lambda_function_arns)
  alert_email          = var.alert_email
  tags                 = var.tags

  depends_on = [module.lambda]
}
