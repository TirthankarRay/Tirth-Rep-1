###############################################################################
# SCLC Patient Journey Dashboard - CloudFront Module Variables
###############################################################################

variable "environment" {
  description = "Deployment environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name used as a prefix for all resources"
  type        = string
}

variable "frontend_bucket_domain" {
  description = "Regional domain name of the S3 frontend bucket for CloudFront origin"
  type        = string
}

variable "frontend_bucket_arn" {
  description = "ARN of the S3 frontend bucket for bucket policy"
  type        = string
}

variable "frontend_bucket_name" {
  description = "Name of the S3 frontend bucket"
  type        = string
}

variable "domain_name" {
  description = "Custom domain name for CloudFront distribution (leave empty to use default CloudFront domain)"
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "ARN of the ACM certificate for the custom domain (must be in us-east-1)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags to apply to all resources in this module"
  type        = map(string)
  default     = {}
}
