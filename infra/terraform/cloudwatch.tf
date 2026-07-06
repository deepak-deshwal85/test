resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name_prefix}/api"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "voice_agent" {
  name              = "/ecs/${local.name_prefix}/voice-agent"
  retention_in_days = var.log_retention_days
}
