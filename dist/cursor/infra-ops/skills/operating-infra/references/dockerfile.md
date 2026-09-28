# Dockerfile and Images

## Build

- Use multi-stage builds for compiled languages and dependency-heavy runtimes.
- Copy dependency manifests before application code to keep the cache useful.
- Use minimal runtime images (distroless, slim, scratch) or a pinned base that fits debugging needs.
- Pin base images by version or digest; deployable images never use `latest`.
- Use `COPY` plus an explicit fetch-and-verify step instead of `ADD` for remote URLs.

## Runtime

- Run as non-root, with a read-only root filesystem when the app allows it.
- Keep secrets, tokens, SSH keys, and cloud credentials out of build args and layers.
- Keep health checks free of secrets and external side effects; match exposed ports to the app contract.

## `.dockerignore`

Exclude VCS data, local caches, secrets, test artifacts, and build output. Keep files the build reads, such as lockfiles and metadata.
