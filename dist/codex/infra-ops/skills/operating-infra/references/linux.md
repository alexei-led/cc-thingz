# Linux Hosts and Services

Capture current state before recovery steps that could lose data. Reboot, kill, delete, chmod/chown, package upgrades, and firewall changes need a clear target and blast radius first.

## Service troubleshooting

- Check service state, recent journal entries, config paths, environment files, ports, dependencies, and restart history.
- Failed starts: unit files, permissions, missing files, bind addresses, config validation, and exit codes.
- Log-heavy failures: narrow by time window and service name.

## Resources

- CPU: load, top processes, thread count, and recent deploys or cron jobs.
- Memory: RSS, OOM killer messages, cgroups, swap, and leak patterns.
- Disk: filesystem fullness, inode exhaustion, mount state, deleted-but-open files, and log growth.
- Network: listener ports, DNS, routes, firewall, TLS certs, proxy config, and packet loss.

Use modern tools when installed (`btop`, `duf`, `dust`, `procs`, `mtr`, `jq`/`yq`) and fall back to standard ones.
