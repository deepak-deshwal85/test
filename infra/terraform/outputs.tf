output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_api_asg_name" {
  description = "Auto Scaling group for the API-dedicated ECS host."
  value       = aws_autoscaling_group.ecs["api"].name
}

output "ecs_voice_asg_name" {
  description = "Auto Scaling group for the voice-agent-dedicated ECS host."
  value       = aws_autoscaling_group.ecs["voice"].name
}

output "ecs_service_api_name" {
  value = aws_ecs_service.api.name
}

output "ecs_service_voice_agent_name" {
  value = aws_ecs_service.voice_agent.name
}

output "ecs_service_ui_name" {
  description = "ECS service name for the RelayDesk UI (null when enable_ui is false)."
  value       = var.enable_ui ? aws_ecs_service.ui[0].name : null
}

output "ecr_api_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "ecr_voice_agent_repository_url" {
  value = aws_ecr_repository.voice_agent.repository_url
}

output "api_alb_dns_name" {
  value = aws_lb.api.dns_name
}

output "api_internal_dns" {
  value = local.api_service_dns
}

output "github_actions_role_arn" {
  description = "Set as GitHub repository variable AWS_ROLE_ARN for OIDC deploy."
  value       = aws_iam_role.github_actions.arn
}

output "ssm_api_parameter_names" {
  value = [for k in local.api_secret_keys : aws_ssm_parameter.api[k].name]
}

output "ssm_voice_agent_parameter_names" {
  value = [for k in local.voice_agent_secret_keys : aws_ssm_parameter.voice_agent[k].name]
}

output "voice_agent_rag_api_base_url" {
  description = "Injected into voice-agent task as RAG_API_BASE_URL (internal ALB)."
  value       = local.api_rag_base_url
}

output "ui_url" {
  description = "Public URL for the RelayDesk UI (ALB HTTP)."
  value       = var.enable_ui ? "http://${aws_lb.api.dns_name}" : null
}

output "cognito_issuer" {
  description = "OIDC issuer URL for UI and API JWT validation."
  value       = local.cognito_enabled ? local.cognito_issuer : null
}

output "cognito_ui_client_id" {
  description = "Cognito app client ID for the UI (authorization code flow)."
  value       = local.cognito_enabled ? local.cognito_ui_client_id : null
}

output "cognito_hosted_ui_url" {
  description = "Cognito hosted UI sign-in URL."
  value = local.cognito_enabled ? (
    "https://${aws_cognito_user_pool_domain.main[0].domain}.auth.${var.aws_region}.amazoncognito.com/login?client_id=${local.cognito_ui_client_id}&response_type=code&scope=email+openid+profile+relaydesk-api/access&redirect_uri=${var.cognito_ui_callback_urls[0]}"
  ) : null
}

output "ecr_ui_repository_url" {
  value = var.enable_ui ? aws_ecr_repository.ui[0].repository_url : null
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint hostname."
  value       = var.enable_rds_postgres ? aws_db_instance.postgres[0].address : null
}

output "rds_port" {
  description = "RDS PostgreSQL port."
  value       = var.enable_rds_postgres ? aws_db_instance.postgres[0].port : null
}

output "rds_database_name" {
  description = "RDS PostgreSQL database name."
  value       = var.enable_rds_postgres ? aws_db_instance.postgres[0].db_name : null
}

output "rds_master_username" {
  description = "RDS PostgreSQL master username."
  value       = var.enable_rds_postgres ? aws_db_instance.postgres[0].username : null
}

output "billing_dashboard_name" {
  description = "CloudWatch dashboard for month-to-date estimated AWS charges (us-east-1)."
  value       = var.enable_cost_monitoring ? aws_cloudwatch_dashboard.billing[0].dashboard_name : null
}

output "billing_dashboard_url" {
  description = "Open CloudWatch billing dashboard (EstimatedCharges; updates every few hours)."
  value = var.enable_cost_monitoring ? (
    "https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=${aws_cloudwatch_dashboard.billing[0].dashboard_name}"
  ) : null
}

output "cost_explorer_url" {
  description = "Cost Explorer home — filter Tag: Project = <project_name> for RelayDesk-only spend."
  value       = var.enable_cost_monitoring ? "https://console.aws.amazon.com/cost-management/home#/cost-explorer" : null
}

output "monthly_budget_name" {
  description = "AWS Budget name for Project-tagged monthly spend."
  value       = var.enable_cost_monitoring ? aws_budgets_budget.monthly[0].name : null
}
