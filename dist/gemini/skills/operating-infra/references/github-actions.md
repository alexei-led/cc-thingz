# GitHub Actions

## Workflow rules

- Keep CI, release, deploy, and security scans in separate workflows when triggers or permissions differ.
- Set workflow and job permissions explicitly. Default to `contents: read`.
- Use OIDC for cloud auth; avoid long-lived cloud keys in secrets.
- Pin third-party actions by full SHA and keep the version comment for readability.
- Add concurrency for deployments and workflows that should not overlap.
- Cache only dependency directories and build caches that are safe to restore across branches.
- Prefer reusable workflows only when the contract is stable and the caller controls inputs clearly.

## Validation

- Use `actionlint` for syntax and expression checks.
- Use `zizmor` or an equivalent scanner for workflow security issues.
- Use `checkov` when scanning GitHub Actions together with other IaC.
- For release pipelines, include artifact provenance, SBOM generation, vulnerability scan, and image signing when supply chain matters.

## Failure and security checks

- Treat broad permissions, unpinned actions, pull-request write tokens, shelling untrusted input, and secret exposure as blockers.
- For matrix jobs, confirm artifact names are unique and later jobs consume the intended artifact set.
- For cloud deploy jobs, verify environment protection, approval gates, and explicit project/account/region.
