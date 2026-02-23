###############################################################################
# SCLC Patient Journey Dashboard - Monitoring Module
###############################################################################

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

###############################################################################
# SNS Topic for Alarm Notifications
###############################################################################

resource "aws_sns_topic" "alarms" {
  name = "${local.name_prefix}-alarm-notifications"

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-alarm-notifications"
  })
}

resource "aws_sns_topic_policy" "alarms" {
  arn = aws_sns_topic.alarms.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudWatchAlarms"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.alarms.arn
      }
    ]
  })
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

###############################################################################
# CloudWatch Dashboard
###############################################################################

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = concat(
      # API Gateway Widgets
      [
        {
          type   = "metric"
          x      = 0
          y      = 0
          width  = 12
          height = 6
          properties = {
            title   = "API Gateway - Request Count"
            view    = "timeSeries"
            stacked = false
            metrics = [
              ["AWS/ApiGateway", "Count", "ApiId", var.api_gateway_name, { stat = "Sum", period = 300 }]
            ]
            region = data.aws_region.current.name
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 0
          width  = 12
          height = 6
          properties = {
            title   = "API Gateway - Latency (ms)"
            view    = "timeSeries"
            stacked = false
            metrics = [
              ["AWS/ApiGateway", "Latency", "ApiId", var.api_gateway_name, { stat = "Average", period = 300 }],
              ["AWS/ApiGateway", "Latency", "ApiId", var.api_gateway_name, { stat = "p99", period = 300 }]
            ]
            region = data.aws_region.current.name
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 6
          width  = 12
          height = 6
          properties = {
            title   = "API Gateway - 4xx Errors"
            view    = "timeSeries"
            stacked = false
            metrics = [
              ["AWS/ApiGateway", "4XXError", "ApiId", var.api_gateway_name, { stat = "Sum", period = 300 }]
            ]
            region = data.aws_region.current.name
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 6
          width  = 12
          height = 6
          properties = {
            title   = "API Gateway - 5xx Errors"
            view    = "timeSeries"
            stacked = false
            metrics = [
              ["AWS/ApiGateway", "5XXError", "ApiId", var.api_gateway_name, { stat = "Sum", period = 300 }]
            ]
            region = data.aws_region.current.name
          }
        }
      ],
      # Lambda Widgets
      [
        {
          type   = "metric"
          x      = 0
          y      = 12
          width  = 12
          height = 6
          properties = {
            title   = "Lambda - Invocations"
            view    = "timeSeries"
            stacked = true
            metrics = [
              for fn_name in var.lambda_function_names :
              ["AWS/Lambda", "Invocations", "FunctionName", fn_name, { stat = "Sum", period = 300 }]
            ]
            region = data.aws_region.current.name
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 12
          width  = 12
          height = 6
          properties = {
            title   = "Lambda - Duration (ms)"
            view    = "timeSeries"
            stacked = false
            metrics = [
              for fn_name in var.lambda_function_names :
              ["AWS/Lambda", "Duration", "FunctionName", fn_name, { stat = "Average", period = 300 }]
            ]
            region = data.aws_region.current.name
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 18
          width  = 12
          height = 6
          properties = {
            title   = "Lambda - Errors"
            view    = "timeSeries"
            stacked = true
            metrics = [
              for fn_name in var.lambda_function_names :
              ["AWS/Lambda", "Errors", "FunctionName", fn_name, { stat = "Sum", period = 300 }]
            ]
            region = data.aws_region.current.name
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 18
          width  = 12
          height = 6
          properties = {
            title   = "Lambda - Throttles"
            view    = "timeSeries"
            stacked = true
            metrics = [
              for fn_name in var.lambda_function_names :
              ["AWS/Lambda", "Throttles", "FunctionName", fn_name, { stat = "Sum", period = 300 }]
            ]
            region = data.aws_region.current.name
          }
        }
      ],
      # Redshift Widgets
      [
        {
          type   = "metric"
          x      = 0
          y      = 24
          width  = 12
          height = 6
          properties = {
            title   = "Redshift Serverless - Query Duration"
            view    = "timeSeries"
            stacked = false
            metrics = [
              ["AWS/Redshift-Serverless", "QueryDuration", "Workgroup", "${local.name_prefix}-workgroup", { stat = "Average", period = 300 }],
              ["AWS/Redshift-Serverless", "QueryDuration", "Workgroup", "${local.name_prefix}-workgroup", { stat = "p99", period = 300 }]
            ]
            region = data.aws_region.current.name
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 24
          width  = 12
          height = 6
          properties = {
            title   = "Redshift Serverless - Database Connections"
            view    = "timeSeries"
            stacked = false
            metrics = [
              ["AWS/Redshift-Serverless", "DatabaseConnections", "Workgroup", "${local.name_prefix}-workgroup", { stat = "Average", period = 300 }]
            ]
            region = data.aws_region.current.name
          }
        }
      ]
    )
  })
}

data "aws_region" "current" {}

###############################################################################
# CloudWatch Alarms
###############################################################################

# API Gateway 5xx Rate > 1%
resource "aws_cloudwatch_metric_alarm" "api_5xx_rate" {
  alarm_name          = "${local.name_prefix}-api-5xx-rate"
  alarm_description   = "API Gateway 5xx error rate exceeds 1% over 5 minutes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 1
  treat_missing_data  = "notBreaching"

  metric_query {
    id          = "error_rate"
    expression  = "IF(requests > 0, errors / requests * 100, 0)"
    label       = "5xx Error Rate (%)"
    return_data = true
  }

  metric_query {
    id = "errors"

    metric {
      metric_name = "5XXError"
      namespace   = "AWS/ApiGateway"
      period      = 300
      stat        = "Sum"

      dimensions = {
        ApiId = var.api_gateway_name
      }
    }
  }

  metric_query {
    id = "requests"

    metric {
      metric_name = "Count"
      namespace   = "AWS/ApiGateway"
      period      = 300
      stat        = "Sum"

      dimensions = {
        ApiId = var.api_gateway_name
      }
    }
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-api-5xx-rate-alarm"
  })
}

# Lambda Errors > 5 in 5 minutes (per function)
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = toset(var.lambda_function_names)

  alarm_name          = "${local.name_prefix}-lambda-errors-${each.key}"
  alarm_description   = "Lambda function ${each.key} has more than 5 errors in 5 minutes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.key
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  tags = merge(var.tags, {
    Name     = "${local.name_prefix}-lambda-errors-alarm"
    Function = each.key
  })
}

# Lambda Duration p99 > 10s
resource "aws_cloudwatch_metric_alarm" "lambda_duration_p99" {
  for_each = toset(var.lambda_function_names)

  alarm_name          = "${local.name_prefix}-lambda-duration-p99-${each.key}"
  alarm_description   = "Lambda function ${each.key} p99 duration exceeds 10 seconds"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  extended_statistic  = "p99"
  threshold           = 10000 # 10 seconds in milliseconds
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.key
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  tags = merge(var.tags, {
    Name     = "${local.name_prefix}-lambda-duration-p99-alarm"
    Function = each.key
  })
}

# Redshift Query Queue Depth > 10
resource "aws_cloudwatch_metric_alarm" "redshift_queue_depth" {
  alarm_name          = "${local.name_prefix}-redshift-queue-depth"
  alarm_description   = "Redshift Serverless query queue depth exceeds 10"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "QueryRuntimeBreakdown"
  namespace           = "AWS/Redshift-Serverless"
  period              = 300
  statistic           = "Average"
  threshold           = 10
  treat_missing_data  = "notBreaching"

  dimensions = {
    Workgroup = "${local.name_prefix}-workgroup"
  }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-redshift-queue-depth-alarm"
  })
}
