# Build context: repo root (so we can see pnpm-workspace.yaml + afters-shared).
# Railway service settings: leave Root Directory blank, set Dockerfile Path
# to "afters-messaging/Dockerfile".

# ---------- base ----------
FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
ENV PNPM_HOME="/root/.local/share/pnpm"
ENV PATH="$PNPM_HOME:$PATH"

# ---------- builder ----------
FROM base AS builder
WORKDIR /app

# Copy manifests first so the install layer caches when source changes.
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
COPY afters-shared/package.json afters-shared/package.json
COPY afters-messaging/package.json afters-messaging/package.json

# Install everything the workspace needs to build messaging. The dashboard
# package is intentionally not listed above, so its install is skipped.
RUN pnpm install --frozen-lockfile --filter "afters-messaging..."

# Copy sources for the packages we need.
COPY afters-shared afters-shared
COPY afters-messaging afters-messaging

# Compile TypeScript -> dist/ via nest build.
RUN pnpm --filter afters-messaging build

# pnpm deploy emits a self-contained, hoisted node_modules + the built code
# for just the target package, ready to copy straight into the runtime stage.
RUN pnpm --filter afters-messaging --prod deploy /tmp/deploy

# ---------- runtime ----------
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV MESSAGING_PORT=3001

# tini gives clean signal handling for the Node process under Railway/PID-1.
RUN apk add --no-cache tini

COPY --from=builder /tmp/deploy ./

EXPOSE 3001
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["node", "dist/main.js"]
