variable "aws_region" {
  description = "AWS region (ap-south-1 recommended for India callers)."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Prefix for resource names."
  type        = string
  default     = "telephone-agent"
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
  description = "EC2 type for ECS container instances (t3.xlarge fits voice-agent + API on one node)."
  type        = string
  default     = "t3.xlarge"
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
  default = 3
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
  default     = "telephone-agent"
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
  default = 2048
}

variable "voice_agent_memory" {
  type    = number
  default = 8192
}

variable "api_cpu" {
  type    = number
  default = 512
}

variable "api_memory" {
  type    = number
  default = 1024
}

variable "api_desired_count" {
  type    = number
  default = 1
}

variable "voice_agent_desired_count" {
  type    = number
  default = 1
}

variable "log_retention_days" {
  type    = number
  default = 14
}
