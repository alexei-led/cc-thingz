# Applying and Deploying

Read this before any `apply`, `upgrade`, `rollout`, or production change to an
already-validated Terraform, Helm, Kustomize, or Kubernetes artifact.

## Hard rules

- Never invent deploy paths, release names, workspaces, namespaces, accounts, or environments. If one is unclear, ask.
- Authorization binds to the reviewed artifact (saved plan or rendered file) and its exact destination. Ambiguous, partial, or mismatched authorization means stop and ask again.
- Blocked validation, missing plan/diff evidence, or an unshown destructive change: stop before confirmation.
- Never run a command with an unresolved placeholder. Keep secrets out of evidence and hashes.
- Push no images and trigger no CI workflows here.
- Asked to describe the workflow rather than run it: give the ordered steps below. Unknown details (destination, release, values) become the questions to ask, not a blocked report.

## Workflow

1. Detect the infra type and target details from repo files.
2. Run the apply evidence below for the detected type, plus the Validation gates this skill lists, on the same rendered artifact. Record each unavailable tool as a skipped check with its reason.
3. Show the pre-flight report. Stop here for a dry run.
4. Record the artifact and input hashes, then get confirmation of the exact artifact and destination unless already authorized.
5. Immediately before apply, verify the artifact and input hashes still match. Changed inputs need revalidation and renewed authorization.
6. Apply with one of the allowed commands below.
7. Verify the changed resources: rollout status, pod health, or Terraform outputs/state.

```markdown
## Pre-flight: READY | BLOCKED

- Environment / type: <env> / <terraform|helm|kustomize|kubernetes>
- Destination: <account/context/namespace/workspace/release>
- Evidence: `<command>` — <summary>
- Resources: create <n>, modify <n>, delete/replace <n>
- Risks: <destructive changes, CRDs/hooks, missing evidence, or none>
- Rollback: <helm rollback <release> <rev> | kubectl rollout undo | revert the commit, re-plan, and confirm again>
```

## Apply evidence by type

Validate and apply against the same explicit destination and frozen inputs.

- Kubernetes: `kubectl --context <context> --namespace <namespace> diff -f <reviewed-rendered-file>`, then `apply --dry-run=server` (`--dry-run=client` only without cluster access, and say so). Confirm the namespace and any referenced Secrets/ConfigMaps exist. List deletions and immutable-field changes (selectors, PVCs) before confirmation.
- Kustomize: `kustomize build <overlay> > <reviewed-rendered-file>`, then the Kubernetes evidence on that file. Apply that same file; do not rebuild the overlay between review and apply.
- Helm: freeze the chart package, dependencies, and every values file/flag. `helm lint`, `helm template` for the target values, then `helm diff upgrade` (or `kubectl diff` on the rendered output without `helm-diff`). Call out CRDs and hooks before confirmation. Record `helm history` as the rollback target.
- Terraform/OpenTofu: `fmt -check`, `init -backend=false` when safe, `validate`, then `plan -out=tfplan` and `show -no-color tfplan`. Confirm workspace, backend, and var files match the target; shared environments need a locked remote backend. List every destroy/replace before confirmation.

## Allowed apply commands

- `terraform apply tfplan`
- `helm upgrade --install <release> <pinned-local-chart> --kube-context <context> --namespace <namespace> --values <reviewed-values-file>`
- `kubectl --context <context> --namespace <namespace> apply -f <reviewed-rendered-file>`

## Output

After an actual apply run, start with one header, then its fields:

```text
DRY RUN COMPLETE: Status; Environment; Types; Validation; Plan/Diff; Blockers; Skipped
AWAITING CONFIRMATION: Environment; Type; Command; Destructive changes; Confirmation needed
DEPLOYMENT COMPLETE: Environment; Type; Status; Applied; Verification; Rollback option
DEPLOYMENT BLOCKED | DEPLOYMENT FAILED: Environment; Type; Reason; Evidence; Next step
```
