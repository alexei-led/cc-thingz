# Helm

## When to use Helm

Weigh environments, values variation, release packaging, and who owns the chart.

- Helm: the app ships as a chart, has many optional components, or needs release history, rollback metadata, and chart versioning.
- Kustomize: small environment deltas without templating.

## Chart rules

- Keep naming and labels in helpers.
- Quote `appVersion`; bump chart `version` on every chart change.
- Default the image tag to `appVersion` or an explicit immutable tag.
- Keep values small and flat; avoid nesting that mirrors Kubernetes YAML.
- Gate optional subcharts with `condition` and `enabled` flags.
- Use one chart with per-environment values files, not a chart per environment.
- Reference existing secrets or an external secret manager; keep secrets out of values files.
- Surface immutable-field, selector, and PVC changes and resource deletions before any upgrade.
