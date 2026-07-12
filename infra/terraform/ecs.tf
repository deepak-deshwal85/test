data "aws_ssm_parameter" "ecs_optimized_ami" {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended/image_id"
}

locals {
  # Separate EC2 pools — API and voice agent do not share a host.
  ecs_host_pools = {
    api = {
      instance_type    = var.api_ecs_instance_type
      desired_capacity = var.api_ecs_instance_desired_capacity
      min_size         = var.api_ecs_instance_min_size
      max_size         = var.api_ecs_instance_max_size
    }
    voice = {
      instance_type    = var.voice_ecs_instance_type
      desired_capacity = var.voice_agent_desired_count > 0 ? var.voice_ecs_instance_desired_capacity : 0
      min_size         = var.voice_agent_desired_count > 0 ? var.voice_ecs_instance_min_size : 0
      max_size         = var.voice_ecs_instance_max_size
    }
  }
}

resource "aws_ecs_cluster" "main" {
  name = local.name_prefix

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }
}

resource "aws_launch_template" "ecs" {
  for_each = local.ecs_host_pools

  name_prefix   = "${local.name_prefix}-ecs-${each.key}-"
  image_id      = data.aws_ssm_parameter.ecs_optimized_ami.value
  instance_type = each.value.instance_type

  iam_instance_profile {
    name = aws_iam_instance_profile.ecs.name
  }

  vpc_security_group_ids = [aws_security_group.ecs_instances.id]

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 30
      volume_type           = "gp2"
      delete_on_termination = true
      encrypted             = true
    }
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    echo ECS_CLUSTER=${aws_ecs_cluster.main.name} >> /etc/ecs/ecs.config
    echo ECS_ENABLE_CONTAINER_METADATA=true >> /etc/ecs/ecs.config
  EOF
  )

  monitoring {
    enabled = var.enable_ec2_detailed_monitoring
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${local.name_prefix}-ecs-${each.key}"
      Role = each.key
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_autoscaling_group" "ecs" {
  for_each = local.ecs_host_pools

  name                = "${local.name_prefix}-ecs-${each.key}"
  vpc_zone_identifier = aws_subnet.private[*].id
  min_size            = each.value.min_size
  max_size            = each.value.max_size
  desired_capacity    = each.value.desired_capacity

  launch_template {
    id      = aws_launch_template.ecs[each.key].id
    version = "$Latest"
  }

  health_check_type         = "EC2"
  health_check_grace_period = 300
  protect_from_scale_in     = true

  tag {
    key                 = "Name"
    value               = "${local.name_prefix}-ecs-${each.key}"
    propagate_at_launch = true
  }

  tag {
    key                 = "AmazonECSManaged"
    value               = "true"
    propagate_at_launch = true
  }

  tag {
    key                 = "Role"
    value               = each.key
    propagate_at_launch = true
  }

  lifecycle {
    ignore_changes = [desired_capacity]
  }
}

resource "aws_ecs_capacity_provider" "ec2" {
  for_each = local.ecs_host_pools

  name = "${local.name_prefix}-ecs-${each.key}"

  auto_scaling_group_provider {
    auto_scaling_group_arn         = aws_autoscaling_group.ecs[each.key].arn
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

  capacity_providers = [
    aws_ecs_capacity_provider.ec2["api"].name,
    aws_ecs_capacity_provider.ec2["voice"].name,
  ]
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
      interval    = 15
      timeout     = 5
      retries     = 2
      startPeriod = 20
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

    secrets = concat(
      [
        for key in local.voice_agent_secret_keys : {
          name      = key
          valueFrom = aws_ssm_parameter.voice_agent[key].arn
        }
      ],
      local.cognito_enabled ? [{
        name      = "COGNITO_CLIENT_SECRET"
        valueFrom = aws_ssm_parameter.cognito_voice_client_secret[0].arn
      }] : []
    )

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
    capacity_provider = aws_ecs_capacity_provider.ec2["api"].name
    weight            = 1
    base              = 1
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

  # API and UI share the api EC2 pool (t3.small ENI limit). Allow stop-before-start deploys.
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  depends_on = [
    aws_lb_listener.api,
    aws_lb_listener_rule.api_paths,
  ]
}

resource "aws_ecs_service" "voice_agent" {
  name            = "${local.name_prefix}-voice-agent"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.voice_agent.arn
  desired_count   = var.voice_agent_desired_count
  launch_type     = null

  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.ec2["voice"].name
    weight            = 1
    base              = 1
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
}
