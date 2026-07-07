locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
  }

  ecr_api_repo         = "${var.project_name}-api"
  ecr_voice_agent_repo = "${var.project_name}-voice-agent"

  ssm_prefix_api         = "/${var.project_name}/${var.environment}/api"
  ssm_prefix_voice_agent = "/${var.project_name}/${var.environment}/voice-agent"

  api_image   = "${aws_ecr_repository.api.repository_url}:${var.api_ecr_image_tag}"
  voice_image = "${aws_ecr_repository.voice_agent.repository_url}:${var.voice_ecr_image_tag}"

  service_discovery_namespace = "${var.project_name}.local"
  api_service_dns             = "api.${local.service_discovery_namespace}"
  # Internal ALB DNS always resolves inside the VPC; Cloud Map only has records while API tasks are healthy.
  api_rag_base_url = "http://${aws_lb.api.dns_name}"

  # Non-secret env injected into tasks
  api_environment = [
    { name = "RAG_API_HOST", value = "0.0.0.0" },
    { name = "RAG_API_PORT", value = "8090" },
    { name = "RAG_BACKEND", value = "qdrant" },
  ]

  voice_agent_environment = [
    { name = "RAG_BACKEND", value = "qdrant" },
    { name = "RAG_API_BASE_URL", value = local.api_rag_base_url },
    { name = "AGENT_NAME", value = "relaydesk-agent" },
    { name = "TURN_ENDPOINTING_MAX_DELAY", value = "1.0" },
    { name = "TURN_ENDPOINTING_MIN_DELAY", value = "0.3" },
  ]

  api_secret_keys = [
    "OPENAI_API_KEY",
    "DATABASE_URL",
    "RAG_API_KEY",
    "QDRANT_API_KEY",
    "QDRANT_CLUSTER_ENDPOINT",
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "LIVEKIT_SIP_OUTBOUND_TRUNK_ID",
  ]

  voice_agent_secret_keys = [
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "XAI_API_KEY",
    "DEEPGRAM_API_KEY",
    "CARTESIA_API_KEY",
    "CALCOM_API_KEY",
    "RAG_API_KEY",
  ]
}
