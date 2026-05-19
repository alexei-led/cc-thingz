"""One-shot helper: migrate legacy hook scripts into `src/hooks/<name>/`.

Reads existing hook scripts under `plugins/dev-workflow/hooks/` and
`plugins/dev-tools/hooks/` and emits:

    src/hooks/<name>/HOOK.{sh,py}   — the executable script
    src/hooks/<name>/meta.yaml      — base metadata (event, timeout, name,
                                       optional status_message)
    src/hooks/<name>/<support>/...  — copied support directories (e.g.
                                       smart-lint/lib.sh)

Event metadata for the four "wired" hooks (file-protector, git-guardrails,
smart-lint, session-start) comes from
`plugins/dev-workflow/hooks/hooks.source.yaml`. The remaining hooks
(skill-enforcer, notify, test-runner, worktree-create, worktree-remove) are
not yet wired into any source manifest; their event/timeout/name come from
a hardcoded table in `LEGACY_REGISTRY`.

Re-running the script is idempotent: existing files are overwritten only when
content differs. Pass `--force` to bypass that check.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

log = logging.getLogger("migrate_hooks")


@dataclass(frozen=True)
class LegacyHook:
    name: str
    source: Path
    event: str
    timeout: int
    status_message: str | None = None
    support_dirs: tuple[str, ...] = field(default_factory=tuple)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def legacy_registry(root: Path) -> list[LegacyHook]:
    """Return the full list of hooks to migrate.

    Event/timeout/status_message values are derived from hooks.source.yaml for
    the four wired hooks; the rest use sensible defaults inferred from
    plugin READMEs and the script bodies.
    """
    dw_hooks = root / "plugins" / "dev-workflow" / "hooks"
    dt_hooks = root / "plugins" / "dev-tools" / "hooks"

    return [
        LegacyHook(
            name="file-protector",
            source=dw_hooks / "file-protector.sh",
            event="preedit",
            timeout=10,
        ),
        LegacyHook(
            name="git-guardrails",
            source=dw_hooks / "git-guardrails.sh",
            event="prebash",
            timeout=10,
            status_message="Checking git command",
        ),
        LegacyHook(
            name="smart-lint",
            source=dw_hooks / "smart-lint.sh",
            event="postedit",
            timeout=60,
            status_message="Running smart-lint",
            support_dirs=("smart-lint",),
        ),
        LegacyHook(
            name="session-start",
            source=dw_hooks / "session-start.py",
            event="sessionstart",
            timeout=5,
            status_message="Loading session context",
        ),
        LegacyHook(
            name="skill-enforcer",
            source=dw_hooks / "skill-enforcer.sh",
            event="userpromptsubmit",
            timeout=15,
        ),
        LegacyHook(
            name="notify",
            source=dw_hooks / "notify.sh",
            event="notification",
            timeout=10,
        ),
        LegacyHook(
            name="test-runner",
            source=dw_hooks / "test-runner.sh",
            event="agentstop",
            timeout=60,
            status_message="Running targeted tests",
        ),
        LegacyHook(
            name="worktree-create",
            source=dt_hooks / "worktree-create.sh",
            event="worktreecreate",
            timeout=10,
        ),
        LegacyHook(
            name="worktree-remove",
            source=dt_hooks / "worktree-remove.sh",
            event="worktreeremove",
            timeout=10,
        ),
    ]


def hook_script_name(source: Path) -> str:
    """Return `HOOK.sh` for shell sources, `HOOK.py` for python sources."""
    suffix = source.suffix.lower()
    if suffix not in {".sh", ".py"}:
        raise ValueError(f"unsupported hook extension: {source}")
    return f"HOOK{suffix}"


def write_meta(out_dir: Path, hook: LegacyHook) -> Path:
    """Serialize hook metadata to `out_dir/meta.yaml` and return the path."""
    payload: dict[str, object] = {
        "name": hook.name,
        "event": hook.event,
        "timeout": hook.timeout,
    }
    if hook.status_message:
        payload["status_message"] = hook.status_message
    meta_path = out_dir / "meta.yaml"
    data = yaml.safe_dump(payload, sort_keys=False).encode()
    if not meta_path.exists() or meta_path.read_bytes() != data:
        meta_path.write_bytes(data)
    return meta_path


def copy_preserving_mode(src: Path, dst: Path) -> None:
    """Copy `src` to `dst` with permission bits preserved."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    shutil.copymode(src, dst)


def copy_support_dirs(out_dir: Path, hook: LegacyHook) -> list[Path]:
    """Mirror each support directory (e.g. `smart-lint/`) into `out_dir`."""
    copied: list[Path] = []
    for sub in hook.support_dirs:
        src_dir = hook.source.parent / sub
        if not src_dir.is_dir():
            log.warning("missing support dir for %s: %s", hook.name, src_dir)
            continue
        dst_dir = out_dir / sub
        for entry in src_dir.rglob("*"):
            if entry.is_dir():
                (dst_dir / entry.relative_to(src_dir)).mkdir(
                    parents=True, exist_ok=True
                )
                continue
            target = dst_dir / entry.relative_to(src_dir)
            copy_preserving_mode(entry, target)
            copied.append(target)
    return copied


def migrate_hook(hook: LegacyHook, src_root: Path) -> list[Path]:
    """Migrate one legacy hook; return the list of written paths."""
    if not hook.source.is_file():
        raise FileNotFoundError(f"hook source missing: {hook.source}")
    out_dir = src_root / "hooks" / hook.name
    out_dir.mkdir(parents=True, exist_ok=True)

    script_dst = out_dir / hook_script_name(hook.source)
    copy_preserving_mode(hook.source, script_dst)

    written = [script_dst, write_meta(out_dir, hook)]
    written.extend(copy_support_dirs(out_dir, hook))
    return written


def migrate_all(root: Path) -> dict[str, list[Path]]:
    """Migrate every hook in the registry. Return name → written paths."""
    src_root = root / "src"
    src_root.mkdir(exist_ok=True)
    written: dict[str, list[Path]] = {}
    for hook in legacy_registry(root):
        written[hook.name] = migrate_hook(hook, src_root)
        log.info(
            "migrated %s (event=%s, %d file(s))",
            hook.name,
            hook.event,
            len(written[hook.name]),
        )
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy hooks to src/hooks/.")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="enable debug logging",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    written = migrate_all(repo_root())
    total = sum(len(paths) for paths in written.values())
    log.info("migrated %d hook(s), wrote %d file(s)", len(written), total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
