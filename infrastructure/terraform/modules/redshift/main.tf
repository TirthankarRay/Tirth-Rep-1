###############################################################################
# SCLC Patient Journey Dashboard - Redshift Serverless Module
###############################################################################

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  is_prod     = var.environment == "prod"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

###############################################################################
# Secrets Manager - Redshift Admin Credentials
###############################################################################

resource "random_password" "redshift_admin" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}|:,.<>?"
}

resource "aws_secretsmanager_secret" "redshift_admin" {
  name        = "${local.name_prefix}/redshift/admin-credentials"
  description = "Redshift Serverless admin credentials for SCLC Dashboard"
  kms_key_id  = var.kms_key_arn

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-redshift-admin-secret"
  })
}

resource "aws_secretsmanager_secret_version" "redshift_admin" {
  secret_id = aws_secretsmanager_secret.redshift_admin.id

  secret_string = jsonencode({
    username = var.admin_username
    password = random_password.redshift_admin.result
    dbname   = "${replace(var.project_name, "-", "_")}_${var.environment}"
  })
}

###############################################################################
# IAM Role for Redshift (S3 Access + KMS)
###############################################################################

resource "aws_iam_role" "redshift" {
  name_prefix = "${local.name_prefix}-redshift-"
  path        = "/service-role/"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "redshift.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-redshift-role"
  })
}

resource "aws_iam_role_policy" "redshift_s3_access" {
  name_prefix = "${local.name_prefix}-redshift-s3-"
  role        = aws_iam_role.redshift.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ReadAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetBucketAcl",
          "s3:GetBucketCors",
          "s3:GetEncryptionConfiguration",
          "s3:GetBucketLocation",
          "s3:ListBucket",
          "s3:ListAllMyBuckets",
          "s3:ListMultipartUploadParts",
          "s3:ListBucketMultipartUploads"
        ]
        Resource = [
          var.s3_data_lake_arn,
          "${var.s3_data_lake_arn}/*"
        ]
      },
      {
        Sid    = "KMSDecryptAccess"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:GenerateDataKey"
        ]
        Resource = [var.kms_key_arn]
      }
    ]
  })
}

###############################################################################
# Redshift Serverless Namespace
###############################################################################

resource "aws_redshiftserverless_namespace" "main" {
  namespace_name      = "${local.name_prefix}-namespace"
  db_name             = "${replace(var.project_name, "-", "_")}_${var.environment}"
  admin_username      = var.admin_username
  admin_user_password = random_password.redshift_admin.result
  kms_key_id          = var.kms_key_arn
  iam_roles           = [aws_iam_role.redshift.arn]
  default_iam_role_arn = aws_iam_role.redshift.arn

  log_exports = [
    "connectionlog",
    "userlog",
    "useractivitylog"
  ]

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-namespace"
  })

  lifecycle {
    ignore_changes = [admin_user_password]
  }
}

###############################################################################
# Redshift Serverless Workgroup
###############################################################################

resource "aws_redshiftserverless_workgroup" "main" {
  workgroup_name     = "${local.name_prefix}-workgroup"
  namespace_name     = aws_redshiftserverless_namespace.main.namespace_name
  base_capacity      = local.is_prod ? 128 : 32
  security_group_ids = [var.sg_redshift_id]
  subnet_ids         = var.data_subnet_ids

  publicly_accessible  = false
  enhanced_vpc_routing = true

  config_parameter {
    parameter_key   = "enable_case_sensitive_identifier"
    parameter_value = "true"
  }

  config_parameter {
    parameter_key   = "auto_mv"
    parameter_value = "true"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-workgroup"
  })

  depends_on = [aws_redshiftserverless_namespace.main]
}
