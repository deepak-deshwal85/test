resource "aws_iam_role" "cognito_assign_guest_role" {
  count = var.enable_cognito ? 1 : 0

  name = "${local.name_prefix}-cognito-assign-guest"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "cognito_assign_guest_role" {
  count = var.enable_cognito ? 1 : 0

  name = "${local.name_prefix}-cognito-assign-guest"
  role = aws_iam_role.cognito_assign_guest_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:AdminAddUserToGroup",
          "cognito-idp:AdminListGroupsForUser",
        ]
        Resource = "arn:aws:cognito-idp:${var.aws_region}:${data.aws_caller_identity.current.account_id}:userpool/*"
      },
    ]
  })
}

data "archive_file" "cognito_assign_guest_role" {
  count = var.enable_cognito ? 1 : 0

  type        = "zip"
  source_file = "${path.module}/lambda/cognito_assign_guest_role/index.py"
  output_path = "${path.module}/lambda/cognito_assign_guest_role/package.zip"
}

resource "aws_lambda_function" "cognito_assign_guest_role" {
  count = var.enable_cognito ? 1 : 0

  function_name = "${local.name_prefix}-cognito-assign-guest"
  role          = aws_iam_role.cognito_assign_guest_role[0].arn
  handler       = "index.handler"
  runtime       = "python3.13"
  timeout       = 10

  filename         = data.archive_file.cognito_assign_guest_role[0].output_path
  source_code_hash = data.archive_file.cognito_assign_guest_role[0].output_base64sha256

  environment {
    variables = {
      GUEST_GROUP     = local.cognito_guest_group_name
      ELEVATED_GROUPS = "${local.cognito_approved_group_name},${local.cognito_admin_group_name}"
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.cognito_assign_guest_role]
}

resource "aws_lambda_permission" "cognito_assign_guest_role" {
  count = var.enable_cognito ? 1 : 0

  statement_id  = "AllowCognitoPostConfirmation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cognito_assign_guest_role[0].function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main[0].arn
}

resource "aws_cloudwatch_log_group" "cognito_assign_guest_role" {
  count = var.enable_cognito ? 1 : 0

  name              = "/aws/lambda/${aws_lambda_function.cognito_assign_guest_role[0].function_name}"
  retention_in_days = 14
  tags              = local.common_tags
}
