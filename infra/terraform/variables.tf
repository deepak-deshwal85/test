variable "aws_region" {
  description = "AWS region (ap-south-1 recommended for India callers)."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Prefix for resource names."
  type        = string
  default     = "relaydesk"
}

variable "environment" {
  description = "Environment name (prod, staging)."
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "ecs_instance_type" {
  description = "EC2 type for ECS container instances. t3.micro is Free Tier eligible (1 vCPU burst, 1 GiB RAM) — fits API only; scale up for voice-agent."
  type        = string
  default     = "t3.micro"
}

variable "ecs_instance_desired_capacity" {
  type    = number
  default = 1
}

variable "ecs_instance_min_size" {
  type    = number
  default = 1
}

variable "ecs_instance_max_size" {
  type    = number
  default = 1
}

variable "api_publicly_accessible" {
  description = "If true, API ALB is internet-facing. If false, internal ALB only (voice agent still reaches API via Cloud Map)."
  type        = bool
  default     = false
}

variable "github_org" {
  description = "GitHub organization or username for OIDC trust."
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name (without org)."
  type        = string
  default     = "relaydesk"
}

variable "github_branch" {
  description = "Branch allowed to deploy via OIDC."
  type        = string
  default     = "main"
}

variable "manage_github_oidc_provider" {
  description = "Create GitHub OIDC provider in this account. Set false if it already exists."
  type        = bool
  default     = true
}

variable "voice_agent_cpu" {
  type    = number
  default = 1024
}

variable "voice_agent_memory" {
  description = "Voice agent needs several GiB; not runnable on t3.micro. Increase instance + memory before setting voice_agent_desired_count > 0."
  type        = number
  default     = 5120
}

variable "api_cpu" {
  type    = number
  default = 256
}

variable "api_memory" {
  type    = number
  default = 512
}

variable "api_desired_count" {
  type    = number
  default = 1
}

variable "voice_agent_desired_count" {
  description = "Set to 0 on Free Tier (t3.micro cannot run the voice agent). Run voice-agent locally or scale EC2 first."
  type        = number
  default     = 0
}

variable "availability_zones" {
  description = "Two AZs for VPC subnets. ap-south-1c lacks NAT, ALB, and gp3 — use a+b in Mumbai."
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "Provide exactly two availability zones."
  }
}

variable "log_retention_days" {
  type    = number
  default = 7
}
