# GCP

## Identity and safety

- Verify active account and project before touching resources.
- Prefer explicit project, region, and zone over CLI defaults.
- Inventory candidate resources with list/describe APIs before delete, stop, IAM, bucket, or network changes.
- For destructive work, show project, account, region/zone, exact resources, and irreversibility before asking for confirmation.
- Avoid quiet/non-interactive destructive commands unless the user already confirmed exact resources.

## Service checks

- Compute Engine: inspect instance state, zone, machine type, boot disk, service account, tags, firewall rules, metadata, serial output, and recent logs.
- GCS: inspect IAM, public access prevention, uniform bucket-level access, versioning, lifecycle, retention, soft delete, and object count.
- IAM: prefer service-account-level least privilege. Treat broad project roles and user-managed keys as review findings.
- Pub/Sub: inspect subscription backlog, dead-letter policy, retry policy, push endpoint health, and ack deadlines.
- Cloud SQL: inspect backups, maintenance window, flags, network exposure, IAM/database users, and connection errors before risky changes.

## Troubleshooting

- Auth errors: check account, active project, ADC vs user credentials, service account impersonation, IAM role, and org policy.
- Quota errors: report quota name, region, current limit, requested amount, and service.
- Region/zone errors: verify the resource location before editing config.
- Missing logs: confirm service account permission, log filter, project, region, and retention.
