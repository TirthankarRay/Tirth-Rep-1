###############################################################################
# SCLC Patient Journey Dashboard - Security Module Outputs
###############################################################################

output "kms_key_arn" {
  description = "ARN of the KMS Customer Managed Key"
  value       = aws_kms_key.main.arn
}

output "kms_key_id" {
  description = "ID of the KMS Customer Managed Key"
  value       = aws_kms_key.main.key_id
}

output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_arn" {
  description = "ARN of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.arn
}

output "cognito_client_id" {
  description = "ID of the Cognito User Pool Client"
  value       = aws_cognito_user_pool_client.main.id
}

output "cloudtrail_arn" {
  description = "ARN of the CloudTrail trail"
  value       = aws_cloudtrail.main.arn
}
