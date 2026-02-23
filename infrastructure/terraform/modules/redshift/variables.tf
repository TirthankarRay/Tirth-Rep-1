###############################################################################
# SCLC Patient Journey Dashboard - Redshift Module Variables
###############################################################################

variable "environment" {
  description = "Deployment environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name used as a prefix for all resources"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where Redshift Serverless will be deployed"
  type        = string
}

variable "data_subnet_ids" {
  description = "List of data subnet IDs for Redshift Serverless workgroup"
  type        = list(string)
}

variable "sg_redshift_id" {
  description = "Security group ID to attach to the Redshift Serverless workgroup"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS CMK for Redshift namespace encryption"
  type        = string
}

variable "s3_data_lake_arn" {
  description = "ARN of the S3 data lake bucket for Redshift IAM role access"
  type        = string
}

variable "admin_username" {
  description = "Admin username for Redshift Serverless namespace"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Additional tags to apply to all resources in this module"
  type        = map(string)
  default     = {}
}
