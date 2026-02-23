###############################################################################
# SCLC Patient Journey Dashboard - S3 Module Variables
###############################################################################

variable "environment" {
  description = "Deployment environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name used as a prefix for all resources"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS CMK for data lake server-side encryption"
  type        = string
}

variable "cloudfront_oac_arn" {
  description = "ARN of the CloudFront Origin Access Control for frontend bucket policy"
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to all resources in this module"
  type        = map(string)
  default     = {}
}
