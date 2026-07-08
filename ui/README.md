# RelayDesk UI

Modern operations console for the RelayDesk API. Built with **Next.js 15**, **TypeScript**, and **Tailwind CSS**.

## Features

- Dashboard with API health and quick actions
- Customer CRUD
- Outbound call job trigger and monitoring
- Knowledge base document upload per phone collection
- Semantic search across uploaded documents
- Collection administration

## Authentication

The UI uses **AWS Cognito OIDC** through [NextAuth.js](https://authjs.dev).
Browser requests never contain static API secrets; the server proxy forwards OAuth access tokens to the API.

### OAuth setup

1. Copy `ui/.env.example` to `ui/.env` (or `.env.local`) and fill values.
2. Generate `AUTH_SECRET`: `openssl rand -base64 32`
3. Set Cognito values:
   - `COGNITO_ISSUER`
   - `COGNITO_CLIENT_ID`
   - `COGNITO_CLIENT_SECRET`
4. Configure API target:
   - `RELAYDESK_API_TARGET=local|aws|auto`
   - `RELAYDESK_API_URL_LOCAL`, `RELAYDESK_API_URL_AWS`

### Local mode without SSO

Set `AUTH_DISABLE_SSO=true` to bypass login locally. This is intended for development only.
When using this mode, set API `OAUTH_DISABLED=true` (or an API instance that accepts unauthenticated local traffic).

## Local development

```bash
cd ui
npm install
cp .env.example .env
# edit .env
npm run dev
```

Open http://localhost:3000

Ensure the API is running (`cd api && uv run uvicorn app.main:app --host 127.0.0.1 --port 8090`).

## Production (ECS)

The UI runs as a Next.js standalone container on ECS.

- Browser → CloudFront/ALB → UI (`:3000`)
- API routes → ALB `/v1/*`, `/health`, `/docs` → API (`:8090`)

Set OAuth callback URL to:
- `https://<public-ui-host>/api/auth/callback/cognito`

### Docker build and push (ECR)

From the **repo root** (not `ui/`):

```bash
PROFILE_NAME="relaydesk-admin"
AWS_REGION="ap-south-1"
IMAGE_TAG="latest"   # or a version / git SHA

cd infra/terraform
ACCOUNT_ID="$(terraform output -raw aws_account_id)"
ECR_UI="$(terraform output -raw ecr_ui_repository_url)"
cd ../..

aws ecr get-login-password --profile "$PROFILE_NAME" --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
    "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker build -t relaydesk-ui:latest ./ui
docker tag relaydesk-ui:latest "${ECR_UI}:${IMAGE_TAG}"
docker tag relaydesk-ui:latest "${ECR_UI}:latest"
docker push "${ECR_UI}:${IMAGE_TAG}"
docker push "${ECR_UI}:latest"
```

Then force a new ECS deployment (optional if the service already watches `:latest`):

```bash
PROFILE_NAME="relaydesk-admin"
AWS_REGION="ap-south-1"

cd infra/terraform
CLUSTER="$(terraform output -raw ecs_cluster_name)"
SERVICE="$(terraform output -raw ecs_service_ui_name)"
cd ../..

aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --force-new-deployment \
  --profile "$PROFILE_NAME" \
  --region "$AWS_REGION"
```

## Stack rationale

| Choice | Why |
|--------|-----|
| Next.js 15 | SSR for auth, API proxy, industry-standard React framework |
| TypeScript | Type-safe API contracts, matches modern full-stack practice |
| Tailwind CSS 4 | Responsive mobile-first styling with minimal bundle size |
| NextAuth v5 | Cognito OIDC support with JWT sessions, ECS-compatible |
