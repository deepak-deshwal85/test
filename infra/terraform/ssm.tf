# Placeholder SecureString parameters — set real values in AWS Console/CLI after apply.
# Terraform ignores value changes so secrets are not stored in state after first edit.

resource "aws_ssm_parameter" "api" {
  for_each = toset(local.api_secret_keys)

  name  = "${local.ssm_prefix_api}/${each.key}"
  type  = "SecureString"
  value = "CHANGEME"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "voice_agent" {
  for_each = toset(local.voice_agent_secret_keys)

  name  = "${local.ssm_prefix_voice_agent}/${each.key}"
  type  = "SecureString"
  value = "CHANGEME"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "ui" {
  for_each = var.enable_ui ? toset(local.ui_secret_keys) : toset([])

  name  = "${local.ssm_prefix_ui}/${each.key}"
  type  = "SecureString"
  value = "CHANGEME"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "cognito_ui_client_secret" {
  count = local.cognito_enabled ? 1 : 0

  name  = "${local.ssm_prefix_ui}/COGNITO_CLIENT_SECRET"
  type  = "SecureString"
  value = aws_cognito_user_pool_client.ui[0].client_secret

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "cognito_voice_client_secret" {
  count = local.cognito_enabled ? 1 : 0

  name  = "${local.ssm_prefix_voice_agent}/COGNITO_CLIENT_SECRET"
  type  = "SecureString"
  value = aws_cognito_user_pool_client.voice_m2m[0].client_secret

  lifecycle {
    ignore_changes = [value]
  }
}
