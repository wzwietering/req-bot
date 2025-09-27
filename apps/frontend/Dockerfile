# Multi-stage Dockerfile for Next.js frontend

# Build stage
FROM node:22.20-alpine3.22 AS builder

# Set working directory
WORKDIR /app

# Copy root package files for workspace setup
COPY package*.json ./
COPY turbo.json ./

# Copy shared types package
COPY packages/shared-types ./packages/shared-types

# Copy frontend app
COPY apps/frontend ./apps/frontend

# Install dependencies
RUN npm ci

# Build the frontend application
WORKDIR /app/apps/frontend
RUN npm run build

# Production stage
FROM node:22.20-alpine3.22 AS runner

# Set working directory
WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/apps/frontend/.next/standalone ./
COPY --from=builder /app/apps/frontend/.next/static ./apps/frontend/.next/static
COPY --from=builder /app/apps/frontend/public ./apps/frontend/public

# Set correct permissions
USER nextjs

# Expose port
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Start the application
CMD ["node", "apps/frontend/server.js"]