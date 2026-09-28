# AWS

Before suggesting a recursive S3 delete, check versioning, lifecycle, replication, and object count.

## Service checks

- EC2: instance state, system status, security groups, subnet, IAM role, user data, attached volumes, and recent CloudWatch metrics.
- ECS: cluster, service events, desired/running count, task definition, image digest, target group health, and task logs.
- Lambda: runtime, timeout, memory, environment, IAM role, trigger source, recent errors, and log group.
- S3: bucket policy, public access block, encryption, versioning, lifecycle, replication, and object ownership.
- RDS: engine/version, storage, backups, maintenance window, parameter and subnet groups, security groups, and snapshots before risky changes.
- IAM: scope policies to least privilege. Wildcard actions/resources and cross-account trust are review findings.

## Troubleshooting

- Auth errors: SSO session, profile, region, permission boundary, SCPs, and resource policy.
- Throttling: find the service quota/API, add pagination and backoff, and avoid unbounded list calls.
- Network failures: VPC, subnet, route table, security group, NACL, DNS, and load balancer target health.
- Missing logs: service role permissions, log group/stream name, region, and retention.
