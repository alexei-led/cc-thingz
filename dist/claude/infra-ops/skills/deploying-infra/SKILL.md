---
{"allowed-tools":["Task","TaskOutput","TaskCreate","TaskUpdate","TaskList","Bash(command -v *)","Bash(kubectl *)","Bash(helm *)","Bash(kustomize *)","Bash(terraform *)","Bash(actionlint)","Bash(actionlint *)","Bash(docker *)","Bash(git *)","Bash(make *)","Read","Grep","Glob","AskUserQuestion"],"argument-hint":"[--dry-run | --apply] [environment] [scope]","context":"fork","description":"Validate infrastructure changes and, after explicit confirmation, apply Terraform, Helm, Kustomize, or Kubernetes deployments. Use when the user says \"deploy\", \"deploy to staging\", \"terraform apply\", \"helm upgrade\", \"kubectl apply\", \"rollout\", \"deploy check\", \"validate deployment\", or \"validate infrastructure\". Dockerfiles and GitHub Actions are validate-only here. NOT for ongoing service troubleshooting, cloud inspection, rollback investigation, or authoring infra from scratch; use operating-infra for those.","name":"deploying-infra","user-invocable":true}
---

# Deploy Infrastructure

Validate first. Apply only after explicit confirmation. Never invent deploy paths,
release names, workspaces, namespaces, accounts, or environments.

## Scope

Use for dry-run validation, Terraform/Helm/Kustomize/Kubernetes apply after
confirmation, and rollout verification after apply.

Do not use for live troubleshooting, rollback investigation, cloud inspection,
authoring infra, pushing Docker images, triggering GitHub Actions workflows, or
applying without plan/diff evidence. Use `operating-infra` for inspection and
troubleshooting.

Dockerfiles and GitHub Actions are validate-only in this skill.

## Usage

`/deploying-infra --dry-run [environment] [scope]` validates only. `/deploying-infra --apply <environment> [scope]` validates, asks, applies, then verifies. `/deploying-infra --background --dry-run [environment] [scope]` starts background validation.

Rules:

- Default mode is `--dry-run`.
- `--background` is valid only with `--dry-run`.
- `--apply` requires authorization covering the reviewed artifact and exact destination. Reuse existing explicit authorization when those inputs are unchanged.
- Production confirmation must include the exact environment name.
- If environment, context, namespace, workspace, chart, release, path, or account is unclear, ask one question.

## Workflow

1. Parse mode, environment, and optional scope.
2. Detect infra with `Glob`, `Grep`, and `Read` before shell commands.
3. Classify detected types: apply-capable Terraform/Helm/Kustomize/Kubernetes; validate-only Dockerfile/GitHub Actions.
4. Check required CLIs with safe version or discovery commands.
5. Read `references/validation-checklists.md` and use only detected sections.
6. Run validation and inspect source-backed policy checks.
7. For apply-capable types, show plan/diff evidence.
8. Stop on `--dry-run`; on `--apply`, confirm any unapproved artifact/destination and apply.
9. Verify changed resources after apply.

Use a background or delegated validation agent only for large scans or explicit
`--background`. The agent validates only; it must not apply changes.

## Validation and evidence

Every validation claim needs exact command output, `file:line`, or a skipped-check
reason. For apply-capable types, plan/diff evidence is mandatory before confirmation.
Use the reference checklist for commands. Do not run commands with unresolved
placeholders; ask first.

Before confirmation, show:

```markdown
## Pre-flight: READY | BLOCKED

### Scope

- Environment: <env>
- Type: <terraform|helm|kustomize|kubernetes>
- Context/account/namespace/workspace: <value>

### Plan or Diff Evidence

- `<command>` — <summary>

### Resources Affected

- Create: <count or unknown>
- Modify: <count or unknown>
- Delete: <count or unknown>

### Risks

- <destructive changes, security concerns, missing evidence, or none>
```

If validation is blocked, stop. Do not continue to confirmation.

## Confirmation and apply

Bind authorization to the shown plan or rendered artifact and the exact account,
context, namespace, workspace, chart/version, release, and values as applicable.
Record artifact and input hashes locally without exposing secrets. Immediately
before apply, verify they still match. Revalidate changed inputs and obtain renewed
authorization for the change; do not ask again for an unchanged approved apply.
For production, authorization must name the exact environment. Stop on ambiguous
or mismatched authorization.

Allowed apply patterns only:

- `terraform apply tfplan`
- `helm upgrade --install <release> <pinned-local-chart> --kube-context <context> --namespace <namespace> --values <reviewed-values-file>`
- `kubectl --context <context> --namespace <namespace> apply -f <reviewed-rendered-file>`

Render Kustomize or Kubernetes inputs once into a local artifact, review and dry-run
that file, then apply the same file. For Helm, freeze the chart package/dependencies
and every values/flag input; use the same context, namespace and release in validation
and upgrade. Bind Terraform to the reviewed saved plan and its workspace/backend.

Use only commands already matched to the repo layout. Do not write deployment logs
unless the repo already documents that convention.

If apply fails, stop with `DEPLOYMENT FAILED`. Do not rollback without separate
confirmation.

## Verification

After apply, verify the changed resources with the relevant checklist command or
repo convention. If rollout times out or health is degraded, show investigation
and rollback options, then ask what to do next.

## Output contracts

Use the matching header, then the listed fields.

```text
DRY RUN COMPLETE
Status; Environment; Types; Validation; Plan/Diff; Blockers; Skipped

AWAITING CONFIRMATION
Environment; Type; Command; Destructive changes; Confirmation needed

BACKGROUND VALIDATION STARTED
Agent ID; Mode; Scope

DEPLOYMENT COMPLETE
Environment; Type; Status; Applied; Verification; Rollback option

DEPLOYMENT BLOCKED | DEPLOYMENT FAILED
Environment; Type; Reason; Evidence; Next step
```

## Failure handling

- Unknown target detail: ask one question.
- Missing tool, missing plan/diff evidence, unshown destructive change, or blocked validation: stop.
- Apply failure or partial deployment: report exact evidence and ask before rollback.
- Rollout timeout or degraded health: show rollback and investigation options, then ask.
- User cancels or gives ambiguous confirmation: stop cleanly.