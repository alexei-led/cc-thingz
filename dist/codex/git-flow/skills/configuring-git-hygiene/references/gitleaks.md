# Gitleaks

- Pre-commit: `gitleaks git --pre-commit --redact --staged --verbose`.
- Pre-push: scan the pushed commits, or the full repo when the repo accepts the cost.
- Preserve existing `.gitleaks.toml` rules.

## Missing tool

Before writing hooks, ask which policy the user wants: fail closed with an install message, or skip with a warning for local-only convenience.

## False positives

Tune `.gitleaks.toml` with narrow allowlist entries tied to stable paths or test fixtures. Never allowlist broad secret-like patterns globally or remove the scanner to unblock work.
