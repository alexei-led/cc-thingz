# Kubernetes

## Tool choice

- Raw manifests: small stable resources with little environment variation.
- Kustomize: overlays, environment deltas, and patching without templating.
- Helm: packaged apps, third-party charts, or heavy templating.
- Terraform: cluster and cloud resources whose lifecycle sits outside the Kubernetes API.

## Workload defaults

- Pin image tags; never `latest`.
- Set requests and sane limits; avoid limits that cause predictable throttling or OOMs.
- Use readiness probes for routing; add liveness probes only when a restart is a real recovery path.
- Run as non-root, disable privilege escalation, drop capabilities, and use a read-only root filesystem where possible.
- Add network policies when namespace isolation matters.
- Use PodDisruptionBudgets and topology spread for production availability when replicas allow it.
- Keep labels stable: `app.kubernetes.io/name`, `instance`, `component`, `part-of`, and `managed-by`.
- Check Service and Ingress selectors against pod labels.
- Selector, PVC, and other immutable-field changes may need a migration instead of a rollout.

## Secrets and config

- Keep real secret values out of manifests. Use External Secrets Operator, CSI secret drivers, SOPS, Sealed Secrets, or a cloud secret manager.
- Separate config from secrets. Mount high-risk secrets as files rather than environment variables.

## Troubleshooting

- Check, in order: events, rollout status, pod status, container logs, image pull errors, probes, resource pressure, and service endpoints.
- Networking: Service selectors, EndpointSlices, NetworkPolicies, DNS, ingress/controller logs, and cloud load balancer state.
- Scheduling: node selectors, taints/tolerations, requests, affinity, topology spread, and quota.
