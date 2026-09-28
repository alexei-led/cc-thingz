---
{"allowed-tools":["Task","TaskOutput","TaskCreate","TaskUpdate","TaskList","Bash(command -v *)","Bash(kubectl *)","Bash(helm *)","Bash(kustomize *)","Bash(terraform *)","Bash(git *)","Bash(make *)","Bash(tflint *)","Bash(checkov *)","Bash(trivy *)","Bash(kubeconform *)","Bash(kube-linter *)","Bash(kubescape *)","Bash(conftest *)","Bash(kyverno *)","Read","Grep","Glob","AskUserQuestion"],"argument-hint":"[--dry-run | --apply] [environment] [scope]","context":"fork","description":"Validate infrastructure changes and, after explicit confirmation, apply Terraform, Helm, Kustomize, or Kubernetes deployments. Use when the user says \"deploy\", \"deploy to staging\", \"terraform apply\", \"helm upgrade\", \"kubectl apply\", \"rollout\", \"deploy check\", \"validate deployment\", or \"validate infrastructure\". NOT for Dockerfile or GitHub Actions review, service troubleshooting, cloud inspection, rollback investigation, or authoring infra; use operating-infra for those.","name":"deploying-infra","user-invocable":true}
---

# Deploy Infrastructure

Validate first and apply only what the user approved. Hard rules:

- Never invent deploy paths, release names, workspaces, namespaces, accounts, or environments. If one is unclear, ask one question.
- Authorization binds to the reviewed artifact (saved plan or rendered file) and its exact destination: account, context, namespace, workspace, chart/version, release, and values. Production authorization names the exact environment. Ambiguous, partial, or mismatched authorization means stop and ask again.
- Blocked validation, missing plan/diff evidence, or an unshown destructive change: stop before confirmation.
- Apply failure: stop with `DEPLOYMENT FAILED` and ask before any rollback.
- Rollout timeout or degraded health: show investigation and rollback options, then ask.
- Push no images and trigger no CI workflows here.

## Modes

- `--dry-run [environment] [scope]` (default): validate and report.
- `--apply <environment> [scope]`: validate, confirm, apply, verify. Reuse an existing explicit authorization when the artifact and destination are unchanged.
- `--background --dry-run ...`: validation in a background agent, which never applies.

## Workflow

Order is the safety gate:

1. Detect infra types and target details from repo files.
2. Run the evidence commands for each detected type from [validation-checklists.md](references/validation-checklists.md). Run the lint, schema, and policy gates that operating-infra lists on the same rendered artifact; record each unavailable tool as a skipped check with its reason.
3. Show the pre-flight report below. Stop here on `--dry-run`.
4. Record the artifact and input hashes, then ask for confirmation of the exact artifact and destination unless already authorized.
5. Immediately before apply, verify the artifact and input hashes still match. Changed inputs need revalidation and renewed authorization.
6. Apply with one of the allowed commands.
7. Verify the changed resources: rollout status, pod health, Terraform outputs or state.

Every validation claim cites exact command output, `file:line`, or a skipped-check reason. Never run a command with an unresolved placeholder. Keep secrets out of evidence and hashes.

```markdown
## Pre-flight: READY | BLOCKED

- Environment / type: <env> / <terraform|helm|kustomize|kubernetes>
- Destination: <account/context/namespace/workspace/release>
- Evidence: `<command>` — <summary>
- Resources: create <n>, modify <n>, delete/replace <n>
- Risks: <destructive changes, CRDs/hooks, missing evidence, or none>
- Rollback: <helm rollback <release> <rev> | kubectl rollout undo | revert the commit, re-plan, and confirm again>
```

## Allowed apply commands

- `terraform apply tfplan`
- `helm upgrade --install <release> <pinned-local-chart> --kube-context <context> --namespace <namespace> --values <reviewed-values-file>`
- `kubectl --context <context> --namespace <namespace> apply -f <reviewed-rendered-file>`

Write deployment logs only where the repo already has that convention.

## Output

Start with one header, then its fields:

```text
DRY RUN COMPLETE: Status; Environment; Types; Validation; Plan/Diff; Blockers; Skipped
AWAITING CONFIRMATION: Environment; Type; Command; Destructive changes; Confirmation needed
BACKGROUND VALIDATION STARTED: Agent ID; Mode; Scope
DEPLOYMENT COMPLETE: Environment; Type; Status; Applied; Verification; Rollback option
DEPLOYMENT BLOCKED | DEPLOYMENT FAILED: Environment; Type; Reason; Evidence; Next step
```
