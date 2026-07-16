# Terraform and OpenTofu

## Scope

Use for cloud resource lifecycle, shared infrastructure, policy-controlled state, and repeatable environment creation. Do not use it for one-off operational fixes when the source of truth is elsewhere.

## Module boundaries

- Put slow-changing shared primitives in foundation modules: networks, shared IAM, org policy, base logging, and shared secrets plumbing.
- Put app-owned resources in app/environment modules: service accounts, bindings, runtime config, queues, buckets, databases, and deploy-time wiring.
- Pass explicit inputs/outputs: IDs, self-links, names, emails, regions, and subnet names. Do not reach into sibling state implicitly.
- Keep state boundaries aligned with ownership and rollout risk. Shared foundations should not be coupled to frequent app deploys.
- Prefer small root modules per environment or bounded service area over one global state file.

## Safety

- Treat plan output as evidence, not permission to apply.
- Surface every create/update/delete count. Stop on unexpected destroy or replacement.
- Do not suggest targeted apply except for narrowly explained recovery work.
- Keep remote state encrypted and locked. Never commit state, plan files with secrets, or provider credentials.
- Mark sensitive outputs. Avoid secrets in variables files unless encrypted and intentionally managed.

## Validation

- Run format, init without backend when possible, validate, and plan for changed roots.
- Use `tflint` for provider-aware lint.
- Use `checkov` or `trivy config` for misconfiguration/security checks.
- Convert plan to JSON for policy checks with OPA/Conftest when rules depend on planned values.
- For OpenTofu, use the equivalent `tofu` command and keep provider/version constraints explicit.

## Troubleshooting

- Lock errors: identify the lock owner before forcing unlock.
- Drift: compare state, plan, and live resource ownership before importing or changing code.
- Provider auth failures: verify identity, project/account, region, and required IAM before editing modules.
- Quota failures: report requested resource, region, quota name, and current limit.
