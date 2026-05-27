FROM node:22-slim AS base

RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@10

WORKDIR /app

COPY pnpm-workspace.yaml package.json pnpm-lock.yaml tsconfig.base.json tsconfig.json ./

COPY lib/ ./lib/
COPY artifacts/api-server/ ./artifacts/api-server/
COPY artifacts/afsona-tv/ ./artifacts/afsona-tv/

RUN pnpm install --frozen-lockfile

FROM base AS build

RUN pnpm --filter @workspace/api-spec run codegen

RUN BASE_PATH=/ PORT=8080 pnpm --filter @workspace/afsona-tv run build

RUN pnpm --filter @workspace/api-server run build

RUN cp -r artifacts/afsona-tv/dist/public artifacts/api-server/dist/public

FROM node:22-slim AS runtime

RUN apt-get update && apt-get install -y python3 make g++ && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@10

WORKDIR /app

COPY pnpm-workspace.yaml package.json pnpm-lock.yaml tsconfig.base.json tsconfig.json ./
COPY lib/ ./lib/
COPY artifacts/api-server/package.json ./artifacts/api-server/package.json

RUN pnpm install --frozen-lockfile --filter @workspace/api-server

COPY --from=build /app/artifacts/api-server/dist ./artifacts/api-server/dist

RUN mkdir -p /data

EXPOSE 8080

CMD ["node", "--enable-source-maps", "./artifacts/api-server/dist/index.mjs"]
