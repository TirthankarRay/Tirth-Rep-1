###############################################################################
# SCLC Patient Journey Dashboard - Redshift Module Outputs
###############################################################################

output "workgroup_name" {
  description = "Name of the Redshift Serverless workgroup"
  value       = aws_redshiftserverless_workgroup.main.workgroup_name
}

output "namespace_name" {
  description = "Name of the Redshift Serverless namespace"
  value       = aws_redshiftserverless_namespace.main.namespace_name
}

output "redshift_role_arn" {
  description = "ARN of the IAM role attached to Redshift for S3 access"
  value       = aws_iam_role.redshift.arn
}

output "admin_secret_arn" {
  description = "ARN of the Secrets Manager secret containing admin credentials"
  value       = aws_secretsmanager_secret.redshift_admin.arn
}
