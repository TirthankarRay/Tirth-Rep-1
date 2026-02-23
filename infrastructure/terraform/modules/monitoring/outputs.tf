###############################################################################
# SCLC Patient Journey Dashboard - Monitoring Module Outputs
###############################################################################

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alarm notifications"
  value       = aws_sns_topic.alarms.arn
}

output "alarm_arns" {
  description = "Map of alarm names to their ARNs"
  value = merge(
    { "api-5xx-rate" = aws_cloudwatch_metric_alarm.api_5xx_rate.arn },
    { for k, v in aws_cloudwatch_metric_alarm.lambda_errors : "lambda-errors-${k}" => v.arn },
    { for k, v in aws_cloudwatch_metric_alarm.lambda_duration_p99 : "lambda-duration-p99-${k}" => v.arn },
    { "redshift-queue-depth" = aws_cloudwatch_metric_alarm.redshift_queue_depth.arn }
  )
}
