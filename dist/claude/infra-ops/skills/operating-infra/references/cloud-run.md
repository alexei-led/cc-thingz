# Cloud Run

## Service model

- Track service, revision, traffic split, image digest, region, service account, ingress, authentication, concurrency, CPU/memory, timeout, and min/max instances.
- Use immutable image digests for production diagnosis and rollback clarity.
- Keep environment variables non-secret; reference Secret Manager for secrets.
- Use least-privilege runtime service accounts. Confirm ingress and invoker IAM before changing public/private access.
- Deploy, traffic migration, and rollback are deployment work.

## Troubleshooting

- Start with service status, latest ready revision, traffic target, recent revision errors, and logs.
- Startup failures: container port, command/entrypoint, env/secret references, image architecture, and startup probe.
- Request failures: authentication, ingress, URL, load balancer/serverless NEG config, timeout, concurrency, and application logs.
- Cold starts or latency: min instances, CPU allocation, concurrency, image size, startup work, VPC connector, and downstream latency.
- Egress failures: VPC connector, route, firewall, DNS, private service access, and service account permissions.
