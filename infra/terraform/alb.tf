resource "aws_lb" "api" {
  name               = "${local.name_prefix}-api"
  internal           = !var.api_publicly_accessible
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_api.id]
  subnets            = var.api_publicly_accessible ? aws_subnet.public[*].id : aws_subnet.private[*].id

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

resource "aws_lb_listener" "api" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}
