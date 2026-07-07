output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_api_name" {
  value = aws_ecs_service.api.name
}

output "ecs_service_voice_agent_name" {
  value = aws_ecs_service.voice_agent.name
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
  description = "Injected into voice-agent task as RAG_API_BASE_URL."
  value       = "http://${local.api_service_dns}:8090"
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
