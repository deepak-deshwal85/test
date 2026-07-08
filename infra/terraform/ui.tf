resource "aws_lb_target_group" "ui" {
  count = var.enable_ui ? 1 : 0

  name        = "${local.name_prefix}-ui"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/login"
    matcher             = "200-399"
  }
}

resource "aws_ecs_task_definition" "ui" {
  count = var.enable_ui ? 1 : 0

  family                   = "${local.name_prefix}-ui"
  requires_compatibilities = ["EC2"]
  network_mode             = "awsvpc"
  cpu                      = var.ui_cpu
  memory                   = var.ui_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "ui"
    image     = local.ui_image
    essential = true
    cpu       = var.ui_cpu
    memory    = var.ui_memory

    portMappings = [{
      containerPort = 3000
      hostPort      = 3000
      protocol      = "tcp"
    }]

    environment = local.ui_environment

    secrets = concat(
      [
        for key in local.ui_secret_keys : {
          name      = key
          valueFrom = aws_ssm_parameter.ui[key].arn
        }
      ],
      local.cognito_enabled ? [{
        name      = "COGNITO_CLIENT_SECRET"
        valueFrom = aws_ssm_parameter.cognito_ui_client_secret[0].arn
      }] : []
    )

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.ui[0].name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "ui"
      }
    }
  }])
}

resource "aws_ecs_service" "ui" {
  count = var.enable_ui ? 1 : 0

  name            = "${local.name_prefix}-ui"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ui[0].arn
  desired_count   = var.ui_desired_count
  launch_type     = null

  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.ec2["api"].name
    weight            = 1
    base              = 0
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ui[0].arn
    container_name   = "ui"
    container_port   = 3000
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  depends_on = [
    aws_lb_listener.api,
    aws_lb_listener_rule.api_paths,
  ]
}
