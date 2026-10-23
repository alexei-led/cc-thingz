"""Test execution evidence must not confuse no tests with a pass."""

from __future__ import annotations

import importlib.util
import json

import pytest
from conftest import REPO_ROOT

spec = importlib.util.spec_from_file_location(
    "test_report", REPO_ROOT / "src/hooks/test-runner/parse-report.py"
)
assert spec and spec.loader
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


@pytest.mark.parametrize(
    ("kind", "text", "expected"),
    [
        (
            "go-json",
            "\n".join(
                json.dumps(item)
                for item in [
                    {"Action": "pass", "Package": "demo", "Test": "TestWorks"},
                    {"Action": "pass", "Package": "demo"},
                ]
            ),
            (1, 0),
        ),
        ("go-json", '{"Action":"skip","Package":"demo"}', (0, 0)),
        (
            "go-json",
            '{"Action":"skip","Package":"demo","Test":"TestSkipped"}',
            (0, 0),
        ),
        ("js-json", '{"numPassedTests":0,"numFailedTests":0}', (0, 0)),
        ("js-json", '{"numPassedTests":2,"numFailedTests":1}', (3, 1)),
        ("bun-junit", "<testsuites><testsuite/></testsuites>", (0, 0)),
        (
            "bun-junit",
            "<testsuite><testcase><skipped/></testcase></testsuite>",
            (0, 0),
        ),
        (
            "bun-junit",
            "<testsuite><testcase/><testcase><failure>bad</failure>"
            "</testcase></testsuite>",
            (2, 1),
        ),
    ],
)
def test_execution_counts(kind, text, expected):
    executed, failed, _ = report.parse_report(kind, text)
    assert (executed, failed) == expected


@pytest.mark.parametrize(
    ("kind", "text"),
    [
        ("go-json", "not a report"),
        ("js-json", "null"),
        ("js-json", '{"numPassedTests":true,"numFailedTests":0}'),
        ("js-json", '{"numPassedTests":1,"numFailedTests":-1}'),
        ("js-json", "{}"),
        ("bun-junit", "not xml"),
    ],
)
def test_invalid_reports_do_not_count_as_passes(kind, text):
    with pytest.raises((ValueError, TypeError, report.ET.ParseError)):
        report.parse_report(kind, text)
