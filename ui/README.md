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

End users sign in with **GitHub** or **Google** via [NextAuth.js](https://authjs.dev). The UI never exposes `RAG_API_KEY` to the browser — authenticated server routes proxy requests to the FastAPI backend.

### OAuth setup

1. Copy `.env.example` to `.env.local`
2. Generate `AUTH_SECRET`: `openssl rand -base64 32`
3. Create OAuth apps:
   - **GitHub**: Settings → Developer settings → OAuth Apps  
     Callback: `http://localhost:3000/api/auth/callback/github`
   - **Google**: Cloud Console → APIs & Credentials → OAuth client  
     Callback: `http://localhost:3000/api/auth/callback/google`
4. Set `RELAYDESK_API_URL` and `RAG_API_KEY` to match your running API

## Local development

```bash
cd ui
npm install
cp .env.example .env.local
# edit .env.local
npm run dev
```

Open http://localhost:3000

Ensure the API is running (`cd api && uv run uvicorn app.main:app --host 127.0.0.1 --port 8090`).

## Production (ECS)

The UI runs as a Next.js standalone container on the shared ALB:

- Browser → ALB `:80` → UI (`:3000`)
- API routes → ALB `/v1/*`, `/health`, `/docs` → API (`:8090`)

Set OAuth callback URLs to `https://<your-alb-or-domain>/api/auth/callback/<provider>`.

## Stack rationale

| Choice | Why |
|--------|-----|
| Next.js 15 | SSR for auth, API proxy, industry-standard React framework |
| TypeScript | Type-safe API contracts, matches modern full-stack practice |
| Tailwind CSS 4 | Responsive mobile-first styling with minimal bundle size |
| NextAuth v5 | Native GitHub/Google OAuth, JWT sessions, ECS-compatible |
