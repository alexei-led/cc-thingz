# AWS

## Identity and safety

- Verify caller identity before touching resources.
- Use explicit profile and region for commands that inspect or mutate resources.
- Inventory candidate resources with list/describe APIs before any delete, stop, terminate, policy, or bucket operation.
- For destructive work, show account, profile, region, exact ARNs or names, and irreversibility before asking for confirmation.
- Do not use recursive S3 deletion as a suggested next action until versioning, lifecycle, replication, and object count are understood.

## Service checks

- EC2: inspect instance state, system status, security groups, subnet, IAM role, user data, attached volumes, and recent CloudWatch metrics.
- ECS: inspect cluster, service events, desired/running count, task definition, image digest, target group health, and task logs.
- Lambda: inspect runtime, timeout, memory, environment, IAM role, trigger source, recent errors, and log group.
- S3: inspect bucket policy, public access block, encryption, versioning, lifecycle, replication, and object ownership.
- RDS: inspect engine/version, storage, backups, maintenance window, parameter groups, subnet groups, security groups, and snapshots before risky changes.
- IAM: prefer least-privilege scoped policies. Treat wildcard actions/resources and cross-account trust as review findings.

## Troubleshooting

- Auth errors: check identity, profile, SSO session, region, permission boundary, SCPs, and resource policy.
- Throttling: identify service quota/API, add pagination/backoff, and avoid large unbounded list calls.
- Network failures: compare VPC, subnet, route table, security group, NACL, DNS, and load balancer target health.
- Missing logs: confirm service role permissions, log group/stream name, region, and retention policy.
