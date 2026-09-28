# GCP

Use `--quiet` on destructive commands only after the user confirmed the exact resources.

## Service checks

- Compute Engine: instance state, zone, machine type, boot disk, service account, tags, firewall rules, metadata, serial output, and recent logs.
- GCS: IAM, public access prevention, uniform bucket-level access, versioning, lifecycle, retention, soft delete, and object count.
- IAM: least privilege at the service-account level. Broad project roles and user-managed keys are review findings.
- Pub/Sub: subscription backlog, dead-letter and retry policy, push endpoint health, and ack deadlines.
- Cloud SQL: backups, maintenance window, flags, network exposure, IAM/database users, and connection errors before risky changes.

## Troubleshooting

- Auth errors: ADC vs user credentials, service account impersonation, IAM role, and org policy.
- Quota errors: report quota name, region, current limit, requested amount, and service.
- Region/zone errors: verify the resource location before editing config.
- Missing logs: service account permission, log filter, project, region, and retention.
