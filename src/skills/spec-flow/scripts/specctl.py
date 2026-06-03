#!/usr/bin/env python3
"""Tiny markdown-state CLI for spec-flow.

Skills do planning and implementation. This CLI only owns durable state:
artifacts, readiness, sessions, checkpoints, completion evidence, and validation.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from datetime import timezone as _timezone
from pathlib import Path
from typing import Any, NoReturn

try:
    from datetime import UTC
except ImportError:  # Python < 3.11 on some agent hosts.
    UTC = _timezone(timedelta(0))

SPEC_DIR = ".spec"
TASKS_DIR = "tasks"
REQS_DIR = "reqs"
EPICS_DIR = "epics"
MEMORY_DIR = "memory"
PROGRESS_FILE = "PROGRESS.md"
SESSION_FILE = "SESSION.yaml"

TASK_PREFIX = "TASK-"
REQ_PREFIX = "REQ-"
EPIC_PREFIX = "EPIC-"

TODO = "todo"
IN_PROGRESS = "in-progress"
DONE = "done"
LEGACY_IN_PROGRESS = "in_progress"
TASK_STATES = {TODO, IN_PROGRESS, DONE}
SESSION_STEPS = {"planning", "implementing", "testing", "reviewing", "completing"}
PRIORITY = {"critical": 0, "normal": 1, "low": 2}
PLACEHOLDERS = {
    "tbd",
    "todo",
    "describe",
    "observable behavior is defined",
    "verification command or manual check is defined",
    "it works",
    "criterion is observable",
}


class Artifact(dict[str, Any]):
    """Small typed-ish dict for loaded markdown artifacts."""


# --- process and paths ---


def fail(message: str, code: int = 1) -> NoReturn:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(code)


def ok(message: str) -> None:
    print(f"✓ {message}")


def root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (FileNotFoundError, subprocess.CalledProcessError):
        return Path.cwd()


def spec_dir() -> Path:
    return root() / SPEC_DIR


def require_spec() -> Path:
    path = spec_dir()
    if not path.exists():
        fail(".spec/ not found. Run 'specctl init' first.")
    return path


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_log() -> str:
    return datetime.now().strftime("%H:%M")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(root()))
    except ValueError:
        return str(path)


# --- markdown frontmatter ---


def strip_comment(value: str) -> str:
    if value.startswith("[") and "]" in value:
        return value[: value.index("]") + 1].strip()
    return value.split(" #", 1)[0].strip()


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text.strip()

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()

    meta: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] = []

    for raw in parts[1].strip().splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - "):
            if current_key:
                current_list.append(strip_comment(line[4:].strip()))
            continue
        if current_key is not None:
            meta[current_key] = current_list
            current_key = None
            current_list = []
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = strip_comment(value.strip())
        if not value:
            current_key = key.strip()
        elif value.startswith("[") and value.endswith("]"):
            meta[key.strip()] = [
                item.strip().strip("\"'")
                for item in value[1:-1].split(",")
                if item.strip()
            ]
        else:
            meta[key.strip()] = value.strip("\"'")

    if current_key is not None:
        meta[current_key] = current_list

    return meta, parts[2].strip()


def dump_frontmatter(meta: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                lines.extend(f"  - {item}" for item in value)
            else:
                lines.append(f"{key}: []")
        else:
            lines.append(f"{key}: {value}")
    lines.extend(["---", "", body.strip()])
    return "\n".join(lines) + "\n"


def listify(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        value = strip_comment(value.strip())
        if value.startswith("[") and value.endswith("]"):
            return [
                item.strip().strip("\"'") for item in value[1:-1].split(",") if item
            ]
        return [value] if value else []
    return [str(value)]


def csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# --- artifacts ---


def normalize_id(value: str, prefix: str) -> str:
    value = value.strip()
    return value if value.startswith(prefix) else f"{prefix}{value}"


def task_id(value: str) -> str:
    return normalize_id(value, TASK_PREFIX)


def req_id(value: str) -> str:
    return normalize_id(value, REQ_PREFIX)


def epic_id(value: str) -> str:
    return normalize_id(value, EPIC_PREFIX)


def slug(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    if not result:
        fail("name must contain at least one alphanumeric character")
    return result


def split_name(value: str) -> tuple[list[str], str]:
    parts = [slug(part) for part in value.strip("/").split("/") if part.strip()]
    if not parts:
        fail("name is required")
    return parts[:-1], parts[-1]


def title_from_body(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("#"):
            return line.lstrip("# ").strip() or "Untitled"
    return "Untitled"


def load(path: Path) -> Artifact:
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    return Artifact(path=path, meta=meta, body=body, id=meta.get("id", path.stem))


def paths(base: Path, subdir: str, pattern: str) -> list[Path]:
    folder = base / subdir
    return sorted(folder.rglob(pattern)) if folder.exists() else []


def artifacts(base: Path, kind: str) -> list[Artifact]:
    if kind == "task":
        return [load(path) for path in paths(base, TASKS_DIR, "TASK-*.md")]
    if kind == "req":
        return [load(path) for path in paths(base, REQS_DIR, "REQ-*.md")]
    if kind == "epic":
        return [load(path) for path in paths(base, EPICS_DIR, "EPIC-*.md")]
    fail(f"unknown artifact kind: {kind}")


def find(base: Path, item_id: str) -> Artifact | None:
    candidates = [
        task_id(item_id),
        req_id(item_id),
        epic_id(item_id),
        item_id,
    ]
    for kind in ("task", "req", "epic"):
        for item in artifacts(base, kind):
            if item["id"] in candidates or item["path"].stem in candidates:
                return item
    return None


def status_of(item: Artifact) -> str:
    status = item["meta"].get("status", TODO)
    return IN_PROGRESS if status == LEGACY_IN_PROGRESS else str(status)


def save(item: Artifact) -> None:
    item["path"].write_text(
        dump_frontmatter(item["meta"], item["body"]),
        encoding="utf-8",
    )


# --- state helpers ---


def init_dirs() -> Path:
    base = spec_dir()
    for name in (TASKS_DIR, REQS_DIR, EPICS_DIR, MEMORY_DIR):
        (base / name).mkdir(parents=True, exist_ok=True)
    progress = base / PROGRESS_FILE
    if not progress.exists():
        progress.write_text(f"{now_log()} INIT .spec/\n", encoding="utf-8")
    return base


def log(action: str, target: str) -> None:
    base = spec_dir()
    base.mkdir(parents=True, exist_ok=True)
    progress = base / PROGRESS_FILE
    old = progress.read_text(encoding="utf-8").splitlines() if progress.exists() else []
    progress.write_text("\n".join([*old, f"{now_log()} {action} {target}"]) + "\n")


def session_path() -> Path:
    return spec_dir() / SESSION_FILE


def read_session() -> dict[str, str]:
    path = session_path()
    if not path.exists():
        return {}
    session: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        session[key.strip()] = value.strip()
    return session


def write_session(session: dict[str, str]) -> None:
    lines = ["# Session state - auto-managed by specctl"]
    lines.extend(f"{key}: {value}" for key, value in session.items())
    session_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


def clear_session() -> None:
    path = session_path()
    if path.exists():
        path.unlink()


def git(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def head() -> str:
    return git(["git", "rev-parse", "--short", "HEAD"])


def handoff() -> dict[str, Any]:
    session = read_session()
    base = session.get("base_commit", "")
    ready_ids = [item["id"] for item in ready_tasks(require_spec())[:5]]
    return {
        "task": session.get("task", ""),
        "step": session.get("step", ""),
        "base_commit": base,
        "diff_stat": git(["git", "diff", "--stat", base]) if base else "",
        "git_status": git(["git", "status", "--short"]),
        "ready": ready_ids,
    }


def print_handoff(data: dict[str, Any]) -> None:
    print("--- SESSION HANDOFF ---")
    if data["task"]:
        print(f"Task: {data['task']} (step: {data['step']})")
    else:
        print("Task: none")
    if data["diff_stat"]:
        print(f"Changes since base:\n{data['diff_stat']}")
    elif data["git_status"]:
        print(f"Uncommitted changes:\n{data['git_status']}")
    else:
        print("Changes: none")
    print(f"Next ready: {', '.join(data['ready']) if data['ready'] else 'none'}")
    if data["task"]:
        print(f"Resume: spec-flow work {data['task']}")
    print("---")


# --- readiness and validation ---


def ready_tasks(base: Path, epic: str | None = None) -> list[Artifact]:
    tasks = artifacts(base, "task")
    done = {item["id"] for item in tasks if status_of(item) == DONE}
    ready: list[Artifact] = []
    for item in tasks:
        meta = item["meta"]
        if epic and meta.get("epic") != epic_id(epic):
            continue
        if status_of(item) != TODO:
            continue
        if all(dep in done for dep in listify(meta.get("blocked-by"))):
            ready.append(item)
    return sorted(
        ready, key=lambda item: PRIORITY.get(item["meta"].get("priority", "normal"), 1)
    )


def blocked_tasks(
    base: Path, epic: str | None = None
) -> list[tuple[Artifact, list[str]]]:
    tasks = artifacts(base, "task")
    done = {item["id"] for item in tasks if status_of(item) == DONE}
    blocked: list[tuple[Artifact, list[str]]] = []
    for item in tasks:
        if epic and item["meta"].get("epic") != epic_id(epic):
            continue
        if status_of(item) != TODO:
            continue
        missing = [
            dep for dep in listify(item["meta"].get("blocked-by")) if dep not in done
        ]
        if missing:
            blocked.append((item, missing))
    return blocked


def section(body: str, name: str) -> str:
    lines = body.splitlines()
    capture = False
    found: list[str] = []
    wanted = f"## {name}".lower()
    for line in lines:
        if line.lower().strip() == wanted:
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture:
            found.append(line)
    return "\n".join(found).strip()


def is_placeholder(line: str) -> bool:
    line = line.lower().strip(" -[]0123456789.`")
    return line in PLACEHOLDERS or line.startswith("describe ")


def has_real_text(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return any(len(line) > 12 and not is_placeholder(line) for line in lines)


def creates_cycle(base: Path, item_id: str, dep_id: str) -> bool:
    task_by_id = {item["id"]: item for item in artifacts(base, "task")}

    def reaches(current: str, seen: set[str]) -> bool:
        if current == item_id:
            return True
        if current in seen:
            return False
        seen.add(current)
        item = task_by_id.get(current)
        if not item:
            return False
        return any(
            reaches(dep, seen) for dep in listify(item["meta"].get("blocked-by"))
        )

    return dep_id == item_id or reaches(dep_id, set())


def validate() -> list[str]:
    base = require_spec()
    issues: list[str] = []
    tasks = artifacts(base, "task")
    reqs = artifacts(base, "req")
    epics = artifacts(base, "epic")

    for label, items in (("task", tasks), ("req", reqs), ("epic", epics)):
        seen: dict[str, Path] = {}
        for item in items:
            item_id = item["id"]
            if item_id in seen:
                issues.append(
                    f"duplicate {label} id {item_id}: "
                    f"{rel(seen[item_id])} and {rel(item['path'])}"
                )
            seen[item_id] = item["path"]

    task_ids = {item["id"] for item in tasks}
    req_ids = {item["id"] for item in reqs}

    for item in tasks:
        meta = item["meta"]
        item_id = item["id"]
        if status_of(item) not in TASK_STATES:
            issues.append(f"{item_id}: invalid status '{meta.get('status')}'")
        if meta.get("status") == LEGACY_IN_PROGRESS:
            issues.append(
                f"{item_id}: use status '{IN_PROGRESS}', not '{LEGACY_IN_PROGRESS}'"
            )
        if not has_real_text(section(item["body"], "Description")):
            issues.append(f"{item_id}: missing meaningful Description")
        if not has_real_text(section(item["body"], "Acceptance")):
            issues.append(f"{item_id}: missing meaningful Acceptance")
        if not has_real_text(section(item["body"], "Files")):
            issues.append(f"{item_id}: missing meaningful Files")
        for dep in listify(meta.get("blocked-by")):
            if dep not in task_ids:
                issues.append(f"{item_id}: blocked-by references missing task '{dep}'")
        for req in listify(meta.get("implements")):
            if req not in req_ids:
                issues.append(
                    f"{item_id}: implements references missing requirement '{req}'"
                )

    for req in reqs:
        if not has_real_text(section(req["body"], "Success criteria")):
            issues.append(f"{req['id']}: missing meaningful Success criteria")

    for epic in epics:
        refs = listify(epic["meta"].get("tasks"))
        if not refs:
            issues.append(f"{epic['id']}: no tasks listed")
        for ref in refs:
            if ref not in task_ids:
                issues.append(f"{epic['id']}: references missing task '{ref}'")

    task_by_id = {item["id"]: item for item in tasks}

    def cyclic(item_id: str, visited: set[str], stack: set[str]) -> bool:
        if item_id in stack:
            return True
        if item_id in visited:
            return False
        visited.add(item_id)
        stack.add(item_id)
        item = task_by_id.get(item_id)
        if item:
            for dep in listify(item["meta"].get("blocked-by")):
                if cyclic(dep, visited, stack):
                    return True
        stack.remove(item_id)
        return False

    if any(cyclic(item["id"], set(), set()) for item in tasks):
        issues.append("dependency cycle detected")
    return issues


# --- commands ---


def cmd_init(_args: argparse.Namespace) -> None:
    existed = spec_dir().exists()
    base = init_dirs()
    print(
        f".spec/ already exists at {base}" if existed else f"✓ Created .spec/ at {base}"
    )


def task_template(item_id: str, title: str) -> str:
    return f"""---
id: {item_id}
status: todo
priority: normal
blocked-by: []
---

# {title}

## Description

TBD

## Acceptance

- [ ] TBD

## Files

- TBD

## Out of scope

- TBD
"""


def req_template(item_id: str, title: str) -> str:
    return f"""---
id: {item_id}
version: 1
priority: normal
---

# {title}

## Problem

TBD

## Success criteria

- [ ] TBD

## Out of scope

- TBD
"""


def cmd_new(args: argparse.Namespace) -> None:
    base = init_dirs()
    folders, name = split_name(args.name)
    title = name.replace("-", " ").replace("_", " ").title()
    if args.kind == "task":
        item_id = task_id(name)
        target = base / TASKS_DIR / Path(*folders) / f"{item_id}.md"
        content = task_template(item_id, title)
    else:
        item_id = req_id(name)
        target = base / REQS_DIR / Path(*folders) / f"{item_id}.md"
        content = req_template(item_id, title)
    if find(base, item_id) or target.exists():
        fail(f"artifact already exists: {item_id}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    log("NEW", item_id)
    ok(f"Created {rel(target)}")


def cmd_status(args: argparse.Namespace) -> None:
    base = require_spec()
    if args.id:
        item = find(base, args.id)
        if not item:
            fail(f"Not found: {args.id}")
        meta = item["meta"]
        print(f"ID: {item['id']}")
        print(f"Path: {rel(item['path'])}")
        if str(item["id"]).startswith(TASK_PREFIX):
            print(f"Status: {status_of(item)}")
            print(f"Priority: {meta.get('priority', 'normal')}")
            print(f"Blocked by: {', '.join(listify(meta.get('blocked-by'))) or 'none'}")
        return

    tasks = artifacts(base, "task")
    counts = {
        state: sum(1 for item in tasks if status_of(item) == state)
        for state in TASK_STATES
    }
    ready = ready_tasks(base)
    session = read_session()
    if args.json:
        print(
            json.dumps(
                {
                    "total": len(tasks),
                    "todo": counts[TODO],
                    "in_progress": counts[IN_PROGRESS],
                    "done": counts[DONE],
                    "ready": [item["id"] for item in ready[:5]],
                    "session": session,
                }
            )
        )
        return
    print("SPEC STATUS")
    print(f"Tasks: {counts[DONE]}/{len(tasks)} done, {counts[IN_PROGRESS]} in progress")
    if session:
        print(f"Active session: {session.get('task')} ({session.get('step')})")
    if ready:
        print("Ready:")
        for item in ready[:5]:
            print(f"  • {item['id']}")
    else:
        print("Ready: none")


def cmd_show(args: argparse.Namespace) -> None:
    item = find(require_spec(), args.id)
    if not item:
        fail(f"Not found: {args.id}")
    print(item["path"].read_text(encoding="utf-8"))


def cmd_ready(args: argparse.Namespace) -> None:
    base = require_spec()
    ready = ready_tasks(base, args.epic)
    if args.json:
        print(
            json.dumps(
                [
                    {"id": item["id"], "title": title_from_body(item["body"])}
                    for item in ready
                ]
            )
        )
        return
    if ready:
        for item in ready:
            print(f"{item['id']}  {title_from_body(item['body'])}")
        return
    print("No tasks ready to start.")
    for item, deps in blocked_tasks(base, args.epic):
        print(f"  blocked: {item['id']} waiting for {', '.join(deps)}")


def cmd_start(args: argparse.Namespace) -> None:
    base = require_spec()
    item = find(base, task_id(args.id))
    if not item or not str(item["id"]).startswith(TASK_PREFIX):
        fail(f"Task not found: {task_id(args.id)}")
    if status_of(item) == DONE:
        fail(f"Task {item['id']} is already done")
    session = read_session()
    active = session.get("task")
    if active and active != item["id"] and not args.force:
        fail(f"Session exists for {active}. Run 'specctl session handoff' first.")
    item["meta"]["status"] = IN_PROGRESS
    save(item)
    write_session(
        {
            "task": item["id"],
            "step": "planning",
            "started": now_iso(),
            "base_commit": head(),
        }
    )
    log("START", item["id"])
    ok(f"Started {item['id']}")


def cmd_done(args: argparse.Namespace) -> None:
    base = require_spec()
    item = find(base, task_id(args.id))
    if not item or not str(item["id"]).startswith(TASK_PREFIX):
        fail(f"Task not found: {task_id(args.id)}")
    session = read_session()
    active = session.get("task")
    if active and active != item["id"] and not args.force:
        fail(f"Active session is for {active}, not {item['id']}")
    missing = [
        flag
        for flag, value in (("--summary", args.summary), ("--tests", args.tests))
        if not value
    ]
    if missing and not args.force:
        fail(f"Missing completion evidence: {', '.join(missing)}")
    item["meta"].update({"status": DONE, "done-at": now_iso()})
    for key, value in {
        "done-summary": args.summary,
        "done-tests": args.tests,
        "done-files": csv(args.files),
        "done-commits": csv(args.commits),
    }.items():
        if value:
            item["meta"][key] = value
    save(item)
    if active == item["id"]:
        clear_session()
    log("DONE", item["id"])
    ok(f"Completed {item['id']}")


def cmd_checkpoint(args: argparse.Namespace) -> None:
    require_spec()
    session = read_session()
    target = session.get("task", "session") if session else "session"
    if args.message:
        target = f"{target}: {args.message}"
    log("CHECKPOINT", target)
    data = handoff()
    print(json.dumps(data) if args.json else "", end="")
    if not args.json:
        print_handoff(data)


def print_session(data: dict[str, str]) -> None:
    if not data:
        print("No active session")
        return
    print("Active Session:")
    print(f"  Task: {data.get('task', 'unknown')}")
    print(f"  Step: {data.get('step', 'unknown')}")
    if data.get("base_commit"):
        print(f"  Base commit: {data['base_commit']}")


def cmd_session(args: argparse.Namespace) -> None:
    require_spec()
    if args.action == "show":
        data = read_session()
        if args.json:
            print(json.dumps(data))
        else:
            print_session(data)
    elif args.action == "clear":
        data = read_session()
        clear_session()
        print(
            f"Cleared session for {data.get('task')}" if data else "No active session"
        )
    elif args.action == "handoff":
        data = handoff()
        print(json.dumps(data) if args.json else "", end="")
        if not args.json:
            print_handoff(data)
    elif args.action == "resume":
        data = read_session()
        if args.json:
            print(json.dumps(data))
        elif data:
            print_session(data)
            print(f"Resume: spec-flow work {data.get('task')}")
        else:
            print("No session to resume")
    elif args.action == "step":
        data = read_session()
        if not data:
            fail("No active session")
        data["step"] = args.step
        write_session(data)
        ok(f"Session step: {args.step}")


def cmd_validate(_args: argparse.Namespace) -> None:
    issues = validate()
    if issues:
        print("Validation issues found:")
        for issue in issues:
            print(f"  • {issue}")
        sys.exit(1)
    ok("No issues found")


def cmd_reset(args: argparse.Namespace) -> None:
    item = find(require_spec(), task_id(args.id))
    if not item:
        fail(f"Task not found: {task_id(args.id)}")
    item["meta"] = {
        key: value for key, value in item["meta"].items() if not key.startswith("done-")
    }
    item["meta"]["status"] = TODO
    save(item)
    if read_session().get("task") == item["id"]:
        clear_session()
    log("RESET", item["id"])
    ok(f"Reset {item['id']} to todo")


def cmd_dep(args: argparse.Namespace) -> None:
    base = require_spec()
    item = find(base, task_id(args.task))
    if not item:
        fail(f"Task not found: {task_id(args.task)}")
    dep = task_id(getattr(args, "dep", "")) if getattr(args, "dep", "") else ""
    if args.action == "list":
        blockers = listify(item["meta"].get("blocked-by"))
        discovered = listify(item["meta"].get("discovered-from"))
        print(json.dumps({"blocked-by": blockers, "discovered-from": discovered}))
        return
    if not find(base, dep):
        fail(f"Dependency not found: {dep}")
    key = "discovered-from" if args.type == "discovered-from" else "blocked-by"
    values = listify(item["meta"].get(key))
    if args.action == "add" and dep not in values:
        if key == "blocked-by" and creates_cycle(base, item["id"], dep):
            fail(f"Cannot add dependency: {item['id']} -> {dep} creates a cycle")
        values.append(dep)
    if args.action == "rm" and dep in values:
        values.remove(dep)
    item["meta"][key] = values
    save(item)
    ok(f"Updated {item['id']} {key}")


# --- parser ---


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="specctl - lightweight spec-flow state CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    new = sub.add_parser("new")
    new.add_argument("kind", choices=["task", "req"])
    new.add_argument("name")

    status = sub.add_parser("status")
    status.add_argument("id", nargs="?")
    status.add_argument("--json", action="store_true")

    show = sub.add_parser("show")
    show.add_argument("id")

    ready = sub.add_parser("ready")
    ready.add_argument("--epic")
    ready.add_argument("--json", action="store_true")

    start = sub.add_parser("start")
    start.add_argument("id")
    start.add_argument("--force", action="store_true")

    done = sub.add_parser("done")
    done.add_argument("id")
    done.add_argument("--summary")
    done.add_argument("--tests")
    done.add_argument("--files")
    done.add_argument("--commits")
    done.add_argument("--force", action="store_true")

    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--message")
    checkpoint.add_argument("--json", action="store_true")

    session = sub.add_parser("session")
    session_sub = session.add_subparsers(dest="action", required=True)
    for name in ("show", "handoff", "resume"):
        cmd = session_sub.add_parser(name)
        cmd.add_argument("--json", action="store_true")
    session_sub.add_parser("clear")
    step = session_sub.add_parser("step")
    step.add_argument("step", choices=sorted(SESSION_STEPS))

    sub.add_parser("validate")

    reset = sub.add_parser("reset")
    reset.add_argument("id")

    dep = sub.add_parser("dep")
    dep_sub = dep.add_subparsers(dest="action", required=True)
    add = dep_sub.add_parser("add")
    add.add_argument("task")
    add.add_argument("dep")
    add.add_argument("--type", choices=["blocks", "discovered-from"], default="blocks")
    rm = dep_sub.add_parser("rm")
    rm.add_argument("task")
    rm.add_argument("dep")
    rm.add_argument("--type", choices=["blocks", "discovered-from"], default="blocks")
    listing = dep_sub.add_parser("list")
    listing.add_argument("task")

    return p


def main() -> None:
    args = parser().parse_args()
    commands = {
        "init": cmd_init,
        "new": cmd_new,
        "status": cmd_status,
        "show": cmd_show,
        "ready": cmd_ready,
        "start": cmd_start,
        "done": cmd_done,
        "checkpoint": cmd_checkpoint,
        "session": cmd_session,
        "validate": cmd_validate,
        "reset": cmd_reset,
        "dep": cmd_dep,
    }
    commands[args.cmd](args)


if __name__ == "__main__":
    main()
