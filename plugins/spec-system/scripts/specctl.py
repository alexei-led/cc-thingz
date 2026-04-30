#!/usr/bin/env python3
"""
specctl - CLI for managing .spec/ task tracking system.

Simple YAML-frontmatter-based state management for spec-driven development.
All state lives in markdown files - no separate JSON state.

Usage:
    specctl init                    Create .spec/ structure
    specctl ready [--epic ID]       Show unblocked tasks in dependency order
    specctl start <id>              Mark task in-progress
    specctl done <id> [--summary/--files/--commits/--tests]  Mark task done
    specctl validate [--all]        Check for issues
    specctl status [ID]             Show progress overview
    specctl dep add <task> <dep>    Add dependency (task blocked by dep)
    specctl show <id>               Show task or epic details
"""

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# --- Constants ---

SPEC_DIR = ".spec"
REQS_DIR = "reqs"
EPICS_DIR = "epics"
TASKS_DIR = "tasks"
PROGRESS_FILE = "PROGRESS.md"
SESSION_FILE = "SESSION.yaml"

TASK_STATUS = ["todo", "in_progress", "done"]
EPIC_STATUS = ["open", "done"]
SESSION_STEPS = ["planning", "implementing", "testing", "reviewing", "completing"]


# --- Helpers ---


def get_repo_root() -> Path:
    """Find git repo root or current directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        return Path.cwd()


def get_spec_dir() -> Path:
    """Get .spec/ directory path."""
    return get_repo_root() / SPEC_DIR


def ensure_spec_exists() -> bool:
    """Check if .spec/ exists."""
    return get_spec_dir().exists()


def now_iso() -> str:
    """Current timestamp in ISO format."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_log() -> str:
    """Current timestamp for PROGRESS.md."""
    return datetime.now().strftime("%H:%M")


def error_exit(message: str, code: int = 1) -> None:
    """Print error and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(code)


def success_print(message: str) -> None:
    """Print success message."""
    print(f"✓ {message}")


# --- YAML Frontmatter Parser ---


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Returns (metadata dict, body text).
    """
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    yaml_part = parts[1].strip()
    body = parts[2].strip()

    # Simple YAML parser for our use case
    metadata: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] = []

    for line in yaml_part.split("\n"):
        line = line.rstrip()

        # Handle list items
        if line.startswith("  - "):
            if current_key:
                current_list.append(line[4:].strip())
            continue

        # Save previous list if any
        if current_key and current_list:
            metadata[current_key] = current_list
            current_list = []
            current_key = None

        # Handle key: value
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            if not value:
                # Start of a list
                current_key = key
            elif value.startswith("[") and value.endswith("]"):
                # Inline list
                items = value[1:-1].split(",")
                metadata[key] = [
                    item.strip().strip("\"'") for item in items if item.strip()
                ]
            else:
                # Simple value
                metadata[key] = value.strip("\"'")

    # Save final list if any
    if current_key and current_list:
        metadata[current_key] = current_list

    return metadata, body


def serialize_frontmatter(metadata: dict[str, Any], body: str) -> str:
    """Serialize metadata and body back to markdown with frontmatter."""
    lines = ["---"]

    for key, value in metadata.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        else:
            lines.append(f"{key}: {value}")

    lines.append("---")
    lines.append("")
    lines.append(body)

    return "\n".join(lines)


def update_frontmatter(filepath: Path, updates: dict[str, Any]) -> None:
    """Update frontmatter in a file."""
    content = filepath.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(content)
    metadata.update(updates)
    new_content = serialize_frontmatter(metadata, body)
    filepath.write_text(new_content, encoding="utf-8")


# --- Task/Epic Loading ---


def find_tasks(spec_dir: Path, epic_id: str | None = None) -> list[Path]:
    """Find all task files, optionally filtered by epic."""
    tasks_dir = spec_dir / TASKS_DIR
    if not tasks_dir.exists():
        return []

    tasks = list(tasks_dir.glob("TASK-*.md"))

    if epic_id:
        filtered = []
        for task_path in tasks:
            content = task_path.read_text(encoding="utf-8")
            metadata, _ = parse_frontmatter(content)
            if metadata.get("epic") == epic_id:
                filtered.append(task_path)
        return filtered

    return tasks


def find_epics(spec_dir: Path) -> list[Path]:
    """Find all epic files."""
    epics_dir = spec_dir / EPICS_DIR
    if not epics_dir.exists():
        return []
    return list(epics_dir.glob("EPIC-*.md"))


def find_reqs(spec_dir: Path) -> list[Path]:
    """Find all requirement files."""
    reqs_dir = spec_dir / REQS_DIR
    if not reqs_dir.exists():
        return []
    return list(reqs_dir.glob("REQ-*.md"))


def load_task(task_path: Path) -> dict[str, Any]:
    """Load task metadata and body."""
    content = task_path.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(content)
    return {
        "path": task_path,
        "metadata": metadata,
        "body": body,
        "id": metadata.get("id", task_path.stem),
    }


def load_epic(epic_path: Path) -> dict[str, Any]:
    """Load epic metadata and body."""
    content = epic_path.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(content)
    return {
        "path": epic_path,
        "metadata": metadata,
        "body": body,
        "id": metadata.get("id", epic_path.stem),
    }


# --- Dependency Resolution ---


def would_create_cycle(
    spec_dir: Path, task_id: str, new_dep_id: str
) -> list[str] | None:
    """Check if adding task_id -> new_dep_id would create a cycle.

    Returns the cycle path if found, None otherwise.
    Uses DFS from new_dep_id following blocked-by to see if we reach task_id.
    """
    all_tasks = [load_task(p) for p in find_tasks(spec_dir)]
    task_map = {t["id"]: t for t in all_tasks}

    def get_deps(tid: str) -> list[str]:
        """Get dependencies for a task."""
        task = task_map.get(tid)
        if not task:
            return []
        blocked_by = task["metadata"].get("blocked-by", [])
        if isinstance(blocked_by, str):
            blocked_by = [blocked_by]
        return blocked_by

    # DFS from new_dep_id to see if we can reach task_id
    def dfs(current: str, path: list[str]) -> list[str] | None:
        if current == task_id:
            return path + [current]  # Found cycle

        deps = get_deps(current)
        # Also consider the new dependency we're about to add
        if current == task_id:
            deps = deps + [new_dep_id]

        for dep in deps:
            if dep in path:
                continue  # Already in path, skip
            result = dfs(dep, path + [current])
            if result:
                return result
        return None

    # Start from new_dep_id and see if we reach task_id
    return dfs(new_dep_id, [])


def get_ready_tasks(spec_dir: Path, epic_id: str | None = None) -> list[dict]:
    """Get tasks that are ready to start (todo + no blockers)."""
    task_paths = find_tasks(spec_dir, epic_id)

    # Load all tasks
    tasks = [load_task(p) for p in task_paths]

    # Build completion set
    done_ids = {t["id"] for t in tasks if t["metadata"].get("status") == "done"}

    # Find ready tasks
    ready = []
    for task in tasks:
        meta = task["metadata"]
        if meta.get("status") != "todo":
            continue

        blocked_by = meta.get("blocked-by", [])
        if isinstance(blocked_by, str):
            blocked_by = [blocked_by]

        # Check if all blockers are done
        unmet = [b for b in blocked_by if b not in done_ids]
        if not unmet:
            ready.append(task)

    # Sort by priority (critical > normal > low)
    priority_order = {"critical": 0, "normal": 1, "low": 2}
    ready.sort(
        key=lambda t: priority_order.get(t["metadata"].get("priority", "normal"), 1)
    )

    return ready


def get_blocked_tasks(
    spec_dir: Path, epic_id: str | None = None
) -> list[tuple[dict, list[str]]]:
    """Get tasks that are blocked with their unmet dependencies."""
    task_paths = find_tasks(spec_dir, epic_id)
    tasks = [load_task(p) for p in task_paths]
    done_ids = {t["id"] for t in tasks if t["metadata"].get("status") == "done"}

    blocked = []
    for task in tasks:
        meta = task["metadata"]
        if meta.get("status") != "todo":
            continue

        blocked_by = meta.get("blocked-by", [])
        if isinstance(blocked_by, str):
            blocked_by = [blocked_by]

        unmet = [b for b in blocked_by if b not in done_ids]
        if unmet:
            blocked.append((task, unmet))

    return blocked


# --- Git Hook ---

PRE_COMMIT_HOOK = """\
#!/usr/bin/env bash
# specctl pre-commit hook - validates .spec/ files before commit

# Check if any .spec/ files are staged
staged_spec=$(git diff --cached --name-only | grep -E '^\\.spec/' || true)

if [ -n "$staged_spec" ]; then
    echo "Validating .spec/ files..."
    if ! specctl validate 2>&1; then
        echo ""
        echo "ERROR: .spec/ validation failed. Fix issues before committing."
        exit 1
    fi
    echo "✓ .spec/ validation passed"
fi
"""


def install_git_hook() -> bool:
    """Install git pre-commit hook for .spec/ validation.

    Returns True if installed, False if skipped.
    """
    repo_root = get_repo_root()
    hooks_dir = repo_root / ".git" / "hooks"

    if not hooks_dir.exists():
        return False

    hook_path = hooks_dir / "pre-commit"

    # Check if hook already exists
    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8")
        if "specctl validate" in existing:
            return True  # Already installed

        # Append to existing hook
        if not existing.endswith("\n"):
            existing += "\n"
        existing += "\n# specctl validation\n"
        existing += PRE_COMMIT_HOOK.split("\n", 2)[2]  # Skip shebang + comment
        hook_path.write_text(existing, encoding="utf-8")
    else:
        hook_path.write_text(PRE_COMMIT_HOOK, encoding="utf-8")

    # Make executable
    hook_path.chmod(0o755)
    return True


# --- Session State ---


def get_session_path() -> Path:
    """Get path to SESSION.yaml."""
    return get_spec_dir() / SESSION_FILE


def load_session() -> dict[str, Any]:
    """Load current session state."""
    session_path = get_session_path()
    if not session_path.exists():
        return {}

    content = session_path.read_text(encoding="utf-8")
    # Simple YAML parsing for session state
    session: dict[str, Any] = {}
    for line in content.strip().split("\n"):
        if ":" in line and not line.startswith("#"):
            key, _, value = line.partition(":")
            session[key.strip()] = value.strip()
    return session


def save_session(session: dict[str, Any]) -> None:
    """Save session state."""
    session_path = get_session_path()
    lines = ["# Session state - auto-managed by specctl"]
    for key, value in session.items():
        lines.append(f"{key}: {value}")
    session_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def clear_session() -> None:
    """Clear session state."""
    session_path = get_session_path()
    if session_path.exists():
        session_path.unlink()


def session_start(task_id: str, base_commit: str | None = None) -> None:
    """Start a session for a task."""
    session = {
        "task": task_id,
        "step": "planning",
        "started": now_iso(),
    }
    if base_commit:
        session["base_commit"] = base_commit
    else:
        # Get current HEAD
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            session["base_commit"] = result.stdout.strip()
        except subprocess.CalledProcessError:
            pass
    save_session(session)


def session_update_step(step: str) -> None:
    """Update session step."""
    session = load_session()
    if session:
        session["step"] = step
        save_session(session)


def session_end() -> None:
    """End current session."""
    clear_session()


# --- Progress Logging ---


def log_progress(action: str, target: str) -> None:
    """Append to PROGRESS.md and truncate to last 10 entries."""
    spec_dir = get_spec_dir()
    progress_path = spec_dir / PROGRESS_FILE

    # Read existing
    lines = []
    if progress_path.exists():
        lines = progress_path.read_text(encoding="utf-8").strip().split("\n")

    # Add new entry
    lines.append(f"{now_log()} {action} {target}")

    # Keep last 10
    if len(lines) > 10:
        lines = lines[-10:]

    progress_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- Commands ---


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize .spec/ directory structure."""
    spec_dir = get_spec_dir()

    if spec_dir.exists():
        print(f".spec/ already exists at {spec_dir}")
        return

    # Create structure
    (spec_dir / REQS_DIR).mkdir(parents=True)
    (spec_dir / EPICS_DIR).mkdir(parents=True)
    (spec_dir / TASKS_DIR).mkdir(parents=True)

    # Create PROGRESS.md
    progress_path = spec_dir / PROGRESS_FILE
    progress_path.write_text(f"{now_log()} INIT .spec/\n", encoding="utf-8")

    success_print(f"Created .spec/ at {spec_dir}")

    # Install git hook
    if install_git_hook():
        success_print("Installed git pre-commit hook for .spec/ validation")

    print("\nNext steps:")
    print("  1. Create a requirement: specctl new req auth")
    print("  2. Or interview for requirements: /spec:interview 'your feature idea'")


def cmd_ready(args: argparse.Namespace) -> None:
    """Show tasks ready to start."""
    if not ensure_spec_exists():
        error_exit(".spec/ not found. Run 'specctl init' first.")

    spec_dir = get_spec_dir()
    ready = get_ready_tasks(spec_dir, args.epic)

    if getattr(args, "json", False):
        items = [
            {
                "id": t["id"],
                "priority": t["metadata"].get("priority", "normal"),
                "title": t["body"].strip().split("\n")[0].lstrip("# "),
            }
            for t in ready
        ]
        print(json.dumps(items))
        return

    if not ready:
        print("No tasks ready to start.")

        # Show blocked tasks
        blocked = get_blocked_tasks(spec_dir, args.epic)
        if blocked:
            print("\nBlocked tasks:")
            for task, unmet in blocked:
                print(f"  {task['id']} (waiting for: {', '.join(unmet)})")
        return

    print("Ready tasks (in priority order):\n")
    for task in ready:
        meta = task["metadata"]
        priority = meta.get("priority", "normal")
        epic = meta.get("epic", "-")
        print(f"  {task['id']:30} priority={priority:8} epic={epic}")

    if ready:
        print(f"\nStart work: specctl start {ready[0]['id']}")


def cmd_start(args: argparse.Namespace) -> None:
    """Mark task as in_progress."""
    if not ensure_spec_exists():
        error_exit(".spec/ not found. Run 'specctl init' first.")

    spec_dir = get_spec_dir()
    task_id = args.id

    # Find task file
    task_path = spec_dir / TASKS_DIR / f"{task_id}.md"
    if not task_path.exists():
        error_exit(f"Task not found: {task_id}")

    task = load_task(task_path)
    current_status = task["metadata"].get("status", "todo")

    if current_status == "in_progress":
        print(f"Task {task_id} is already in_progress")
        return

    if current_status == "done":
        error_exit(f"Task {task_id} is already done")

    # Check for existing session
    existing = load_session()
    if existing and existing.get("task") != task_id:
        print(f"Warning: Session exists for {existing.get('task')}")
        print("  Use 'specctl session clear' to clear it first")

    # Update status
    update_frontmatter(task_path, {"status": "in_progress"})
    log_progress("START", task_id)

    # Start session tracking
    session_start(task_id)

    success_print(f"Started {task_id}")
    session = load_session()
    if session.get("base_commit"):
        print(f"  Base commit: {session['base_commit']}")


def cmd_done(args: argparse.Namespace) -> None:
    """Mark task as done with optional evidence."""
    if not ensure_spec_exists():
        error_exit(".spec/ not found. Run 'specctl init' first.")

    spec_dir = get_spec_dir()
    task_id = args.id

    # Find task file
    task_path = spec_dir / TASKS_DIR / f"{task_id}.md"
    if not task_path.exists():
        error_exit(f"Task not found: {task_id}")

    task = load_task(task_path)

    # Build updates
    updates: dict[str, Any] = {
        "status": "done",
        "done-at": now_iso(),
    }

    if args.summary:
        updates["done-summary"] = args.summary
    if args.files:
        updates["done-files"] = [f.strip() for f in args.files.split(",")]
    if args.commits:
        updates["done-commits"] = [c.strip() for c in args.commits.split(",")]
    if args.tests:
        updates["done-tests"] = args.tests

    # Update
    update_frontmatter(task_path, updates)
    log_progress("DONE", task_id)

    # End session
    session_end()

    success_print(f"Completed {task_id}")

    # Check for newly unblocked tasks
    ready = get_ready_tasks(spec_dir, task["metadata"].get("epic"))
    if ready:
        print(f"\nNewly unblocked: {', '.join(t['id'] for t in ready[:3])}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate .spec/ for issues."""
    if not ensure_spec_exists():
        error_exit(".spec/ not found. Run 'specctl init' first.")

    spec_dir = get_spec_dir()
    issues: list[str] = []

    # Check tasks
    for task_path in find_tasks(spec_dir):
        task = load_task(task_path)
        meta = task["metadata"]
        task_id = task["id"]

        # Required fields
        if "status" not in meta:
            issues.append(f"{task_id}: missing 'status' field")

        # Check blocked-by references exist
        blocked_by = meta.get("blocked-by", [])
        if isinstance(blocked_by, str):
            blocked_by = [blocked_by]

        for dep in blocked_by:
            dep_path = spec_dir / TASKS_DIR / f"{dep}.md"
            if not dep_path.exists():
                issues.append(
                    f"{task_id}: blocked-by references non-existent task '{dep}'"
                )

    # Check epics
    for epic_path in find_epics(spec_dir):
        epic = load_epic(epic_path)
        meta = epic["metadata"]
        epic_id = epic["id"]

        if "status" not in meta:
            issues.append(f"{epic_id}: missing 'status' field")

        # Check task references
        tasks = meta.get("tasks", [])
        if isinstance(tasks, str):
            tasks = [tasks]

        for task_ref in tasks:
            task_path = spec_dir / TASKS_DIR / f"{task_ref}.md"
            if not task_path.exists():
                issues.append(f"{epic_id}: references non-existent task '{task_ref}'")

    # Check for dependency cycles
    all_tasks = [load_task(p) for p in find_tasks(spec_dir)]

    def has_cycle(task_id: str, visited: set, path: set) -> bool:
        if task_id in path:
            return True
        if task_id in visited:
            return False

        visited.add(task_id)
        path.add(task_id)

        # Find task
        task = next((t for t in all_tasks if t["id"] == task_id), None)
        if task:
            blocked_by = task["metadata"].get("blocked-by", [])
            if isinstance(blocked_by, str):
                blocked_by = [blocked_by]
            for dep in blocked_by:
                if has_cycle(dep, visited, path):
                    return True

        path.remove(task_id)
        return False

    for task in all_tasks:
        if has_cycle(task["id"], set(), set()):
            issues.append(f"{task['id']}: part of a dependency cycle")
            break

    if issues:
        print("Validation issues found:\n")
        for issue in issues:
            print(f"  • {issue}")
        sys.exit(1)
    else:
        success_print("No issues found")


def cmd_status(args: argparse.Namespace) -> None:
    """Show progress overview."""
    if not ensure_spec_exists():
        error_exit(".spec/ not found. Run 'specctl init' first.")

    spec_dir = get_spec_dir()

    # If specific ID provided
    if args.id:
        # Try task first
        task_path = spec_dir / TASKS_DIR / f"{args.id}.md"
        if task_path.exists():
            task = load_task(task_path)
            print(f"Task: {task['id']}")
            print(f"Status: {task['metadata'].get('status', 'unknown')}")
            print(f"Priority: {task['metadata'].get('priority', 'normal')}")
            print(f"Epic: {task['metadata'].get('epic', '-')}")
            blocked = task["metadata"].get("blocked-by", [])
            if blocked:
                print(
                    "Blocked by: "
                    f"{', '.join(blocked) if isinstance(blocked, list) else blocked}"
                )
            return

        # Try epic
        epic_path = spec_dir / EPICS_DIR / f"{args.id}.md"
        if epic_path.exists():
            epic = load_epic(epic_path)
            print(f"Epic: {epic['id']}")
            print(f"Status: {epic['metadata'].get('status', 'unknown')}")
            print(f"Implements: {epic['metadata'].get('implements', '-')}")
            tasks = epic["metadata"].get("tasks", [])
            if tasks:
                print(
                    f"Tasks: {', '.join(tasks) if isinstance(tasks, list) else tasks}"
                )
            return

        error_exit(f"Not found: {args.id}")

    # Overview
    all_tasks = [load_task(p) for p in find_tasks(spec_dir)]
    all_epics = [load_epic(p) for p in find_epics(spec_dir)]
    all_reqs = find_reqs(spec_dir)

    todo = [t for t in all_tasks if t["metadata"].get("status") == "todo"]
    in_progress = [t for t in all_tasks if t["metadata"].get("status") == "in_progress"]
    done = [t for t in all_tasks if t["metadata"].get("status") == "done"]

    if getattr(args, "json", False):
        print(
            json.dumps(
                {
                    "total": len(all_tasks),
                    "done": len(done),
                    "in_progress": len(in_progress),
                    "todo": len(todo),
                }
            )
        )
        return

    print("═══════════════════════════════════════════════════")
    print("                  SPEC STATUS                       ")
    print("═══════════════════════════════════════════════════")
    print(f"Requirements: {len(all_reqs)}")
    done_epics = sum(1 for e in all_epics if e["metadata"].get("status") == "done")
    print(f"Epics:        {len(all_epics)} ({done_epics} done)")
    print(
        f"Tasks:        {len(all_tasks)}"
        f" ({len(done)} done,"
        f" {len(in_progress)} in progress,"
        f" {len(todo)} todo)"
    )
    print("───────────────────────────────────────────────────")

    if in_progress:
        print("\nIn Progress:")
        for task in in_progress:
            print(f"  → {task['id']}")

    ready = get_ready_tasks(spec_dir)
    if ready:
        print("\nReady to Start:")
        for task in ready[:5]:
            print(f"  • {task['id']}")
        if len(ready) > 5:
            print(f"  ... and {len(ready) - 5} more")

    # Recent progress
    progress_path = spec_dir / PROGRESS_FILE
    if progress_path.exists():
        lines = progress_path.read_text(encoding="utf-8").strip().split("\n")
        if lines:
            print("\nRecent Activity:")
            for line in lines[-5:]:
                print(f"  {line}")


def cmd_dep_list(args: argparse.Namespace) -> None:
    """List dependencies for a task."""
    if not ensure_spec_exists():
        error_exit(".spec/ not found. Run 'specctl init' first.")

    spec_dir = get_spec_dir()
    task_id = args.task

    task_path = spec_dir / TASKS_DIR / f"{task_id}.md"
    if not task_path.exists():
        error_exit(f"Task not found: {task_id}")

    task = load_task(task_path)
    blocked_by = task["metadata"].get("blocked-by", [])
    if isinstance(blocked_by, str):
        blocked_by = [blocked_by]
    discovered_from = task["metadata"].get("discovered-from", [])
    if isinstance(discovered_from, str):
        discovered_from = [discovered_from]

    if not blocked_by and not discovered_from:
        print(f"{task_id}: no dependencies")
        return

    print(f"Dependencies for {task_id}:\n")
    if blocked_by:
        print("  blocked-by:")
        for dep in blocked_by:
            print(f"    - {dep}")
    if discovered_from:
        print("  discovered-from:")
        for dep in discovered_from:
            print(f"    - {dep}")


def cmd_dep_add(args: argparse.Namespace) -> None:
    """Add dependency: task depends on dep."""
    if not ensure_spec_exists():
        error_exit(".spec/ not found. Run 'specctl init' first.")

    spec_dir = get_spec_dir()
    task_id = args.task
    dep_id = args.dep

    # Verify both exist
    task_path = spec_dir / TASKS_DIR / f"{task_id}.md"
    dep_path = spec_dir / TASKS_DIR / f"{dep_id}.md"

    if not task_path.exists():
        error_exit(f"Task not found: {task_id}")
    if not dep_path.exists():
        error_exit(f"Dependency not found: {dep_id}")

    # Load task
    task = load_task(task_path)
    blocked_by = task["metadata"].get("blocked-by", [])
    if isinstance(blocked_by, str):
        blocked_by = [blocked_by]

    dep_type = getattr(args, "type", "blocks")

    if dep_type == "discovered-from":
        # discovered-from: informational link, no cycle check
        discovered = task["metadata"].get("discovered-from", [])
        if isinstance(discovered, str):
            discovered = [discovered]
        if dep_id in discovered:
            print(f"{task_id} already discovered-from {dep_id}")
            return
        discovered.append(dep_id)
        update_frontmatter(task_path, {"discovered-from": discovered})
        success_print(f"{task_id} discovered-from {dep_id}")
        return

    # blocks (default): blocked-by with cycle check
    if dep_id in blocked_by:
        print(f"{task_id} already depends on {dep_id}")
        return

    cycle = would_create_cycle(spec_dir, task_id, dep_id)
    if cycle:
        cycle_str = " → ".join(cycle)
        error_exit(f"Cannot add dependency: would create cycle: {cycle_str}")

    blocked_by.append(dep_id)
    update_frontmatter(task_path, {"blocked-by": blocked_by})

    success_print(f"{task_id} now blocked by {dep_id}")


def cmd_dep_rm(args: argparse.Namespace) -> None:
    """Remove dependency: task no longer depends on dep."""
    if not ensure_spec_exists():
        error_exit(".spec/ not found. Run 'specctl init' first.")

    spec_dir = get_spec_dir()
    task_id = args.task
    dep_id = args.dep

    # Verify task exists
    task_path = spec_dir / TASKS_DIR / f"{task_id}.md"
    if not task_path.exists():
        error_exit(f"Task not found: {task_id}")

    # Load task
    task = load_task(task_path)
    blocked_by = task["metadata"].get("blocked-by", [])
    if isinstance(blocked_by, str):
        blocked_by = [blocked_by]

    if dep_id not in blocked_by:
        print(f"{task_id} does not depend on {dep_id}")
        return

    blocked_by.remove(dep_id)
    update_frontmatter(task_path, {"blocked-by": blocked_by})

    success_print(f"Removed {dep_id} from {task_id} dependencies")


def cmd_epic_close(args: argparse.Namespace) -> None:
    """Mark epic as done."""
    if not ensure_spec_exists():
        error_exit(".spec/ not found. Run 'specctl init' first.")

    spec_dir = get_spec_dir()
    epic_id = args.id

    # Find epic file
    epic_path = spec_dir / EPICS_DIR / f"{epic_id}.md"
    if not epic_path.exists():
        error_exit(f"Epic not found: {epic_id}")

    epic = load_epic(epic_path)
    current_status = epic["metadata"].get("status", "open")

    if current_status == "done":
        print(f"Epic {epic_id} is already done")
        return

    # Check if all tasks are done
    tasks = epic["metadata"].get("tasks", [])
    if isinstance(tasks, str):
        tasks = [tasks]

    incomplete = []
    for task_ref in tasks:
        task_path = spec_dir / TASKS_DIR / f"{task_ref}.md"
        if task_path.exists():
            task = load_task(task_path)
            if task["metadata"].get("status") != "done":
                incomplete.append(task_ref)

    if incomplete and not args.force:
        error_exit(
            "Epic has incomplete tasks: "
            f"{', '.join(incomplete)}."
            " Use --force to close anyway."
        )

    update_frontmatter(epic_path, {"status": "done"})
    log_progress("CLOSE", epic_id)

    success_print(f"Closed epic {epic_id}")


def cmd_reset(args: argparse.Namespace) -> None:
    """Reset task status back to todo."""
    if not ensure_spec_exists():
        error_exit(".spec/ not found. Run 'specctl init' first.")

    spec_dir = get_spec_dir()
    task_id = args.id

    task_path = spec_dir / TASKS_DIR / f"{task_id}.md"
    if not task_path.exists():
        error_exit(f"Task not found: {task_id}")

    task = load_task(task_path)
    current_status = task["metadata"].get("status", "todo")

    if current_status == "todo":
        print(f"Task {task_id} is already todo")
        return

    # Reset to todo, remove done-* fields
    content = task_path.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(content)

    # Remove done-* fields
    keys_to_remove = [k for k in metadata.keys() if k.startswith("done-")]
    for key in keys_to_remove:
        del metadata[key]

    metadata["status"] = "todo"
    new_content = serialize_frontmatter(metadata, body)
    task_path.write_text(new_content, encoding="utf-8")

    log_progress("RESET", task_id)
    success_print(f"Reset {task_id} to todo")


def cmd_show(args: argparse.Namespace) -> None:
    """Show task or epic details including body."""
    if not ensure_spec_exists():
        error_exit(".spec/ not found. Run 'specctl init' first.")

    spec_dir = get_spec_dir()
    item_id = args.id

    # Try task
    task_path = spec_dir / TASKS_DIR / f"{item_id}.md"
    if task_path.exists():
        print(task_path.read_text(encoding="utf-8"))
        return

    # Try epic
    epic_path = spec_dir / EPICS_DIR / f"{item_id}.md"
    if epic_path.exists():
        print(epic_path.read_text(encoding="utf-8"))
        return

    # Try req
    req_path = spec_dir / REQS_DIR / f"{item_id}.md"
    if req_path.exists():
        print(req_path.read_text(encoding="utf-8"))
        return

    error_exit(f"Not found: {item_id}")


def cmd_hook(args: argparse.Namespace) -> None:
    """Install or manage git hooks."""
    if args.hook_command == "install":
        if install_git_hook():
            success_print("Installed git pre-commit hook for .spec/ validation")
        else:
            error_exit("Could not install hook (not in a git repository?)")
    elif args.hook_command == "status":
        repo_root = get_repo_root()
        hook_path = repo_root / ".git" / "hooks" / "pre-commit"
        if hook_path.exists():
            content = hook_path.read_text(encoding="utf-8")
            if "specctl validate" in content:
                success_print("Pre-commit hook is installed")
            else:
                print("Pre-commit hook exists but doesn't include specctl validation")
        else:
            print("No pre-commit hook installed")


def cmd_session(args: argparse.Namespace) -> None:
    """Manage session state."""
    if not ensure_spec_exists():
        error_exit(".spec/ not found. Run 'specctl init' first.")

    if args.session_command == "show":
        session = load_session()
        if not session:
            if getattr(args, "json", False):
                print(json.dumps({}))
            else:
                print("No active session")
            return

        if getattr(args, "json", False):
            print(json.dumps(session))
            return

        print("Active Session:")
        print(f"  Task: {session.get('task', 'unknown')}")
        print(f"  Step: {session.get('step', 'unknown')}")
        print(f"  Started: {session.get('started', 'unknown')}")
        if session.get("base_commit"):
            print(f"  Base commit: {session['base_commit']}")

    elif args.session_command == "clear":
        session = load_session()
        if session:
            session_end()
            success_print(f"Cleared session for {session.get('task', 'unknown')}")
        else:
            print("No active session to clear")

    elif args.session_command == "step":
        session = load_session()
        if not session:
            error_exit("No active session")

        step = args.step
        if step not in SESSION_STEPS:
            error_exit(f"Invalid step: {step}. Valid: {', '.join(SESSION_STEPS)}")

        session_update_step(step)
        success_print(f"Session step: {step}")

    elif args.session_command == "resume":
        session = load_session()
        if not session:
            if getattr(args, "json", False):
                print(json.dumps({}))
            else:
                print("No session to resume")
            return

        task_id = session.get("task")
        step = session.get("step", "planning")
        base = session.get("base_commit", "")

        if getattr(args, "json", False):
            print(json.dumps({"task": task_id, "step": step, "base_commit": base}))
            return

        print("Session Recovery Info:")
        print(f"  Task: {task_id}")
        print(f"  Step: {step}")
        print(f"  Base: {base}")
        print(f"\nTo continue: /spec:work {task_id}")

    elif args.session_command == "handoff":
        session = load_session()
        task_id = session.get("task", "") if session else ""
        step = session.get("step", "") if session else ""
        base_commit = session.get("base_commit", "") if session else ""

        # Git diff stat
        diff_stat = ""
        if base_commit:
            try:
                result = subprocess.run(
                    ["git", "diff", "--stat", f"{base_commit}..HEAD"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                diff_stat = result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        # Ready tasks
        spec_dir = get_spec_dir()
        ready = get_ready_tasks(spec_dir)
        ready_ids = [t["id"] for t in ready[:5]]

        if getattr(args, "json", False):
            print(
                json.dumps(
                    {
                        "task": task_id,
                        "step": step,
                        "base_commit": base_commit,
                        "diff_stat": diff_stat,
                        "ready": ready_ids,
                    }
                )
            )
            return

        print("--- SESSION HANDOFF ---")
        if task_id:
            print(f"Task: {task_id} (step: {step})")
        else:
            print("Task: none")
        if diff_stat:
            print(f"Changes:\n{diff_stat}")
        else:
            print("Changes: none")
        if ready_ids:
            print(f"Next ready: {', '.join(ready_ids)}")
        else:
            print("Next ready: none")
        if task_id:
            print(f"Resume: /spec:work {task_id}")
        print("---")


# --- Main ---


def main() -> None:
    parser = argparse.ArgumentParser(
        description="specctl - Spec-driven development CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    specctl init                        Initialize .spec/
    specctl ready                       Show tasks ready to start
    specctl ready --epic EPIC-auth      Show ready tasks for specific epic
    specctl start TASK-login            Start working on a task
    specctl done TASK-login             Mark task complete
    specctl done TASK-login --summary "Added login form" --files "src/login.ts"
    specctl reset TASK-login            Reset task back to todo
    specctl validate                    Check for issues
    specctl status                      Show overview
    specctl dep add TASK-b TASK-a       TASK-b depends on TASK-a
    specctl dep add TASK-b TASK-a --type discovered-from  Informational link
    specctl dep rm TASK-b TASK-a        Remove dependency
    specctl dep list TASK-b             List all dependencies
    specctl epic close EPIC-auth        Mark epic as done
    specctl show TASK-login             Show task details
    specctl hook install                Install git pre-commit hook
    specctl hook status                 Check if hook is installed
    specctl session show                Show active session
    specctl session show --json         JSON output
    specctl session step implementing   Update session step
    specctl session resume              Show recovery info
    specctl session handoff             Generate handoff summary
    specctl session clear               Clear session state
    specctl status --json               JSON status overview
    specctl ready --json                JSON ready tasks
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    subparsers.add_parser("init", help="Initialize .spec/ directory")

    # ready
    ready_parser = subparsers.add_parser("ready", help="Show tasks ready to start")
    ready_parser.add_argument("--epic", help="Filter by epic ID")
    ready_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # start
    start_parser = subparsers.add_parser("start", help="Mark task as in_progress")
    start_parser.add_argument("id", help="Task ID")

    # done
    done_parser = subparsers.add_parser("done", help="Mark task as done")
    done_parser.add_argument("id", help="Task ID")
    done_parser.add_argument("--summary", help="Summary of what was done")
    done_parser.add_argument("--files", help="Comma-separated list of changed files")
    done_parser.add_argument("--commits", help="Comma-separated list of commit hashes")
    done_parser.add_argument("--tests", help="Test results")

    # validate
    validate_parser = subparsers.add_parser("validate", help="Check for issues")
    validate_parser.add_argument("--all", action="store_true", help="Check everything")

    # status
    status_parser = subparsers.add_parser("status", help="Show progress overview")
    status_parser.add_argument("id", nargs="?", help="Specific task/epic ID")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # reset
    reset_parser = subparsers.add_parser("reset", help="Reset task back to todo")
    reset_parser.add_argument("id", help="Task ID")

    # dep
    dep_parser = subparsers.add_parser("dep", help="Manage dependencies")
    dep_subparsers = dep_parser.add_subparsers(dest="dep_command", required=True)

    dep_add_parser = dep_subparsers.add_parser("add", help="Add dependency")
    dep_add_parser.add_argument("task", help="Task that depends on another")
    dep_add_parser.add_argument("dep", help="Task that must be done first")
    dep_add_parser.add_argument(
        "--type",
        choices=["blocks", "discovered-from"],
        default="blocks",
        help="Dependency type (default: blocks)",
    )

    dep_rm_parser = dep_subparsers.add_parser("rm", help="Remove dependency")
    dep_rm_parser.add_argument("task", help="Task to remove dependency from")
    dep_rm_parser.add_argument("dep", help="Dependency to remove")

    dep_list_parser = dep_subparsers.add_parser("list", help="List dependencies")
    dep_list_parser.add_argument("task", help="Task to list dependencies for")

    # epic
    epic_parser = subparsers.add_parser("epic", help="Manage epics")
    epic_subparsers = epic_parser.add_subparsers(dest="epic_command", required=True)

    epic_close_parser = epic_subparsers.add_parser("close", help="Mark epic as done")
    epic_close_parser.add_argument("id", help="Epic ID")
    epic_close_parser.add_argument(
        "--force", action="store_true", help="Close even if tasks incomplete"
    )

    # show
    show_parser = subparsers.add_parser("show", help="Show item details")
    show_parser.add_argument("id", help="Task, epic, or requirement ID")

    # hook
    hook_parser = subparsers.add_parser("hook", help="Manage git hooks")
    hook_subparsers = hook_parser.add_subparsers(dest="hook_command", required=True)
    hook_subparsers.add_parser("install", help="Install pre-commit hook")
    hook_subparsers.add_parser("status", help="Check hook status")

    # session
    session_parser = subparsers.add_parser("session", help="Manage session state")
    session_subparsers = session_parser.add_subparsers(
        dest="session_command", required=True
    )
    session_show_parser = session_subparsers.add_parser(
        "show", help="Show current session"
    )
    session_show_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    session_subparsers.add_parser("clear", help="Clear session state")
    session_resume_parser = session_subparsers.add_parser(
        "resume", help="Show recovery info"
    )
    session_resume_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    session_handoff_parser = session_subparsers.add_parser(
        "handoff", help="Generate session handoff summary"
    )
    session_handoff_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    session_step_parser = session_subparsers.add_parser("step", help="Update step")
    session_step_parser.add_argument(
        "step", choices=SESSION_STEPS, help="New step value"
    )

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "ready":
        cmd_ready(args)
    elif args.command == "start":
        cmd_start(args)
    elif args.command == "done":
        cmd_done(args)
    elif args.command == "reset":
        cmd_reset(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "dep":
        if args.dep_command == "add":
            cmd_dep_add(args)
        elif args.dep_command == "rm":
            cmd_dep_rm(args)
        elif args.dep_command == "list":
            cmd_dep_list(args)
    elif args.command == "epic":
        if args.epic_command == "close":
            cmd_epic_close(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "hook":
        cmd_hook(args)
    elif args.command == "session":
        cmd_session(args)


if __name__ == "__main__":
    main()
