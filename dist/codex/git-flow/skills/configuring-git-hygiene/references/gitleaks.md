# Gitleaks Rules

## Defaults

- Pre-commit: scan staged changes.
- Pre-push: scan pushed history or the full repo when the repo accepts the cost.
- Always redact findings.
- Never send secret values to external tools.
- Preserve existing `.gitleaks.toml` rules.

Preferred staged scan when supported:

```bash
gitleaks git --pre-commit --redact --staged --verbose
```

## Missing Tool

If `gitleaks` is unavailable, ask for the desired policy before writing hooks:

- fail closed with a clear install message
- skip with a warning for local-only convenience

Do not silently weaken security.

## False Positives

Tune allowlists in `.gitleaks.toml`. Do not remove the scanner to unblock work.

Use narrow allowlist entries tied to stable paths or test fixtures. Do not allowlist broad secret-like patterns globally.
