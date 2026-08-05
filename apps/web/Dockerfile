# Next.js 16 production image for the Aegis web app.
#
# The demo compose file has always referenced apps/web/Dockerfile, but the file
# didn't exist, so `docker compose up` failed with "failed to read dockerfile" and
# demo-smoke could never get past starting the stack.
#
# Build context is apps/web only, which works because this package has no
# workspace: dependencies. If one is ever added, the context has to move to the
# repo root and the COPY paths change with it.

FROM node:22-alpine AS deps
WORKDIR /app
# pnpm's own lockfile lives at the repo root, outside this build context, so the
# image resolves from package.json. That means dependency versions here can drift
# from the workspace lockfile — acceptable for a demo image, not for production.
COPY package.json ./
# pnpm is pinned to the workspace's packageManager version. Left to corepack's
# default, it installs the newest pnpm (11.x), which needs Node 22+ APIs this base
# didn't have and died with ERR_UNKNOWN_BUILTIN_MODULE.
RUN corepack enable && corepack prepare pnpm@10.33.0 --activate \
    && pnpm install --no-frozen-lockfile

FROM node:22-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN corepack enable && corepack prepare pnpm@10.33.0 --activate && pnpm build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Run as a non-root user. The demo stack is local, but an image that only works
# as root is an image nobody can deploy anywhere else.
RUN addgroup -g 1001 -S nodejs && adduser -u 1001 -S nextjs -G nodejs

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.ts ./next.config.ts

RUN chown -R nextjs:nodejs /app
USER nextjs

EXPOSE 3000
CMD ["node_modules/.bin/next", "start"]
