# Apply Evidence by Type

Read the sections for detected types. Validate and apply against the same explicit
destination and frozen inputs. Mark each type READY or BLOCKED.

## Kubernetes

- `kubectl --context <context> --namespace <namespace> diff -f <reviewed-rendered-file>`
- `kubectl --context <context> --namespace <namespace> apply --dry-run=server -f <reviewed-rendered-file>`; use `--dry-run=client` only without cluster access, and say so.
- The namespace exists or the manifest creates it; referenced Secrets and ConfigMaps exist.
- List deletions and immutable-field changes (selectors, PVCs) from the diff before confirmation.

## Kustomize

- `kustomize build <overlay> > <reviewed-rendered-file>`, then the Kubernetes commands on that file.
- Apply that same file; do not rebuild the overlay between review and apply.
- The overlay path matches the target environment.

## Helm

- Freeze the chart package, dependencies, and every values file and flag.
- `helm lint <chart>`
- `helm template <release> <pinned-local-chart> --kube-context <context> --namespace <namespace> --values <reviewed-values-file>`
- `helm diff upgrade <release> <pinned-local-chart> --kube-context <context> --namespace <namespace> --values <reviewed-values-file>` when `helm-diff` is installed; without it, diff the rendered output with `kubectl diff`.
- The values file matches the target environment. Call out CRDs and hooks before confirmation.
- Record the current revision (`helm history <release>`) as the rollback target.

## Terraform

- `terraform fmt -check`, then `terraform init -backend=false` when provider setup is needed and safe, then `terraform validate`.
- `terraform plan -out=tfplan`, then `terraform show -no-color tfplan`.
- Workspace, backend, and var files match the target environment; shared environments use a locked remote backend.
- List every destroy and replace before confirmation. Keep sensitive values out of output.
