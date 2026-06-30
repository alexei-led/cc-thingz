---
description: Author, inspect, troubleshoot, and review infrastructure across IaC,
  Kubernetes, cloud resources, containers, CI/CD, and Linux hosts. Use when changing
  Terraform/OpenTofu, Kubernetes, Helm, Kustomize, Dockerfiles, GitHub Actions workflow/job/permissions
  semantics, AWS, GCP, Cloud Run, BigQuery, IAM, logs, instances, or service health.
  NOT for deploy/apply/rollback workflows (see deploying-infra). NOT for shell scripts,
  generic command pipelines, or only the shell body inside `run:` steps (see writing-shell).
name: operating-infra
---

# Operate Infrastructure

## Boundary

- Work from files, plans, logs, and read-only commands before changing anything.
- Do not run apply, delete, destroy, or rollback until identity, exact resources, blast radius, and plan/diff/inventory are shown and the user confirms.
- If the task is deployment, rollout, rollback, or production apply, use `deploying-infra`.
- If the task is only shell scripts, generic command pipelines, or the shell body
  inside a GitHub Actions `run:` step, use `writing-shell`.
- For GitHub Actions, workflow structure, triggers, jobs, permissions, runners,
  actions, environments, secrets, caching, concurrency, and policy stay here.
  Mixed workflow and shell-body changes compose with `writing-shell`.

## Role behavior

- Write-capable: make minimal file changes and run safe validation. Stop before live mutation unless the user confirmed exact resources.
- Read-only: apply nothing; return proposed file changes, evidence, and validation commands.

## Load references

Load every matching reference:

- Terraform/OpenTofu files, modules, state, or plans → [terraform.md](references/terraform.md)
- Kubernetes manifests or `kustomization.yaml` → [kubernetes.md](references/kubernetes.md)
- `Chart.yaml`, Helm values, or chart templates → [helm.md](references/helm.md)
- GitHub workflow YAML outside pure `run:` shell bodies → [github-actions.md](references/github-actions.md)
- `Dockerfile` or container image build/release concerns → [dockerfile.md](references/dockerfile.md)
- AWS CLI, EC2, ECS, Lambda, S3, RDS, IAM, or CloudWatch → [aws.md](references/aws.md)
- GCP CLI, GCS, Compute Engine, IAM, quotas, or Cloud Logging → [gcp.md](references/gcp.md)
- Cloud Run services, revisions, traffic, or logs → [cloud-run.md](references/cloud-run.md)
- BigQuery queries, tables, datasets, or cost checks → [bigquery.md](references/bigquery.md)
- Linux services, hosts, processes, disks, or networks → [linux.md](references/linux.md)

Mixed stacks: load all matching references. Unknown stack: use the workflow below only.

## Workflow

1. Identify scope: files, resources, environment, account/project, region/zone, and owner.
2. Verify cloud identity before cloud work; prefer explicit profile/project/region over defaults.
3. Inspect current state with read-only evidence: files, plan/diff, list/describe/status, logs, metrics, and recent events.
4. For authoring/design: choose the smallest pattern that preserves ownership, state boundaries, and least privilege.
5. For troubleshooting: rank likely causes, gather one safe signal, then propose the next step.
6. For validation: run relevant gates when tools exist; state skipped gates and why.
7. For destructive, costly, or externally visible work: show exact resources and blast radius, then stop for confirmation or hand off to `deploying-infra`.

## Validation gates

- Terraform/OpenTofu: format, init without backend when possible, validate, plan, `tflint`, `checkov` or `trivy config`; use plan JSON for policy checks when needed.
- Kubernetes/Kustomize: render first, schema-check with `kubeconform`, then policy/security-check with `kube-linter`, `kubescape`, `conftest`, or `kyverno`.
- Helm: lint chart, render templates, use `helm diff` before upgrade planning, validate rendered YAML.
- Docker/images: lint Dockerfile with `hadolint`; scan images/config with `trivy`; use `syft`, `grype`, and `cosign` where SBOM, vulnerability, or signature proof matters.
- GitHub Actions: run `actionlint` and `zizmor`; require SHA-pinned actions and least-permission jobs.
- Cloud CLI: verify identity, inventory resources, estimate cost or dry-run when available, and check IAM/quota before mutation.

## Output

```text
INFRA RESULT
============
Scope: <files/resources/environment>
Identity: <account/project/profile/region or not applicable>
Status: DONE | NEEDS CONFIRMATION | BLOCKED

Evidence:
- <file:line, plan/log/status summary, or command result>

Changes or proposal:
- <minimal change or proposed next step>

Validation:
- <gate> — pass/fail/skipped

Next:
- <safe next action, confirmation request, or none>
```
