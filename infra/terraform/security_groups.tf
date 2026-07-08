resource "aws_security_group" "alb_api" {
  name        = "${local.name_prefix}-alb-api"
  description = "ALB for RAG API"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = local.alb_public ? ["0.0.0.0/0"] : [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-alb-api"
  }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "${local.name_prefix}-ecs-tasks"
  description = "ECS tasks (API + voice agent)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "API from ALB"
    from_port       = 8090
    to_port         = 8090
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_api.id]
  }

  ingress {
    description     = "UI from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_api.id]
  }

  ingress {
    description = "API from VPC (voice agent via Cloud Map)"
    from_port   = 8090
    to_port     = 8090
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-ecs-tasks"
  }
}

resource "aws_security_group" "ecs_instances" {
  name        = "${local.name_prefix}-ecs-instances"
  description = "EC2 hosts for ECS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Container host traffic within VPC"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-ecs-instances"
  }
}
