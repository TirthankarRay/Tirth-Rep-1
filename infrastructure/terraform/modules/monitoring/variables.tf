###############################################################################
# SCLC Patient Journey Dashboard - Monitoring Module Variables
###############################################################################

variable "environment" {
  description = "Deployment environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name used as a prefix for all resources"
  type        = string
}

variable "api_gateway_name" {
  description = "API Gateway REST API ID for CloudWatch metrics dimensions"
  type        = string
}

variable "lambda_function_names" {
  description = "List of Lambda function names for per-function CloudWatch alarms"
  type        = list(string)
}

variable "alert_email" {
  description = "Email address for SNS alarm notification subscription"
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to all resources in this module"
  type        = map(string)
  default     = {}
}
