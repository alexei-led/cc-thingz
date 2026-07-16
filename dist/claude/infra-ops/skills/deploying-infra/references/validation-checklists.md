# Pre-flight Validation Checklists

Use only the sections for detected infrastructure types. Report READY/BLOCKED per
category with `file:line` for source-backed issues and exact command output for
tool-backed issues.

## Kubernetes

Validation commands:

- `kubectl diff -f <path>`
- `kubectl apply --dry-run=server -f <path>` when cluster access exists
- `kubectl apply --dry-run=client -f <path>` when cluster access is unavailable

Checks:

- Target context and namespace are known and shown to the user.
- Namespace exists or is created by the manifest.
- Workload has requests and limits for CPU and memory.
- Workload runs as non-root where practical.
- Readiness probes exist for serving workloads.
- Liveness probes exist when restart detection is useful.
- Images do not use `latest` tags.
- Secrets and ConfigMaps referenced by workloads exist or are created.
- Services, ingress, and selectors match pod labels.
- Destructive changes in `kubectl diff` are listed before apply confirmation.

## Helm

Validation commands:

- `helm lint <chart>`
- `helm template <release> <chart> --values <values-file>`
- `helm diff upgrade <release> <chart> --values <values-file>` when `helm-diff` is installed

Checks:

- Release name, namespace, chart path, and values files are detected or supplied.
- Values file matches the target environment.
- Rendered manifests pass the relevant Kubernetes checks.
- CRDs and hooks are called out before apply.
- Destructive changes in `helm diff` are listed before apply confirmation.

## Kustomize

Validation commands:

- `kustomize build <overlay>`
- `kustomize build <overlay> | kubectl apply --dry-run=server -f -` when cluster access exists
- `kustomize build <overlay> | kubectl apply --dry-run=client -f -` when cluster access is unavailable

Checks:

- Overlay path matches the target environment.
- Built manifests pass the relevant Kubernetes checks.
- Image tags, patches, namespaces, and name prefixes are expected.
- Destructive changes from diff output are listed before apply confirmation.

## Terraform

Validation commands:

- `terraform fmt -check`
- `terraform init -backend=false` only when provider/plugin setup is needed and safe for the repo
- `terraform validate`
- `terraform plan -out=tfplan`
- `terraform show -no-color tfplan`

Checks:

- Workspace, backend, var files, and target environment are known and shown to the user.
- State backend is configured for shared environments.
- Plan output lists creates, updates, replacements, and destroys.
- Any destroy or replace is listed before apply confirmation.
- Provider credentials are not hardcoded in files.
- Sensitive values are not printed in final output.
- State lock behavior is understood before apply.

## Dockerfile

Docker is validate-only in this skill unless the user explicitly asks for a build
validation. Do not push images or deploy containers here.

Validation commands:

- `docker build --no-cache --progress=plain <context>` when a build context is clear

Checks:

- Base images are pinned to stable tags or digests; avoid `latest`.
- Multi-stage builds are used when they reduce shipped build tools or secrets.
- Runtime image uses a non-root user where practical.
- Secrets are not passed through build args or copied into layers.
- Exposed ports and health checks match the app contract when present.

## GitHub Actions

GitHub Actions are validate-only in this skill. Do not trigger workflows or change
repository settings here.

Validation commands:

- `actionlint`

Checks:

- Secrets are referenced through the platform, not hardcoded.
- Top-level and job-level permissions are minimal; avoid `write-all`.
- Third-party actions are pinned to immutable SHAs or justified version tags.
- Deploy jobs have environment protection or explicit approval where needed.
- Workflow triggers match the intended deploy path.
