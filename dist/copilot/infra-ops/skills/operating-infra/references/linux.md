# Linux Hosts and Services

## Safety

- Inspect before changing service state, firewall rules, files, users, disks, or processes.
- Do not suggest reboot, kill, delete, chmod/chown, package upgrade, or firewall mutation as the next action until blast radius and target are clear.
- Capture current state before recovery steps when data loss is possible.

## Service troubleshooting

- Check service state, recent journal entries, config paths, environment files, ports, dependencies, and restart history.
- For failed starts, inspect unit files, permissions, missing files, bind addresses, config validation, and exit codes.
- For log-heavy failures, narrow by time window and service name.

## Resource troubleshooting

- CPU: inspect load, top processes, thread count, and recent deploys or cron jobs.
- Memory: inspect RSS, OOM killer messages, cgroups, swap, and leak patterns.
- Disk: inspect filesystem fullness, inode exhaustion, mount state, deleted-but-open files, and log growth.
- Network: inspect listener ports, DNS, routes, firewall, TLS certs, proxy config, and packet loss.

## Useful modern tools

Prefer available modern tools for inspection: `btop` or `bottom` for system view, `duf` and `dust` for disk, `procs` for processes, `mtr` for path latency, `jq`/`yq` for structured output. Fall back cleanly if missing.
