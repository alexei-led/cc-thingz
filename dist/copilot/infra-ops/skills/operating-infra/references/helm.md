# Helm

## Use Helm when

- The app is distributed as a chart or has many optional components.
- Values-driven templating is simpler than many Kustomize overlays.
- Release history, rollback metadata, and chart versioning matter.

Prefer Kustomize for small environment deltas without templating.

## Chart rules

- Keep naming and labels in helpers.
- Quote `appVersion`; bump chart `version` on chart changes.
- Default image tag to `appVersion` or an explicit immutable tag, not `latest`.
- Keep values small and typed by convention. Avoid deeply nested values that mirror Kubernetes YAML.
- Use `condition` and `enabled` flags for optional subcharts.
- Use one chart with environment values files, not separate charts per environment.
- Do not store secrets in values files; reference existing secrets or external secret managers.

## Validation

- Lint the chart.
- Render templates for every relevant values file.
- Validate rendered YAML with Kubernetes schema and policy tools.
- Use chart-testing for reusable charts.
- Use helm-unittest when template conditionals are complex.
- Use helm-diff before any upgrade plan is treated as safe.

## Safety

- Surface immutable-field changes, PVC changes, selector changes, and resource deletions before deployment.
- Do not run live upgrade/install here; hand off to `deploying-infra` after diff and confirmation.
