# Build context: repo root (for pnpm-workspace.yaml + afters-shared).
# Railway service settings: leave Root Directory blank, set Dockerfile Path
# to "afters-dashboard/Dockerfile". Set NEXT_PUBLIC_ORCHESTRATOR_BASE_URL and
# NEXT_PUBLIC_MESSAGING_BASE_URL as build-time variables on the Railway
# service so they get baked into the client bundle here.

# ---------- base ----------
FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
ENV PNPM_HOME="/root/.local/share/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

# ---------- builder ----------
FROM base AS builder
WORKDIR /app

# Manifests first for layer cache.
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
COPY afters-shared/package.json afters-shared/package.json
COPY afters-dashboard/package.json afters-dashboard/package.json

RUN pnpm install --frozen-lockfile --filter "afters-dashboard..."

# Source.
COPY afters-shared afters-shared
COPY afters-dashboard afters-dashboard

# NEXT_PUBLIC_* values are baked into the client bundle at build time.
# Defaults are placeholders; Railway should pass real values via build args.
ARG NEXT_PUBLIC_ORCHESTRATOR_BASE_URL=""
ARG NEXT_PUBLIC_MESSAGING_BASE_URL=""
ENV NEXT_PUBLIC_ORCHESTRATOR_BASE_URL=${NEXT_PUBLIC_ORCHESTRATOR_BASE_URL}
ENV NEXT_PUBLIC_MESSAGING_BASE_URL=${NEXT_PUBLIC_MESSAGING_BASE_URL}

# Public dir is optional; create it so the runtime COPY does not fail on a
# fresh repo that has no static assets yet.
RUN mkdir -p afters-dashboard/public

RUN pnpm --filter afters-dashboard build

# ---------- runtime ----------
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN apk add --no-cache tini

# Standalone output is a self-contained Node.js server: server.js, the minimal
# node_modules it needs, and the workspace-aware tracing root layout. Static
# assets and the public folder need to be copied alongside, per Next.js docs.
COPY --from=builder /app/afters-dashboard/.next/standalone ./
COPY --from=builder /app/afters-dashboard/.next/static ./afters-dashboard/.next/static
COPY --from=builder /app/afters-dashboard/public ./afters-dashboard/public

EXPOSE 3000
ENTRYPOINT ["/sbin/tini", "--"]
WORKDIR /app/afters-dashboard
CMD ["node", "server.js"]
