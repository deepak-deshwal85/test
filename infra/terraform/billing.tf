# Billing metrics and Budgets are account-level; CloudWatch billing metrics live in us-east-1.
provider "aws" {
  alias  = "billing"
  region = "us-east-1"
}

locals {
  billing_dashboard_name = "${local.name_prefix}-billing"
  budget_name            = "${local.name_prefix}-monthly"

  # Top AWS services for this stack (EstimatedCharges by ServiceName).
  billing_service_metrics = [
    ["AWS/Billing", "EstimatedCharges", "ServiceName", "AmazonEC2", "Currency", "USD"],
    ["AWS/Billing", "EstimatedCharges", "ServiceName", "AmazonRDS", "Currency", "USD"],
    ["AWS/Billing", "EstimatedCharges", "ServiceName", "AmazonVPC", "Currency", "USD"],
    ["AWS/Billing", "EstimatedCharges", "ServiceName", "AWSELB", "Currency", "USD"],
    ["AWS/Billing", "EstimatedCharges", "ServiceName", "AmazonECR", "Currency", "USD"],
    ["AWS/Billing", "EstimatedCharges", "ServiceName", "AmazonCloudWatch", "Currency", "USD"],
  ]
}

# Activate cost allocation tags so Cost Explorer can filter by Project / Environment.
resource "aws_ce_cost_allocation_tag" "project" {
  count = var.enable_cost_monitoring ? 1 : 0

  tag_key = "Project"
  status  = "Active"
}

resource "aws_ce_cost_allocation_tag" "environment" {
  count = var.enable_cost_monitoring ? 1 : 0

  tag_key = "Environment"
  status  = "Active"
}

resource "aws_budgets_budget" "monthly" {
  count = var.enable_cost_monitoring ? 1 : 0

  name         = local.budget_name
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = ["Project$${var.project_name}"]
  }

  dynamic "notification" {
    for_each = length(var.budget_alert_emails) > 0 ? [1] : []
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = 80
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = var.budget_alert_emails
    }
  }

  dynamic "notification" {
    for_each = length(var.budget_alert_emails) > 0 ? [1] : []
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = 100
      threshold_type             = "PERCENTAGE"
      notification_type          = "FORECASTED"
      subscriber_email_addresses = var.budget_alert_emails
    }
  }
}

resource "aws_cloudwatch_dashboard" "billing" {
  count = var.enable_cost_monitoring ? 1 : 0

  provider       = aws.billing
  dashboard_name = local.billing_dashboard_name

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 8
        height = 6
        properties = {
          view    = "singleValue"
          region  = "us-east-1"
          stat    = "Maximum"
          period  = 21600
          title   = "Month-to-date estimated total (USD)"
          metrics = [
            ["AWS/Billing", "EstimatedCharges", "Currency", "USD", { stat = "Maximum" }],
          ]
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 0
        width  = 16
        height = 6
        properties = {
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          stat    = "Maximum"
          period  = 21600
          title   = "Month-to-date estimated total over time (USD)"
          metrics = [
            ["AWS/Billing", "EstimatedCharges", "Currency", "USD"],
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 24
        height = 8
        properties = {
          view    = "timeSeries"
          stacked = true
          region  = "us-east-1"
          stat    = "Maximum"
          period  = 21600
          title   = "Estimated charges by service (USD) — current month"
          metrics = local.billing_service_metrics
        }
      },
      {
        type   = "text"
        x      = 0
        y      = 14
        width  = 24
        height = 3
        properties = {
          markdown = <<-EOT
            **RelayDesk cost monitoring** — Metrics update every ~6 hours. Forecasted month-end spend: open [Cost Explorer](https://console.aws.amazon.com/cost-management/home#/cost-explorer) → *Monthly costs by service* → filter **Tag: Project = ${var.project_name}**. Budget: **${local.budget_name}** (${var.monthly_budget_usd} USD/month).
          EOT
        }
      },
    ]
  })
}
