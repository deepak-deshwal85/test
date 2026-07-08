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

  tags = local.common_tags
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
    var.cognito_google_client_id != "" ? "Google" : null,
  ])
  callback_urls = local.cognito_callback_urls
  logout_urls   = local.cognito_logout_urls

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"
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

resource "aws_cognito_identity_provider" "google" {
  count = var.enable_cognito && var.cognito_google_client_id != "" ? 1 : 0

  user_pool_id  = aws_cognito_user_pool.main[0].id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    authorize_scopes = "email openid profile"
    client_id        = var.cognito_google_client_id
    client_secret    = var.cognito_google_client_secret
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
  }
}

## NOTE:
## This stack intentionally uses Cognito-native + Google federation only.
