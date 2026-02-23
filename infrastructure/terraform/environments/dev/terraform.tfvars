###############################################################################
# SCLC Patient Journey Dashboard - Dev Environment Configuration
###############################################################################

environment = "dev"
aws_region  = "us-east-1"
vpc_cidr    = "10.0.0.0/16"
alert_email = "sclc-alerts-dev@example.com"

tags = {
  CostCenter  = "sclc-research"
  DataClass   = "phi"
  Compliance  = "hipaa"
}
