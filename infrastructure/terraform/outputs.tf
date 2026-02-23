###############################################################################
# SCLC Patient Journey Dashboard - Root Outputs
###############################################################################

output "cloudfront_url" {
  description = "CloudFront distribution URL for the dashboard frontend"
  value       = module.cloudfront.distribution_domain
}

output "api_gateway_url" {
  description = "API Gateway invoke URL for backend endpoints"
  value       = module.lambda.api_gateway_url
}

output "redshift_workgroup" {
  description = "Redshift Serverless workgroup name"
  value       = module.redshift.workgroup_name
}

output "s3_data_lake_bucket" {
  description = "S3 data lake bucket name for clinical data ingestion"
  value       = module.s3.data_lake_bucket_name
}

output "cognito_user_pool_id" {
  description = "Cognito user pool ID for authentication"
  value       = module.security.cognito_user_pool_id
}
