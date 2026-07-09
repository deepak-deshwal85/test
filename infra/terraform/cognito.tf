resource "aws_cognito_user_pool" "main" {
  count = var.enable_cognito ? 1 : 0

  name = "${local.name_prefix}-users"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  lambda_config {
    post_confirmation = aws_lambda_function.cognito_assign_guest_role[0].arn
  }

  tags = local.common_tags
}

resource "aws_cognito_user_group" "guest_clients" {
  count = var.enable_cognito ? 1 : 0

  name         = local.cognito_guest_group_name
  user_pool_id = aws_cognito_user_pool.main[0].id
  description  = "Read-only RelayDesk console access"
}

resource "aws_cognito_user_group" "approved_clients" {
  count = var.enable_cognito ? 1 : 0

  name         = local.cognito_approved_group_name
  user_pool_id = aws_cognito_user_pool.main[0].id
  description  = "Can upload and delete knowledge-base documents"
}

resource "aws_cognito_user_group" "relaydesk_admins" {
  count = var.enable_cognito ? 1 : 0

  name         = local.cognito_admin_group_name
  user_pool_id = aws_cognito_user_pool.main[0].id
  description  = "Full RelayDesk console and API access"
}

resource "aws_cognito_user_pool_domain" "main" {
  count = var.enable_cognito ? 1 : 0

  domain       = "${var.project_name}-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main[0].id
}

resource "aws_cognito_resource_server" "api" {
  count = var.enable_cognito ? 1 : 0

  identifier   = "relaydesk-api"
  name         = "RelayDesk API"
  user_pool_id = aws_cognito_user_pool.main[0].id

  scope {
    scope_name        = "access"
    scope_description = "Access RelayDesk REST API"
  }
}

resource "aws_cognito_user_pool_client" "ui" {
  count = var.enable_cognito ? 1 : 0

  name         = "${local.name_prefix}-ui"
  user_pool_id = aws_cognito_user_pool.main[0].id

  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes = [
    "email",
    "openid",
    "profile",
    "${aws_cognito_resource_server.api[0].identifier}/access",
  ]
  supported_identity_providers = compact([
    "COGNITO",
    var.enable_cognito_google ? "Google" : null,
  ])
  callback_urls = local.cognito_callback_urls
  logout_urls   = local.cognito_logout_urls

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"

  # Google must exist on the pool before the app client can list it as a provider.
  depends_on = [aws_cognito_identity_provider.google]
}

resource "aws_cognito_user_pool_client" "voice_m2m" {
  count = var.enable_cognito ? 1 : 0

  name         = "${local.name_prefix}-voice-m2m"
  user_pool_id = aws_cognito_user_pool.main[0].id

  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["client_credentials"]
  allowed_oauth_scopes = [
    "${aws_cognito_resource_server.api[0].identifier}/access",
  ]
  supported_identity_providers = ["COGNITO"]
}

# Google OAuth credentials live in SSM (synced separately). Terraform only reads them.
data "aws_ssm_parameter" "cognito_google_client_id" {
  count = local.cognito_enabled && var.enable_cognito_google ? 1 : 0

  name            = "${local.ssm_prefix_cognito}/GOOGLE_CLIENT_ID"
  with_decryption = true

  depends_on = [aws_ssm_parameter.cognito]
}

data "aws_ssm_parameter" "cognito_google_client_secret" {
  count = local.cognito_enabled && var.enable_cognito_google ? 1 : 0

  name            = "${local.ssm_prefix_cognito}/GOOGLE_CLIENT_SECRET"
  with_decryption = true

  depends_on = [aws_ssm_parameter.cognito]
}

resource "aws_cognito_identity_provider" "google" {
  count = local.cognito_enabled && var.enable_cognito_google ? 1 : 0

  user_pool_id  = aws_cognito_user_pool.main[0].id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    authorize_scopes = "email openid profile"
    client_id        = data.aws_ssm_parameter.cognito_google_client_id[0].value
    client_secret    = data.aws_ssm_parameter.cognito_google_client_secret[0].value
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
  }
}

## NOTE:
## Cognito-native + Google federation.
## Google client ID/secret are stored in SSM under local.ssm_prefix_cognito
## (not in terraform.tfvars). Sync values before enable_cognito_google=true.
