###############################################################################
# SCLC Patient Journey Dashboard - Lambda Module Outputs
###############################################################################

output "api_gateway_url" {
  description = "Invoke URL for the API Gateway v1 stage"
  value       = aws_api_gateway_stage.v1.invoke_url
}

output "api_gateway_id" {
  description = "ID of the API Gateway REST API"
  value       = aws_api_gateway_rest_api.main.id
}

output "lambda_function_arns" {
  description = "Map of Lambda function names to their ARNs"
  value       = { for k, v in aws_lambda_function.api : v.function_name => v.arn }
}
