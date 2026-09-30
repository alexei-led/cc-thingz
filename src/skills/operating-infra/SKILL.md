---
description: Author, inspect, troubleshoot, review, and apply (after explicit
  confirmation) infrastructure across IaC, Kubernetes, cloud resources, containers,
  CI/CD, and Linux hosts. Use when changing Terraform/OpenTofu, Kubernetes, Helm,
  Kustomize, Dockerfiles, GitHub Actions workflow/job/permissions semantics, AWS,
  GCP, Cloud Run, BigQuery, IAM, logs, instances, or service health, or when the
  user says "deploy", "deploy to staging", "terraform apply", "helm upgrade",
  "kubectl apply", "rollout", "deploy check", "validate deployment", or
  "validate infrastructure". NOT for shell scripts,
  generic command pipelines, or only the shell body inside `run:` steps (see
  writing-shell).
name: operating-infra
---

# Operate Infrastructure

Work from files, plans, logs, and read-only commands; edit repo files freely, but touch live resources only under these rules:

- Before any cloud command, confirm identity (`aws sts get-caller-identity --profile <profile>`; `gcloud auth list`, `gcloud config list`), passing profile, project, region, and zone explicitly instead of relying on CLI defaults.
- Before any live change that's destructive, costly, or externally visible (apply, upgrade, rollout, delete, destroy, stop, resize, scale, IAM, bucket, network, DDL/DML, rollback): show identity, exact resources (ARNs or names), blast radius, irreversibility, and the plan/diff/inventory behind them, then wait for explicit confirmation.
- Every apply, upgrade, or rollout, regardless of blast radius: confirm the exact destination first (account, context, namespace, workspace, or release — name production explicitly), run the validation gates below on the same rendered artifact, show the plan or diff with create/modify/delete counts, and apply only that same reviewed artifact (the saved plan file or rendered manifest), only after explicit confirmation of that exact artifact and destination — never apply to production without it.
- After applying, verify rollout status, pod health, or Terraform outputs/state, and name the rollback path. On apply failure or a timed-out/degraded rollout: stop, report status and rollback options, and ask before any rollback.
- Without write access, return proposed changes (file, change, reason) instead of applying them.

For troubleshooting: rank likely causes, gather one safe signal at a time, propose the next step. For authoring: pick the smallest pattern keeping ownership, state boundaries, and least privilege.

In GitHub Actions this skill owns workflow structure, triggers, permissions, runners, actions, environments, secrets, caching, and concurrency — not the shell body of a `run:` step (writing-shell); mixed changes use both.

## References

Load every reference that matches the stack:

- Terraform/OpenTofu files, modules, state, or plans → [terraform.md](references/terraform.md)
- Kubernetes manifests or `kustomization.yaml` → [kubernetes.md](references/kubernetes.md)
- `Chart.yaml`, Helm values, or chart templates → [helm.md](references/helm.md)
- GitHub workflow YAML → [github-actions.md](references/github-actions.md)
- `Dockerfile` or image build/release → [dockerfile.md](references/dockerfile.md)
- AWS: EC2, ECS, Lambda, S3, RDS, IAM, CloudWatch → [aws.md](references/aws.md)
- GCP: GCS, Compute Engine, IAM, Pub/Sub, Cloud SQL, quotas, Cloud Logging → [gcp.md](references/gcp.md)
- Cloud Run services, revisions, traffic, or logs → [cloud-run.md](references/cloud-run.md)
- BigQuery queries, tables, datasets, or cost → [bigquery.md](references/bigquery.md)
- Linux services, hosts, processes, disks, or networks → [linux.md](references/linux.md)
- Applying, upgrading, rolling out, or any deploy request, including a bare "deploy this" → [deploying.md](references/deploying.md)

## Validation gates

Run the gates for changed types when the tools exist; report each skipped gate and why.

- Terraform/OpenTofu (or `tofu` equivalents): `fmt`, `init -backend=false` when possible, `validate`, `plan`, `tflint`, `checkov` or `trivy config`.
- Kubernetes/Kustomize: render first, then `kubeconform` against the target version, then `kube-linter`, `kubescape`, `conftest`, or `kyverno`.
- Helm: `helm lint`, `helm template` for every relevant values file, the Kubernetes gates on the output, and `helm diff` before an upgrade counts as safe.
- Dockerfile/images: `hadolint`, `trivy`.
- GitHub Actions: `actionlint`, `zizmor`.
- Cloud CLI: inventory, cost estimate or dry-run when available, and IAM/quota checks before mutation.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.

## Output

```text
INFRA RESULT
Scope: <files/resources/environment>
Identity: <account/project/profile/region or not applicable>
Status: DONE | NEEDS CONFIRMATION | BLOCKED | FAILED
Evidence: <file:line, plan/log/status summary, command result>
Changes or proposal: <minimal change or next step>
Validation: <gate — pass/fail/skipped>
Next: <safe next action, confirmation request, or none>
```
