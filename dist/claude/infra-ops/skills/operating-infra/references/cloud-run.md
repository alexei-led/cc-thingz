# Cloud Run

## Service model

- Track service, revision, traffic split, image digest, region, service account, ingress, authentication, concurrency, CPU/memory, timeout, and min/max instances.
- Prefer immutable image digests for production diagnosis and rollback clarity.
- Keep environment variables non-secret; use Secret Manager references for secrets.
- Use least-privilege runtime service accounts.
- Confirm ingress and invoker IAM before changing public/private access.

## Troubleshooting

- Start with service status, latest ready revision, traffic target, recent revision errors, and logs.
- For startup failures, inspect container port, command/entrypoint, env/secret references, image architecture, and startup probe behavior.
- For request failures, inspect authentication, ingress, URL, load balancer/serverless NEG config, timeout, concurrency, and application logs.
- For cold starts or latency, inspect min instances, CPU allocation, concurrency, image size, startup work, VPC connector, and downstream latency.
- For egress failures, inspect VPC connector, route, firewall, DNS, private service access, and service account permissions.

## Boundary

Cloud Run deploy, traffic migration, and rollback are deployment work. Use this reference to inspect and plan; use `deploying-infra` to apply.
