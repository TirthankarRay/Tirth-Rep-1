###############################################################################
# SCLC Patient Journey Dashboard - CloudFront Module Outputs
###############################################################################

output "distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.id
}

output "distribution_domain" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.domain_name
}

output "oac_arn" {
  description = "ARN of the CloudFront Origin Access Control"
  value       = aws_cloudfront_distribution.main.arn
}

output "web_acl_arn" {
  description = "ARN of the WAF v2 Web ACL"
  value       = aws_wafv2_web_acl.main.arn
}
