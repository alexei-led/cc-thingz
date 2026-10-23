#!/usr/bin/env python3
"""Read execution evidence from Go JSON, Jest/Vitest JSON, or Bun JUnit."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPORT_LIMIT_BYTES = 8 * 1024 * 1024


def parse_report(kind: str, text: str) -> tuple[int, int, str]:
    if kind == "go-json":
        executed = failed = 0
        completed = False
        output: list[str] = []
        for line in text.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                output.append(line + "\n")
                continue
            if not isinstance(event, dict):
                raise ValueError("invalid Go test event")
            action = event.get("Action")
            if action in {"pass", "fail", "skip"} and event.get("Package"):
                completed = True
            if (
                isinstance(event.get("Test"), str)
                and event["Test"]
                and action in {"pass", "fail"}
            ):
                executed += 1
                failed += action == "fail"
            if isinstance(event.get("Output"), str):
                output.append(event["Output"])
        if not completed:
            raise ValueError("Go report has no completed package")
        return executed, failed, "".join(output)
    if kind == "js-json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("invalid JS test report")
        passed, failed = data.get("numPassedTests"), data.get("numFailedTests")
        if any(type(value) is not int or value < 0 for value in (passed, failed)):
            raise ValueError("JS report lacks valid test execution counts")
        diagnostics: list[str] = []
        for suite in data.get("testResults", []):
            if not isinstance(suite, dict):
                continue
            if isinstance(suite.get("message"), str) and suite["message"]:
                diagnostics.append(suite["message"])
            for test in suite.get("assertionResults", []):
                if isinstance(test, dict):
                    diagnostics.extend(
                        message
                        for message in test.get("failureMessages", [])
                        if isinstance(message, str)
                    )
        return passed + failed, failed, "\n".join(diagnostics)
    if kind == "bun-junit":
        root = ET.fromstring(text)
        executed = failed = 0
        diagnostics = []
        for test in root.iter("testcase"):
            if test.find("skipped") is not None:
                continue
            executed += 1
            errors = [*test.findall("failure"), *test.findall("error")]
            failed += bool(errors)
            for error in errors:
                diagnostics.append(error.text or error.get("message", "Test failed"))
        return executed, failed, "\n".join(diagnostics)
    raise ValueError(f"unknown report kind: {kind}")


def main() -> int:
    try:
        kind, path = sys.argv[1:]
        if path:
            with Path(path).open("rb") as stream:
                raw = stream.read(REPORT_LIMIT_BYTES + 1)
        else:
            raw = sys.stdin.buffer.read(REPORT_LIMIT_BYTES + 1)
        if len(raw) > REPORT_LIMIT_BYTES:
            raise ValueError("test report exceeds 8 MiB")
        executed, failed, diagnostics = parse_report(kind, raw.decode())
    except Exception as error:
        print(f"Test report unavailable: {error}", file=sys.stderr)
        return 1
    print(executed, failed)
    if diagnostics:
        print(diagnostics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
