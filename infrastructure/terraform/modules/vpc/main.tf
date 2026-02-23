###############################################################################
# SCLC Patient Journey Dashboard - VPC Module
###############################################################################

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  is_prod     = var.environment == "prod"
}

###############################################################################
# Availability Zones
###############################################################################

data "aws_availability_zones" "available" {
  state = "available"

  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

###############################################################################
# VPC
###############################################################################

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpc"
  })
}

###############################################################################
# Public Subnets (NAT Gateway, ALB)
###############################################################################

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-public-${data.aws_availability_zones.available.names[count.index]}"
    Tier = "public"
  })
}

###############################################################################
# Private Subnets (Lambda)
###############################################################################

resource "aws_subnet" "private" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 11)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-private-${data.aws_availability_zones.available.names[count.index]}"
    Tier = "private"
  })
}

###############################################################################
# Data Subnets (Redshift)
###############################################################################

resource "aws_subnet" "data" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 21)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-data-${data.aws_availability_zones.available.names[count.index]}"
    Tier = "data"
  })
}

###############################################################################
# Internet Gateway
###############################################################################

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-igw"
  })
}

###############################################################################
# Elastic IP(s) for NAT Gateway
###############################################################################

resource "aws_eip" "nat" {
  count  = local.is_prod ? 2 : 1
  domain = "vpc"

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-nat-eip-${count.index + 1}"
  })

  depends_on = [aws_internet_gateway.main]
}

###############################################################################
# NAT Gateway (single for dev, HA pair for prod)
###############################################################################

resource "aws_nat_gateway" "main" {
  count = local.is_prod ? 2 : 1

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-nat-${count.index + 1}"
  })

  depends_on = [aws_internet_gateway.main]
}

###############################################################################
# Route Tables - Public
###############################################################################

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-rt-public"
  })
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

###############################################################################
# Route Tables - Private (route through NAT)
###############################################################################

resource "aws_route_table" "private" {
  count = local.is_prod ? 2 : 1

  vpc_id = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-rt-private-${count.index + 1}"
  })
}

resource "aws_route" "private_nat" {
  count = local.is_prod ? 2 : 1

  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main[count.index].id
}

resource "aws_route_table_association" "private" {
  count = 2

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[local.is_prod ? count.index : 0].id
}

###############################################################################
# Route Tables - Data (no internet access)
###############################################################################

resource "aws_route_table" "data" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-rt-data"
  })
}

resource "aws_route_table_association" "data" {
  count = 2

  subnet_id      = aws_subnet.data[count.index].id
  route_table_id = aws_route_table.data.id
}

###############################################################################
# Security Group - Lambda
###############################################################################

resource "aws_security_group" "lambda" {
  name_prefix = "${local.name_prefix}-sg-lambda-"
  description = "Security group for Lambda functions accessing Redshift and HTTPS endpoints"
  vpc_id      = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-sg-lambda"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_egress_rule" "lambda_to_redshift" {
  security_group_id            = aws_security_group.lambda.id
  description                  = "Allow Lambda to connect to Redshift on port 5439"
  from_port                    = 5439
  to_port                      = 5439
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.redshift.id
}

resource "aws_vpc_security_group_egress_rule" "lambda_to_https" {
  security_group_id = aws_security_group.lambda.id
  description       = "Allow Lambda outbound HTTPS for AWS API calls"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"
}

###############################################################################
# Security Group - Redshift
###############################################################################

resource "aws_security_group" "redshift" {
  name_prefix = "${local.name_prefix}-sg-redshift-"
  description = "Security group for Redshift Serverless workgroup"
  vpc_id      = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-sg-redshift"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "redshift_from_lambda" {
  security_group_id            = aws_security_group.redshift.id
  description                  = "Allow inbound connections from Lambda on port 5439"
  from_port                    = 5439
  to_port                      = 5439
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.lambda.id
}

###############################################################################
# Security Group - VPC Endpoints
###############################################################################

resource "aws_security_group" "vpc_endpoint" {
  name_prefix = "${local.name_prefix}-sg-vpce-"
  description = "Security group for VPC Interface Endpoints"
  vpc_id      = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-sg-vpce"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "vpce_https" {
  security_group_id = aws_security_group.vpc_endpoint.id
  description       = "Allow HTTPS inbound from VPC CIDR"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  cidr_ipv4         = var.vpc_cidr
}

###############################################################################
# VPC Endpoints (Interface)
###############################################################################

resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpce-secretsmanager"
  })
}

resource "aws_vpc_endpoint" "redshift_data" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.redshift-data"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpce-redshift-data"
  })
}

resource "aws_vpc_endpoint" "cloudwatch_logs" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpce-logs"
  })
}

data "aws_region" "current" {}

###############################################################################
# VPC Flow Logs
###############################################################################

resource "aws_flow_log" "main" {
  vpc_id                   = aws_vpc.main.id
  traffic_type             = "ALL"
  log_destination_type     = "cloud-watch-logs"
  log_destination          = aws_cloudwatch_log_group.flow_log.arn
  iam_role_arn             = aws_iam_role.flow_log.arn
  max_aggregation_interval = 60

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpc-flow-log"
  })
}

resource "aws_cloudwatch_log_group" "flow_log" {
  name              = "/aws/vpc/flow-log/${local.name_prefix}"
  retention_in_days = 90

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpc-flow-log-group"
  })
}

resource "aws_iam_role" "flow_log" {
  name_prefix = "${local.name_prefix}-vpc-flow-log-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpc-flow-log-role"
  })
}

resource "aws_iam_role_policy" "flow_log" {
  name_prefix = "${local.name_prefix}-vpc-flow-log-"
  role        = aws_iam_role.flow_log.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}
