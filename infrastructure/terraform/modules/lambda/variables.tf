###############################################################################
# SCLC Patient Journey Dashboard - Lambda Module Variables
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
  description = "ID of the VPC for Lambda VPC configuration"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for Lambda VPC configuration"
  type        = list(string)
}

variable "sg_lambda_id" {
  description = "Security group ID to attach to Lambda functions"
  type        = string
}

variable "redshift_workgroup" {
  description = "Name of the Redshift Serverless workgroup for Lambda environment variables"
  type        = string
}

variable "redshift_database" {
  description = "Name of the Redshift database for Lambda environment variables"
  type        = string
}

variable "cognito_user_pool_arn" {
  description = "ARN of the Cognito User Pool for API Gateway authorization"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS CMK for encrypting Lambda environment variables and logs"
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to all resources in this module"
  type        = map(string)
  default     = {}
}
