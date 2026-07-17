# Dockerfile and Images

## Build pattern

- Use multi-stage builds for compiled languages and dependency-heavy runtimes.
- Copy dependency manifests before application code to keep cache useful.
- Prefer minimal runtime images: distroless, slim, scratch, or a pinned base that fits debugging needs.
- Use explicit versions or digests when reproducibility matters.
- Avoid `ADD` for remote URLs. Prefer `COPY` and explicit fetch/verify steps when downloads are required.

## Runtime safety

- Run as non-root.
- Keep root filesystem read-only at runtime when the app allows it.
- Avoid baking secrets, tokens, SSH keys, or cloud credentials into layers.
- Do not rely on `latest` tags for deployable images.
- Keep health checks free of secrets and external side effects.

## Validation

- Use `hadolint` for Dockerfile lint.
- Use `trivy` for image and config scanning.
- Use `syft` for SBOMs and `grype` for vulnerability checks when release evidence matters.
- Use `cosign` for signing and verification when deployment policy requires provenance.

## `.dockerignore`

Exclude VCS data, local caches, secrets, test artifacts, and build output. Do not exclude files needed by the build context, such as lockfiles or metadata read by the build.
