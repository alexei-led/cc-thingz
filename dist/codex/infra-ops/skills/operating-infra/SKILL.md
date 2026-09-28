---
{"description":"Author, inspect, troubleshoot, and review infrastructure across IaC, Kubernetes, cloud resources, containers, CI/CD, and Linux hosts. Use when changing Terraform/OpenTofu, Kubernetes, Helm, Kustomize, Dockerfiles, GitHub Actions workflow/job/permissions semantics, AWS, GCP, Cloud Run, BigQuery, IAM, logs, instances, or service health. NOT for deploy/apply/rollback workflows (see deploying-infra). NOT for shell scripts, generic command pipelines, or only the shell body inside `run:` steps (see writing-shell).","name":"operating-infra"}
---
<!-- Codex platform guidance -->
<!-- Use this platform's installed tool names exactly for shell, file reads, and search. If a referenced helper or optional tool is unavailable, say so and continue with built-in tools. -->


# Operate Infrastructure

Work from files, plans, logs, and read-only commands. Edit repo files as the task needs; touch live resources only under these rules:

- Before any cloud command, confirm identity: `aws sts get-caller-identity --profile <profile>`, `gcloud auth list` and `gcloud config list`. Pass profile, project, region, and zone explicitly instead of relying on CLI defaults.
- Before any live change that is destructive, costly, or externally visible (apply, delete, destroy, stop, resize, scale, IAM, bucket, network, DDL/DML, rollback), show the identity, exact resources (ARNs or names), blast radius, irreversibility, and the plan/diff/inventory behind them, then wait for the user to confirm.
- Deployment, rollout, rollback, and production apply belong to deploying-infra where it is installed. Otherwise stop at the reviewed plan or diff and give the user the exact apply command.
- Without write access, return proposed changes (file, change, reason) instead of applying them.

For troubleshooting, rank likely causes, gather one safe signal at a time, and propose the next step. For authoring, pick the smallest pattern that keeps ownership, state boundaries, and least privilege.

In GitHub Actions, this skill owns workflow structure, triggers, permissions, runners, actions, environments, secrets, caching, and concurrency. The shell body of a `run:` step belongs to writing-shell; mixed changes use both.

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

## Validation gates

Run the gates for changed types when the tools exist; report each skipped gate and why.

- Terraform/OpenTofu: `fmt`, `init -backend=false` when possible, `validate`, `plan`, `tflint`, `checkov` or `trivy config`; Conftest on plan JSON when policy depends on planned values. Use the `tofu` equivalents for OpenTofu.
- Kubernetes/Kustomize: render first, then `kubeconform` against the target version, then `kube-linter`, `kubescape`, `conftest`, or `kyverno`.
- Helm: `helm lint`, `helm template` for every relevant values file, the Kubernetes gates on the output, and `helm diff` before an upgrade counts as safe. Add chart-testing for reusable charts and helm-unittest for complex conditionals.
- Dockerfile/images: `hadolint`, `trivy`; `syft`, `grype`, and `cosign` when SBOM, vulnerability, or provenance evidence matters.
- GitHub Actions: `actionlint`, `zizmor`; `checkov` when scanned with other IaC.
- Cloud CLI: inventory, cost estimate or dry-run when available, and IAM/quota checks before mutation.

Done when the relevant build/test/lint checks pass on what you changed, or you name each check that did not run and why.

## Output

```text
INFRA RESULT
Scope: <files/resources/environment>
Identity: <account/project/profile/region or not applicable>
Status: DONE | NEEDS CONFIRMATION | BLOCKED
Evidence: <file:line, plan/log/status summary, command result>
Changes or proposal: <minimal change or next step>
Validation: <gate — pass/fail/skipped>
Next: <safe next action, confirmation request, or none>
```
