###############################################
# Custom domain HTTPS (Cloudflare DNS + ACM on ALB)
# DNS is managed in Cloudflare — Terraform outputs the records to create.
###############################################

locals {
  ui_https_enabled = var.ui_domain_name != "" && local.alb_public

  ui_public_base_url = local.ui_https_enabled ? (
    "https://${var.ui_domain_name}"
  ) : "http://${aws_lb.api.dns_name}"

  cognito_callback_urls = distinct(concat(
    var.cognito_ui_callback_urls,
    local.ui_https_enabled ? [
      "https://${var.ui_domain_name}/api/auth/callback/cognito",
    ] : [],
  ))

  cognito_logout_urls = distinct(concat(
    var.cognito_ui_logout_urls,
    local.ui_https_enabled ? [
      "https://${var.ui_domain_name}/login",
    ] : [],
  ))
}

resource "aws_acm_certificate" "ui" {
  count = local.ui_https_enabled ? 1 : 0

  domain_name       = var.ui_domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = local.common_tags
}

resource "aws_acm_certificate_validation" "ui" {
  count = local.ui_https_enabled ? 1 : 0

  certificate_arn = aws_acm_certificate.ui[0].arn
  validation_record_fqdns = [
    for dvo in aws_acm_certificate.ui[0].domain_validation_options : dvo.resource_record_name
  ]
}

resource "aws_lb_listener" "api_https" {
  count = local.ui_https_enabled ? 1 : 0

  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.ui[0].certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = var.enable_ui ? aws_lb_target_group.ui[0].arn : aws_lb_target_group.api.arn
  }

  depends_on = [aws_acm_certificate_validation.ui]
}

resource "aws_lb_listener_rule" "api_paths_https" {
  count = var.enable_ui && local.ui_https_enabled ? 1 : 0

  listener_arn = aws_lb_listener.api_https[0].arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/v1*", "/health", "/docs*", "/openapi.json", "/redoc"]
    }
  }
}
