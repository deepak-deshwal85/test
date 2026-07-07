resource "aws_db_subnet_group" "postgres" {
  count = var.enable_rds_postgres ? 1 : 0

  name       = "${local.name_prefix}-postgres"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${local.name_prefix}-postgres-subnets"
  }
}

resource "aws_security_group" "rds_postgres" {
  count = var.enable_rds_postgres ? 1 : 0

  name        = "${local.name_prefix}-rds-postgres"
  description = "PostgreSQL access from ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-rds-postgres"
  }
}

resource "aws_db_instance" "postgres" {
  count = var.enable_rds_postgres ? 1 : 0

  identifier             = "${local.name_prefix}-postgres"
  engine                 = "postgres"
  engine_version         = var.rds_engine_version
  instance_class         = var.rds_instance_class
  allocated_storage      = var.rds_allocated_storage
  max_allocated_storage  = 100
  db_name                = var.rds_database_name
  username               = var.rds_master_username
  password               = var.rds_master_password
  port                   = 5432
  db_subnet_group_name   = aws_db_subnet_group.postgres[0].name
  vpc_security_group_ids = [aws_security_group.rds_postgres[0].id]

  multi_az               = false
  publicly_accessible    = false
  storage_encrypted      = true
  deletion_protection    = false
  skip_final_snapshot    = true
  backup_retention_period = 7

  lifecycle {
    ignore_changes = [password]
  }

  tags = {
    Name = "${local.name_prefix}-postgres"
  }
}
