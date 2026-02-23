###############################################################################
# SCLC Patient Journey Dashboard - Prod Environment Configuration
###############################################################################

environment = "prod"
aws_region  = "us-east-1"
vpc_cidr    = "10.1.0.0/16"
alert_email = "sclc-alerts-prod@example.com"

tags = {
  CostCenter  = "sclc-research"
  DataClass   = "phi"
  Compliance  = "hipaa"
}
