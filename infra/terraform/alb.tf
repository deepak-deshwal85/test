resource "aws_lb" "api" {
  name               = "${local.name_prefix}-api"
  internal           = !local.alb_public
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_api.id]
  subnets            = local.alb_public ? aws_subnet.public[*].id : aws_subnet.private[*].id

  tags = {
    Name = "${local.name_prefix}-api-alb"
  }
}

resource "aws_lb_target_group" "api" {
  name        = "${local.name_prefix}-api"
  port        = 8090
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }
}

# HTTP: redirect to HTTPS when ui_domain_name is set; otherwise forward to UI/API.
resource "aws_lb_listener" "api" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = local.ui_https_enabled ? "redirect" : "forward"

    target_group_arn = local.ui_https_enabled ? null : (
      var.enable_ui ? aws_lb_target_group.ui[0].arn : aws_lb_target_group.api.arn
    )

    dynamic "redirect" {
      for_each = local.ui_https_enabled ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}

resource "aws_lb_listener_rule" "api_paths" {
  count = var.enable_ui && !local.ui_https_enabled ? 1 : 0

  listener_arn = aws_lb_listener.api.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      # ALB listener rules allow max 5 path condition values.
      values = ["/v1*", "/health", "/docs*", "/openapi.json", "/redoc"]
    }
  }
}
