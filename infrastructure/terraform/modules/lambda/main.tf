###############################################################################
# SCLC Patient Journey Dashboard - Lambda + API Gateway Module
###############################################################################

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  # Lambda function configurations map
  lambda_functions = {
    fn_metrics_overview = {
      name        = "metrics-overview"
      description = "Returns high-level SCLC dashboard metrics overview"
      handler     = "metrics_overview.handler"
      http_method = "GET"
      resource_path = "metrics/overview"
    }
    fn_metrics_ttt = {
      name        = "metrics-ttt"
      description = "Returns time-to-treatment metrics for SCLC patients"
      handler     = "metrics_ttt.handler"
      http_method = "GET"
      resource_path = "metrics/time-to-treatment"
    }
    fn_metrics_treatment_patterns = {
      name        = "metrics-treatment-patterns"
      description = "Returns SCLC treatment pattern analysis"
      handler     = "metrics_treatment_patterns.handler"
      http_method = "GET"
      resource_path = "metrics/treatment-patterns"
    }
    fn_geographic_states = {
      name        = "geographic-states"
      description = "Returns geographic distribution of SCLC patients by state"
      handler     = "geographic_states.handler"
      http_method = "GET"
      resource_path = "geographic/states"
    }
    fn_patients_list = {
      name        = "patients-list"
      description = "Returns paginated list of SCLC patients"
      handler     = "patients_list.handler"
      http_method = "GET"
      resource_path = "patients"
    }
    fn_patients_detail = {
      name        = "patients-detail"
      description = "Returns detailed information for a specific patient"
      handler     = "patients_detail.handler"
      http_method = "GET"
      resource_path = "patients/{id}"
    }
    fn_journey_sankey = {
      name        = "journey-sankey"
      description = "Returns Sankey diagram data for patient treatment journeys"
      handler     = "journey_sankey.handler"
      http_method = "GET"
      resource_path = "patients/journey/sankey"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

###############################################################################
# IAM Role for Lambda Functions
###############################################################################

resource "aws_iam_role" "lambda" {
  name_prefix = "${local.name_prefix}-lambda-"
  path        = "/service-role/"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-lambda-role"
  })
}

resource "aws_iam_role_policy" "lambda_redshift" {
  name_prefix = "${local.name_prefix}-lambda-redshift-"
  role        = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RedshiftDataAPIAccess"
        Effect = "Allow"
        Action = [
          "redshift-data:BatchExecuteStatement",
          "redshift-data:ExecuteStatement",
          "redshift-data:CancelStatement",
          "redshift-data:DescribeStatement",
          "redshift-data:DescribeTable",
          "redshift-data:GetStatementResult",
          "redshift-data:ListDatabases",
          "redshift-data:ListSchemas",
          "redshift-data:ListTables"
        ]
        Resource = "*"
      },
      {
        Sid    = "RedshiftServerlessAccess"
        Effect = "Allow"
        Action = [
          "redshift-serverless:GetCredentials",
          "redshift-serverless:GetWorkgroup",
          "redshift-serverless:GetNamespace"
        ]
        Resource = "*"
      },
      {
        Sid    = "SecretsManagerAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${local.name_prefix}/*"
      },
      {
        Sid    = "CloudWatchLogsAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.name_prefix}-*:*"
      },
      {
        Sid    = "VPCNetworkInterfaceAccess"
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*"
      },
      {
        Sid    = "KMSDecryptAccess"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = [var.kms_key_arn]
      }
    ]
  })
}

###############################################################################
# Lambda Layer (Shared Code)
###############################################################################

data "archive_file" "lambda_layer" {
  type        = "zip"
  output_path = "${path.module}/builds/layer.zip"

  source {
    content  = <<-EOF
      # Shared database utilities for SCLC Dashboard Lambda functions
      import boto3
      import json
      import os
      import time

      def get_redshift_client():
          """Initialize and return Redshift Data API client."""
          return boto3.client('redshift-data')

      def execute_query(query, workgroup=None, database=None):
          """Execute a query against Redshift Serverless and return results."""
          client = get_redshift_client()
          workgroup = workgroup or os.environ.get('REDSHIFT_WORKGROUP')
          database = database or os.environ.get('REDSHIFT_DATABASE')

          response = client.execute_statement(
              WorkgroupName=workgroup,
              Database=database,
              Sql=query
          )

          statement_id = response['Id']

          # Poll for completion
          while True:
              status = client.describe_statement(Id=statement_id)
              if status['Status'] in ('FINISHED', 'FAILED', 'ABORTED'):
                  break
              time.sleep(0.1)

          if status['Status'] == 'FINISHED':
              if status.get('HasResultSet'):
                  result = client.get_statement_result(Id=statement_id)
                  return result
              return None
          else:
              raise Exception(f"Query failed: {status.get('Error', 'Unknown error')}")
    EOF
    filename = "python/lib/python3.12/site-packages/db.py"
  }

  source {
    content  = <<-EOF
      # Shared authentication utilities for SCLC Dashboard Lambda functions
      import json

      def build_response(status_code, body, headers=None):
          """Build a standard API Gateway response with CORS headers."""
          default_headers = {
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*',
              'Access-Control-Allow-Methods': 'GET,OPTIONS',
              'Access-Control-Allow-Headers': 'Content-Type,Authorization',
              'X-Content-Type-Options': 'nosniff',
              'X-Frame-Options': 'DENY',
              'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
          }
          if headers:
              default_headers.update(headers)

          return {
              'statusCode': status_code,
              'headers': default_headers,
              'body': json.dumps(body)
          }

      def get_user_claims(event):
          """Extract user claims from Cognito authorizer context."""
          claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
          return {
              'sub': claims.get('sub'),
              'email': claims.get('email'),
              'groups': claims.get('cognito:groups', '').split(',') if claims.get('cognito:groups') else []
          }
    EOF
    filename = "python/lib/python3.12/site-packages/auth.py"
  }
}

resource "aws_lambda_layer_version" "shared" {
  layer_name          = "${local.name_prefix}-shared-layer"
  filename            = data.archive_file.lambda_layer.output_path
  source_code_hash    = data.archive_file.lambda_layer.output_base64sha256
  compatible_runtimes = ["python3.12"]
  description         = "Shared utilities (db, auth) for SCLC Dashboard Lambda functions"
}

###############################################################################
# Lambda Functions (using for_each)
###############################################################################

data "archive_file" "lambda_placeholder" {
  for_each = local.lambda_functions

  type        = "zip"
  output_path = "${path.module}/builds/${each.value.name}.zip"

  source {
    content  = <<-EOF
      import json

      def handler(event, context):
          """Placeholder handler for ${each.value.name}. Replace with actual implementation."""
          return {
              'statusCode': 200,
              'headers': {
                  'Content-Type': 'application/json',
                  'Access-Control-Allow-Origin': '*'
              },
              'body': json.dumps({
                  'message': '${each.value.description}',
                  'status': 'placeholder'
              })
          }
    EOF
    filename = "${each.value.handler}.py"
  }
}

resource "aws_lambda_function" "api" {
  for_each = local.lambda_functions

  function_name    = "${local.name_prefix}-${each.value.name}"
  description      = each.value.description
  role             = aws_iam_role.lambda.arn
  handler          = each.value.handler
  runtime          = "python3.12"
  timeout          = 15
  memory_size      = 256
  filename         = data.archive_file.lambda_placeholder[each.key].output_path
  source_code_hash = data.archive_file.lambda_placeholder[each.key].output_base64sha256

  layers = [aws_lambda_layer_version.shared.arn]

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.sg_lambda_id]
  }

  environment {
    variables = {
      REDSHIFT_WORKGROUP = var.redshift_workgroup
      REDSHIFT_DATABASE  = var.redshift_database
      ENVIRONMENT        = var.environment
      LOG_LEVEL          = var.environment == "prod" ? "WARNING" : "DEBUG"
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(var.tags, {
    Name     = "${local.name_prefix}-${each.value.name}"
    Function = each.value.name
  })

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }

  depends_on = [
    aws_iam_role_policy.lambda_redshift,
    aws_cloudwatch_log_group.lambda
  ]
}

###############################################################################
# CloudWatch Log Groups (per Lambda function)
###############################################################################

resource "aws_cloudwatch_log_group" "lambda" {
  for_each = local.lambda_functions

  name              = "/aws/lambda/${local.name_prefix}-${each.value.name}"
  retention_in_days = 90
  kms_key_id        = var.kms_key_arn

  tags = merge(var.tags, {
    Name     = "${local.name_prefix}-${each.value.name}-logs"
    Function = each.value.name
  })
}

###############################################################################
# API Gateway REST API
###############################################################################

resource "aws_api_gateway_rest_api" "main" {
  name        = "${local.name_prefix}-api"
  description = "SCLC Patient Journey Dashboard REST API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-api"
  })
}

###############################################################################
# Cognito Authorizer
###############################################################################

resource "aws_api_gateway_authorizer" "cognito" {
  name            = "${local.name_prefix}-cognito-authorizer"
  rest_api_id     = aws_api_gateway_rest_api.main.id
  type            = "COGNITO_USER_POOLS"
  identity_source = "method.request.header.Authorization"
  provider_arns   = [var.cognito_user_pool_arn]
}

###############################################################################
# API Gateway Resources (nested path hierarchy)
###############################################################################

# /api
resource "aws_api_gateway_resource" "api" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "api"
}

# /api/v1
resource "aws_api_gateway_resource" "v1" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "v1"
}

# /api/v1/metrics
resource "aws_api_gateway_resource" "metrics" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "metrics"
}

# /api/v1/metrics/overview
resource "aws_api_gateway_resource" "metrics_overview" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.metrics.id
  path_part   = "overview"
}

# /api/v1/metrics/time-to-treatment
resource "aws_api_gateway_resource" "metrics_ttt" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.metrics.id
  path_part   = "time-to-treatment"
}

# /api/v1/metrics/treatment-patterns
resource "aws_api_gateway_resource" "metrics_treatment_patterns" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.metrics.id
  path_part   = "treatment-patterns"
}

# /api/v1/geographic
resource "aws_api_gateway_resource" "geographic" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "geographic"
}

# /api/v1/geographic/states
resource "aws_api_gateway_resource" "geographic_states" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.geographic.id
  path_part   = "states"
}

# /api/v1/patients
resource "aws_api_gateway_resource" "patients" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "patients"
}

# /api/v1/patients/{id}
resource "aws_api_gateway_resource" "patients_detail" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.patients.id
  path_part   = "{id}"
}

# /api/v1/patients/journey
resource "aws_api_gateway_resource" "patients_journey" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.patients.id
  path_part   = "journey"
}

# /api/v1/patients/journey/sankey
resource "aws_api_gateway_resource" "patients_journey_sankey" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.patients_journey.id
  path_part   = "sankey"
}

###############################################################################
# Local map: function key -> API Gateway resource ID
###############################################################################

locals {
  function_resource_map = {
    fn_metrics_overview          = aws_api_gateway_resource.metrics_overview.id
    fn_metrics_ttt               = aws_api_gateway_resource.metrics_ttt.id
    fn_metrics_treatment_patterns = aws_api_gateway_resource.metrics_treatment_patterns.id
    fn_geographic_states         = aws_api_gateway_resource.geographic_states.id
    fn_patients_list             = aws_api_gateway_resource.patients.id
    fn_patients_detail           = aws_api_gateway_resource.patients_detail.id
    fn_journey_sankey            = aws_api_gateway_resource.patients_journey_sankey.id
  }
}

###############################################################################
# API Gateway Methods + Integrations (using for_each)
###############################################################################

resource "aws_api_gateway_method" "api" {
  for_each = local.lambda_functions

  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = local.function_resource_map[each.key]
  http_method   = each.value.http_method
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = each.key == "fn_patients_detail" ? {
    "method.request.path.id" = true
  } : {}
}

resource "aws_api_gateway_integration" "api" {
  for_each = local.lambda_functions

  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = local.function_resource_map[each.key]
  http_method             = aws_api_gateway_method.api[each.key].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api[each.key].invoke_arn
}

###############################################################################
# CORS - OPTIONS Methods (using for_each)
###############################################################################

resource "aws_api_gateway_method" "cors" {
  for_each = local.lambda_functions

  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = local.function_resource_map[each.key]
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "cors" {
  for_each = local.lambda_functions

  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = local.function_resource_map[each.key]
  http_method = aws_api_gateway_method.cors[each.key].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "cors" {
  for_each = local.lambda_functions

  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = local.function_resource_map[each.key]
  http_method = aws_api_gateway_method.cors[each.key].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "cors" {
  for_each = local.lambda_functions

  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = local.function_resource_map[each.key]
  http_method = aws_api_gateway_method.cors[each.key].http_method
  status_code = aws_api_gateway_method_response.cors[each.key].status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

###############################################################################
# Lambda Permissions for API Gateway
###############################################################################

resource "aws_lambda_permission" "api_gateway" {
  for_each = local.lambda_functions

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

###############################################################################
# API Gateway Deployment + Stage
###############################################################################

resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.metrics_overview,
      aws_api_gateway_resource.metrics_ttt,
      aws_api_gateway_resource.metrics_treatment_patterns,
      aws_api_gateway_resource.geographic_states,
      aws_api_gateway_resource.patients,
      aws_api_gateway_resource.patients_detail,
      aws_api_gateway_resource.patients_journey_sankey,
      [for k, v in aws_api_gateway_method.api : v.id],
      [for k, v in aws_api_gateway_integration.api : v.id],
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_method.api,
    aws_api_gateway_integration.api,
    aws_api_gateway_method.cors,
    aws_api_gateway_integration.cors,
  ]
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${local.name_prefix}-api"
  retention_in_days = 90

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-api-logs"
  })
}

resource "aws_api_gateway_stage" "v1" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = "v1"

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
    })
  }

  xray_tracing_enabled = true

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-api-stage-v1"
  })
}

resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.v1.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled        = true
    logging_level          = "INFO"
    data_trace_enabled     = var.environment != "prod"
    throttling_burst_limit = 50
    throttling_rate_limit  = 100
  }
}
