---
allowed-tools:
- Task
- TaskOutput
- TaskCreate
- TaskUpdate
- TaskList
- Bash(kubectl *)
- Bash(helm *)
- Bash(kustomize *)
- Bash(terraform *)
- Bash(actionlint *)
- Bash(docker *)
- Bash(git *)
- Bash(make *)
- Read
- Grep
- Glob
- AskUserQuestion
- mcp__perplexity-ask__perplexity_ask
argument-hint: '[--dry-run | --apply] [environment]'
context: fork
description: Validate and deploy Kubernetes, Terraform, Helm, Kustomize, GitHub Actions,
  and Docker configs. Use when user says "deploy", "deploy to staging", "apply changes",
  "terraform apply", "helm upgrade", "kubectl apply", "rollout", "deploy check", "validate
  deployment", "validate infrastructure", or wants to verify or apply infrastructure
  changes.
name: deploying-infra
user-invocable: true
---

# Deploy Infrastructure

## Usage

```
/deploying-infra --dry-run              # Validate only (default)
/deploying-infra --apply staging        # Apply to staging
/deploying-infra --apply production     # Apply to production (requires confirmation)
```

`--dry-run` runs steps 1–5 (validation only). `--apply` runs all 8 steps.

## Step 1: Parse Arguments

**Default**: `--dry-run` (safe mode)

- `--dry-run` → Validate without applying (stops after step 5)
- `--apply` → Apply changes after validation
- `[environment]` → Target environment (staging, production, dev)
- `--background` → Run validation in background, return agent ID

## Step 2: Detect Infrastructure Type

Use Glob to find infrastructure files (quick scan):

- `**/*.yaml`, `**/*.yml` - K8s, Helm, Kustomize
- `.github/workflows/*.yml` - GitHub Actions
- `**/*.tf` - Terraform
- `**/Dockerfile*`, `**/docker-compose*.yml` - Docker
- `**/kustomization.yaml` - Kustomize
- `**/Chart.yaml` - Helm

### If no infrastructure detected

Stop: "No infrastructure files found. Looking for: \*.tf, Chart.yaml, kustomization.yaml, k8s/, Dockerfile"

### If required CLI tools are absent

Stop: "Missing tools: {list}. Install before proceeding." Do not attempt commands with unavailable tools.

## Step 3: Pre-flight Validation

Dry-run-before-apply safety doctrine: `operating-infra` `## Boundary`.

Read `references/validation-checklists.md` (skill-relative). Map
`{detected_type}` to its section header, then copy that section verbatim into
`{checklist}` below:

- `k8s` → `## Kubernetes`
- `helm` → `## Helm`
- `kustomize` → `## Kustomize`
- `terraform` → `## Terraform`
- `docker` → `## Dockerfile`
- `github-actions` → `## GitHub Actions`

The spawned engineer has no skill-relative access, so the checklist must be
inlined — do not pass a path.

Spawn the engineer agent for validation:

```
Task(
  subagent_type="engineer",
  run_in_background={true if --background else false},
  description="Pre-flight validation",
  prompt="Validate infrastructure before deployment.

  Type: {detected_type}
  Environment: {environment}
  Mode: {dry-run|apply}

  Run these pre-flight checks:
  {checklist}

  Output format:
  READY/BLOCKED per category with file:line for issues.
  Severity: CRITICAL / IMPORTANT / SUGGESTION"
)
```

### If --background

Return agent ID immediately for later collection.

## Step 4: Review Changes

### Present diff/plan to user

```
## Pre-flight: {READY|BLOCKED}

### Changes Summary
{terraform plan output / helm diff / kubectl diff}

### Resources Affected
- {resource type}: {count} to create, {count} to modify, {count} to destroy

### Warnings
- {any destructive changes}
- {any security concerns}
```

### If BLOCKED

Stop and show blockers. Do not proceed to Step 5.

## Step 5: Research Best Practices (if needed)

For uncertain findings, use Perplexity for current best practices:

```
mcp__perplexity-ask__perplexity_ask with:
"Current best practices for {specific concern} in {technology} 2024-2025"
```

### If --dry-run

Stop here. Output the Step 4 pre-flight summary as the final result.

## Step 6: Confirm Production Deploys

### If environment = production

**STOP**: `AskUserQuestion`

- **Production** — Deploy to PRODUCTION? Options: 1. **Yes, deploy** - Apply changes now 2. **Review again** - Show full diff 3. **Cancel** - Abort deployment

## Step 7: Apply Changes

```bash
# Record deployment start
echo "$(date -Iseconds) DEPLOY_START env=$environment" >> .deploy.log

# Apply based on type
case $type in
  terraform)
    terraform apply tfplan
    ;;
  helm)
    helm upgrade --install {release} {chart} -f values-{env}.yaml
    ;;
  kustomize)
    kustomize build overlays/{env} | kubectl apply -f -
    ;;
  k8s)
    kubectl apply -f k8s/{env}/ --recursive
    ;;
esac

# Record completion
echo "$(date -Iseconds) DEPLOY_END status=$?" >> .deploy.log
```

## Step 8: Post-Deploy Verification

```bash
# Wait for rollout
kubectl rollout status deployment/{name} --timeout=300s

# Health check
kubectl get pods -l app={name}
```

### If rollout status times out

Do not wait further. Show rollback commands and ask: "Rollout is taking longer than expected — rollback or investigate?"

### If rollout fails

```
ROLLBACK AVAILABLE

kubectl rollout undo deployment/{name}
# or
terraform apply -target=... (previous state)
# or
helm rollback {release}
```

## Output

```
DEPLOYMENT COMPLETE
===================
Environment: {env}
Type: {terraform|helm|kustomize|k8s}
Duration: {time}
Agent ID: {id} (use /agent:resume {id} to continue)

Applied:
- {resource}: {action}

Status: {HEALTHY|DEGRADED|FAILED}

Rollback: {command if needed}
```

Pairs with `operating-infra` for patterns, inspection, and troubleshooting.
