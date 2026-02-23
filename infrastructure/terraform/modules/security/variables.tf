###############################################################################
# SCLC Patient Journey Dashboard - Security Module Variables
###############################################################################

variable "environment" {
  description = "Deployment environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name used as a prefix for all resources"
  type        = string
}

variable "data_lake_bucket_arn" {
  description = "ARN of the S3 data lake bucket for CloudTrail S3 data event logging"
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to all resources in this module"
  type        = map(string)
  default     = {}
}
