# Terraform and OpenTofu

Use Terraform for cloud resource lifecycle, shared infrastructure, policy-controlled state, and repeatable environments, not for one-off fixes whose source of truth is elsewhere.

## Module boundaries

- Foundation modules hold slow-changing shared primitives: networks, shared IAM, org policy, base logging, and shared secrets plumbing.
- App/environment modules hold app-owned resources: service accounts, bindings, runtime config, queues, buckets, databases, and deploy-time wiring.
- Pass explicit inputs and outputs (IDs, self-links, names, emails, regions, subnet names); never read sibling state implicitly.
- Align state boundaries with ownership and rollout risk, so frequent app deploys never touch shared foundations.
- Use small root modules per environment or bounded service area instead of one global state file.
- Keep provider and version constraints explicit.

## Safety

- A plan is evidence, not permission to apply. Surface every create/update/delete count and stop on an unexpected destroy or replace.
- Run Conftest on the plan JSON when policy depends on planned values.
- Use targeted apply only for narrowly explained recovery work.
- Keep remote state encrypted and locked. Never commit state, plan files with secrets, or provider credentials.
- Mark sensitive outputs. Keep secrets out of variable files unless they are encrypted and intentionally managed.

## Troubleshooting

- Lock errors: identify the lock owner before forcing an unlock.
- Drift: compare state, plan, and live resource ownership before importing or changing code.
- Provider auth failures: verify identity, project/account, region, and required IAM before editing modules.
- Quota failures: report requested resource, region, quota name, and current limit.
