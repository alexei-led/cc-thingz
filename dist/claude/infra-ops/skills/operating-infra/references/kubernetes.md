# Kubernetes

## Tool choice

- Raw manifests: small stable resources with little environment variation.
- Kustomize: overlays, environment deltas, and patching without templating.
- Helm: packaged apps, third-party charts, or heavy templating.
- Terraform: cluster/cloud resources and lifecycle outside the Kubernetes API.

## Workload defaults

- Do not use `latest` image tags.
- Set requests and sane limits; avoid limits that cause predictable throttling or OOMs.
- Use readiness probes for routing and liveness probes only when restart is a real recovery path.
- Run as non-root, disable privilege escalation, drop capabilities, and prefer a read-only root filesystem.
- Add network policies when namespace isolation matters.
- Use PodDisruptionBudgets and topology spread for production availability when replicas allow it.
- Keep labels stable: `app.kubernetes.io/name`, `instance`, `component`, `part-of`, and `managed-by`.

## Secrets and config

- Do not put real secret values in manifests.
- Prefer External Secrets Operator, CSI secret drivers, SOPS, Sealed Secrets, or cloud secret managers.
- Separate config from secrets. Avoid environment variables for high-risk secrets when mounted files work better.

## Validation

- Render Kustomize/Helm before validating.
- Use `kubeconform` for schema compatibility with the target Kubernetes version.
- Use `kube-linter`, `kubescape`, `conftest`, or `kyverno` for policy and security checks.
- Check immutable-field changes before proposing rollout; selectors and PVC-sensitive changes may require migration.

## Troubleshooting

- Check events, rollout status, pod status, container logs, image pull errors, probes, resource pressure, and service endpoints in that order.
- For networking, compare Service selectors, EndpointSlices, NetworkPolicies, DNS, ingress/controller logs, and cloud load balancer state.
- For scheduling, inspect node selectors, taints/tolerations, requests, affinity, topology spread, and quota.
