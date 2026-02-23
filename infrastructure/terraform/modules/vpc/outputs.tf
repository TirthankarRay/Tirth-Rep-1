###############################################################################
# SCLC Patient Journey Dashboard - VPC Module Outputs
###############################################################################

output "vpc_id" {
  description = "ID of the created VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs (NAT Gateway, ALB)"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs (Lambda functions)"
  value       = aws_subnet.private[*].id
}

output "data_subnet_ids" {
  description = "List of data subnet IDs (Redshift Serverless)"
  value       = aws_subnet.data[*].id
}

output "sg_lambda_id" {
  description = "Security group ID for Lambda functions"
  value       = aws_security_group.lambda.id
}

output "sg_redshift_id" {
  description = "Security group ID for Redshift Serverless"
  value       = aws_security_group.redshift.id
}

output "nat_gateway_id" {
  description = "ID of the primary NAT Gateway"
  value       = aws_nat_gateway.main[0].id
}
