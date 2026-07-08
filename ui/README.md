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

1. Create `ui/.env` (or `ui/.env.local`) with the variables below.
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
# create/edit .env (or .env.local)
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

## Stack rationale

| Choice | Why |
|--------|-----|
| Next.js 15 | SSR for auth, API proxy, industry-standard React framework |
| TypeScript | Type-safe API contracts, matches modern full-stack practice |
| Tailwind CSS 4 | Responsive mobile-first styling with minimal bundle size |
| NextAuth v5 | Cognito OIDC support with JWT sessions, ECS-compatible |
