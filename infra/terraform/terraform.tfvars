aws_region   = "ap-south-1"
environment  = "prod"
project_name = "relaydesk"

# Required: your GitHub org or username (for OIDC deploy role trust)
github_org  = "YOUR_GITHUB_ORG_OR_USER"
github_repo = "relaydesk"

# Shared EC2 host (t3.large fits API 512 MiB + voice 8192 MiB)
ecs_instance_type             = "t3.large"
ecs_instance_desired_capacity = 1
api_ecr_image_tag             = "latest"
voice_ecr_image_tag           = "v1"

voice_agent_desired_count = 1
voice_agent_cpu           = 2048   # 2 vCPU
voice_agent_memory        = 8192   # 8 GiB

# Set true only if you need to upload documents from the public internet
api_publicly_accessible = false

# Set false if GitHub OIDC provider already exists in this AWS account
manage_github_oidc_provider = true

# Must match aws_region — Mumbai only (avoid ap-south-1c)
availability_zones = ["ap-south-1a", "ap-south-1b"]

# RDS PostgreSQL (used by API DATABASE_URL)
enable_rds_postgres = true
rds_engine_version  = "16.14"
rds_instance_class  = "db.t3.micro"
rds_database_name   = "relaydesk"
rds_master_username = "relaydesk_admin"

# Cost monitoring
enable_cost_monitoring = true
monthly_budget_usd     = 75
# budget_alert_emails  = ["you@example.com"]
