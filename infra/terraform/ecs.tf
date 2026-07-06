data "aws_ssm_parameter" "ecs_optimized_ami" {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended/image_id"
}

resource "aws_ecs_cluster" "main" {
  name = local.name_prefix

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_launch_template" "ecs" {
  name_prefix   = "${local.name_prefix}-ecs-"
  image_id      = data.aws_ssm_parameter.ecs_optimized_ami.value
  instance_type = var.ecs_instance_type

  iam_instance_profile {
    name = aws_iam_instance_profile.ecs.name
  }

  vpc_security_group_ids = [aws_security_group.ecs_instances.id]

  user_data = base64encode(<<-EOF
    #!/bin/bash
    echo ECS_CLUSTER=${aws_ecs_cluster.main.name} >> /etc/ecs/ecs.config
    echo ECS_ENABLE_CONTAINER_METADATA=true >> /etc/ecs/ecs.config
  EOF
  )

  monitoring {
    enabled = true
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${local.name_prefix}-ecs"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_autoscaling_group" "ecs" {
  name                = "${local.name_prefix}-ecs"
  vpc_zone_identifier = aws_subnet.private[*].id
  min_size            = var.ecs_instance_min_size
  max_size            = var.ecs_instance_max_size
  desired_capacity    = var.ecs_instance_desired_capacity

  launch_template {
    id      = aws_launch_template.ecs.id
    version = "$Latest"
  }

  health_check_type         = "EC2"
  health_check_grace_period = 300
  protect_from_scale_in     = true

  tag {
    key                 = "Name"
    value               = "${local.name_prefix}-ecs"
    propagate_at_launch = true
  }

  tag {
    key                 = "AmazonECSManaged"
    value               = "true"
    propagate_at_launch = true
  }

  lifecycle {
    ignore_changes = [desired_capacity]
  }
}

resource "aws_ecs_capacity_provider" "ec2" {
  name = "${local.name_prefix}-ec2"

  auto_scaling_group_provider {
    auto_scaling_group_arn         = aws_autoscaling_group.ecs.arn
    managed_termination_protection = "ENABLED"

    managed_scaling {
      status                    = "ENABLED"
      target_capacity           = 85
      minimum_scaling_step_size = 1
      maximum_scaling_step_size = 2
    }
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = [aws_ecs_capacity_provider.ec2.name]

  default_capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.ec2.name
    weight            = 1
    base              = 1
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name_prefix}-api"
  requires_compatibilities = ["EC2"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = local.api_image
    essential = true
    cpu       = var.api_cpu
    memory    = var.api_memory

    portMappings = [{
      containerPort = 8090
      hostPort      = 8090
      protocol      = "tcp"
    }]

    environment = local.api_environment

    secrets = [
      for key in local.api_secret_keys : {
        name      = key
        valueFrom = aws_ssm_parameter.api[key].arn
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "api"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8090/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

resource "aws_ecs_task_definition" "voice_agent" {
  family                   = "${local.name_prefix}-voice-agent"
  requires_compatibilities = ["EC2"]
  network_mode             = "awsvpc"
  cpu                      = var.voice_agent_cpu
  memory                   = var.voice_agent_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "voice-agent"
    image     = local.voice_image
    essential = true
    cpu       = var.voice_agent_cpu
    memory    = var.voice_agent_memory

    environment = local.voice_agent_environment

    secrets = [
      for key in local.voice_agent_secret_keys : {
        name      = key
        valueFrom = aws_ssm_parameter.voice_agent[key].arn
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.voice_agent.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "voice-agent"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "${local.name_prefix}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = null

  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.ec2.name
    weight            = 1
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8090
  }

  service_registries {
    registry_arn = aws_service_discovery_service.api.arn
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  depends_on = [aws_lb_listener.api]
}

resource "aws_ecs_service" "voice_agent" {
  name            = "${local.name_prefix}-voice-agent"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.voice_agent.arn
  desired_count   = var.voice_agent_desired_count
  launch_type     = null

  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.ec2.name
    weight            = 1
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
}
