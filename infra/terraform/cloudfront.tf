###############################################
# CloudFront HTTPS front door (no custom domain)
# Cognito requires HTTPS for non-localhost callbacks.
# AWS provides https://*.cloudfront.net with a managed cert.
#
# If CreateDistribution returns AccessDenied / "account must be verified":
# open AWS Support → Account and billing → request CloudFront access,
# then set enable_https = true and re-apply.
###############################################

locals {
  # When UI + Cognito are on, front the public ALB with CloudFront for HTTPS.
  enable_cloudfront = var.enable_https && var.enable_ui && local.alb_public

  ui_public_base_url = local.enable_cloudfront ? (
    "https://${aws_cloudfront_distribution.ui[0].domain_name}"
  ) : "http://${aws_lb.api.dns_name}"

  cognito_callback_urls = distinct(concat(
    var.cognito_ui_callback_urls,
    local.enable_cloudfront ? [
      "https://${aws_cloudfront_distribution.ui[0].domain_name}/api/auth/callback/cognito"
    ] : [],
  ))

  cognito_logout_urls = distinct(concat(
    var.cognito_ui_logout_urls,
    local.enable_cloudfront ? [
      "https://${aws_cloudfront_distribution.ui[0].domain_name}/login"
    ] : [],
  ))
}

resource "aws_cloudfront_distribution" "ui" {
  count = local.enable_cloudfront ? 1 : 0

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${local.name_prefix} UI/API HTTPS"
  default_root_object = ""
  price_class         = "PriceClass_200"
  wait_for_deployment = true

  origin {
    domain_name = aws_lb.api.dns_name
    origin_id   = "alb"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Next.js + API are dynamic — do not cache by default.
  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    target_origin_id       = "alb"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = true
      headers      = ["*"]

      cookies {
        forward = "all"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  tags = {
    Name = "${local.name_prefix}-cloudfront"
  }
}
