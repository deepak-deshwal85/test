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
