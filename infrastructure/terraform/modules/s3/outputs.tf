###############################################################################
# SCLC Patient Journey Dashboard - S3 Module Outputs
###############################################################################

output "data_lake_bucket_arn" {
  description = "ARN of the S3 data lake bucket"
  value       = aws_s3_bucket.data_lake.arn
}

output "data_lake_bucket_name" {
  description = "Name of the S3 data lake bucket"
  value       = aws_s3_bucket.data_lake.id
}

output "frontend_bucket_arn" {
  description = "ARN of the S3 frontend bucket"
  value       = aws_s3_bucket.frontend.arn
}

output "frontend_bucket_name" {
  description = "Name of the S3 frontend bucket"
  value       = aws_s3_bucket.frontend.id
}

output "frontend_bucket_domain" {
  description = "Regional domain name of the S3 frontend bucket for CloudFront origin"
  value       = aws_s3_bucket.frontend.bucket_regional_domain_name
}
