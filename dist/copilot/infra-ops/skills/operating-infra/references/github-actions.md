# GitHub Actions

## Workflow rules

- Separate CI, release, deploy, and security-scan workflows when their triggers or permissions differ.
- Set workflow and job permissions explicitly; default to `contents: read`.
- Pin every external action, including `actions/*`, by full commit SHA with a version comment (`uses: actions/checkout@<sha> # v6`). Only local `./` actions and local reusable workflows are exempt; pin remote reusable workflows by SHA like actions.
- Use OIDC for cloud auth instead of long-lived cloud keys in secrets.
- Add concurrency to deployments and workflows that must not overlap.
- Cache only dependency and build caches that are safe to restore across branches.
- Use reusable workflows only when the contract is stable and the caller controls inputs clearly.

## Blockers

- Broad permissions, unpinned actions, write tokens on `pull_request_target` or fork PRs, untrusted input interpolated into `run:`, and secret exposure.
- Cloud deploy jobs without environment protection, approval gates, or an explicit project/account/region.

## Other checks

- Matrix jobs: artifact names are unique, and later jobs consume the intended artifact set.
- Release pipelines: include provenance, SBOM, vulnerability scan, and image signing when supply chain matters.
- Run `checkov` on this workflow when it's scanned alongside other IaC changes.
