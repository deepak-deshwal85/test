# RelayDesk UI

Next.js 15 operations console for RelayDesk: dashboard, customers, call jobs, knowledge-base upload, semantic search, and collection management. Authenticates users via **AWS Cognito** (NextAuth.js) and proxies API calls with OAuth access tokens.

[← Back to monorepo](../README.md) · **Infrastructure:** [`../infra/README.md`](../infra/README.md)

---

## 1. Description

### What it does

- **Dashboard** — API health, customer/collection counts (scoped by tenant).
- **Login** — Cognito SSO via `/login`.
- **Customers** — List and manage consumers per `client_email_id`.
- **Call jobs** — Trigger and monitor outbound campaigns (admin).
- **Knowledge** — Upload documents to phone-scoped Qdrant collections.
- **Search** — Natural-language search over uploaded knowledge.
- **Collections** — Browse vector collections.

### Role-based UI

| Cognito group | UI capability |
|---------------|-----------------|
| `guest-clients` | View-only (default after SSO) |
| `approved-clients` | Upload/delete documents |
| `relaydesk-admins` | Full access including customer create, call-job trigger |

### Stack

Next.js 15 · TypeScript · Tailwind CSS 4 · NextAuth v5 · Server-side API proxy (`/api/backend/*`)

---

## 2. Run locally

### Prerequisites

- Node.js 22+
- RelayDesk API running locally (see [`../api/README.md`](../api/README.md)) — RDS tunnel + Qdrant Cloud

### Configure environment

```bash
cd ui
cp .env.example .env
npm install
```

| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH_SECRET` | Yes | `openssl rand -base64 32` |
| `AUTH_URL` | Yes | `http://localhost:3000` (must match browser URL) |
| `AUTH_DISABLE_SSO` | Local | `true` — skip Cognito, use local dev user |
| `COGNITO_ISSUER` | SSO | `https://cognito-idp.<region>.amazonaws.com/<pool-id>` |
| `COGNITO_CLIENT_ID` | SSO | Cognito UI app client ID |
| `COGNITO_CLIENT_SECRET` | SSO | Cognito UI app client secret |
| `COGNITO_SCOPE` | SSO | `relaydesk-api/access` |
| `RELAYDESK_API_TARGET` | Routing | `local` \| `aws` \| `auto` |
| `RELAYDESK_API_URL_LOCAL` | Local API | `http://127.0.0.1:8090` |
| `RELAYDESK_API_URL_AWS` | Production API | `https://relaydesk.uk` |

**Local without SSO:** set `AUTH_DISABLE_SSO=true` in UI and `OAUTH_DISABLED=true` in API.

### Start dev server

```bash
npm run dev
```

From repo root (Windows): `infra\scripts\start_local_ui.bat`

Open http://localhost:3000

### Production build (verify before Docker)

```bash
npm run build
npm start   # optional smoke test on :3000
```

---

## 3. Docker build, push to ECR, update ECS

Run from **repo root**. **`npm run build` must succeed** inside Docker before you push — a failed build leaves the old image on ECR.

```bash
export PROFILE_NAME="relaydesk-admin"
export AWS_REGION="ap-south-1"
export IMAGE_TAG="latest"    # match ui_ecr_image_tag in terraform.tfvars

cd infra/terraform
export ACCOUNT_ID="$(terraform output -raw aws_account_id)"
export ECR_UI="$(terraform output -raw ecr_ui_repository_url)"
export CLUSTER="$(terraform output -raw ecs_cluster_name)"
export SERVICE="$(terraform output -raw ecs_service_ui_name)"
cd ../..

echo "ECR_UI=$ECR_UI IMAGE_TAG=$IMAGE_TAG"

aws ecr get-login-password --profile "$PROFILE_NAME" --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
    "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker build -t relaydesk-ui:latest ./ui
docker tag relaydesk-ui:latest "${ECR_UI}:${IMAGE_TAG}"
docker tag relaydesk-ui:latest "${ECR_UI}:latest"
docker push "${ECR_UI}:${IMAGE_TAG}"
docker push "${ECR_UI}:latest"

aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --force-new-deployment \
  --profile "$PROFILE_NAME" \
  --region "$AWS_REGION"
```

### Production OAuth

- Callback URL: `https://<your-domain>/api/auth/callback/cognito`
- Set `AUTH_URL=https://<your-domain>` in SSM (`/relaydesk/prod/ui/AUTH_URL`)
- Terraform output: `terraform output cognito_callback_urls`

---

## 4. Scripts and npm commands

This project has no `scripts/` folder. Use these **npm** commands from `ui/`:

| Command | Purpose |
|---------|---------|
| `npm run dev` | Development server with hot reload |
| `npm run build` | Production build (required before Docker image) |
| `npm start` | Run production build locally |
| `npm run lint` | ESLint |

### Related infra scripts (SSO / secrets)

| Script | Purpose |
|--------|---------|
| [`../infra/scripts/sync_ssm_parameters.py`](../infra/scripts/sync_ssm_parameters.py) | Push `ui/.env` values to SSM |
| [`../infra/scripts/approve_cognito_user.py`](../infra/scripts/approve_cognito_user.py) | Promote user to `approved-clients` or `relaydesk-admins` |
| [`../infra/scripts/backfill_guest_clients.py`](../infra/scripts/backfill_guest_clients.py) | Add `guest-clients` group to existing users |

---

## Project layout

```
ui/
├── src/
│   ├── app/              # Pages (login, dashboard, customers, …)
│   ├── components/       # AppShell, profile form, UI primitives
│   ├── hooks/            # usePermissions, useClientProfile
│   └── lib/              # auth, api-client, cognito helpers
├── Dockerfile            # Multi-stage Next.js standalone
├── .env.example
└── README.md
```
