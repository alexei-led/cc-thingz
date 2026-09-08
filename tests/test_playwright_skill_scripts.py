from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT

SCRIPTS_SRC = REPO_ROOT / "src" / "skills" / "playwright-skill" / "scripts"

PLAYWRIGHT_STUB = r"""
const fs = require("fs");
const path = require("path");

function makeLocator() {
  const locator = {
    filter() { return locator; },
    first() { return locator; },
    async textContent() { return "Fake Title"; },
    async boundingBox() { return { x: 0, y: 0, width: 1, height: 1 }; }
  };
  return locator;
}

function makePage() {
  return {
    setDefaultTimeout() {},
    on() {},
    async goto() {},
    async waitForLoadState() {},
    async waitForSelector() {},
    async evaluate() {},
    locator() { return makeLocator(); },
    async title() { return "Document Title"; },
    async screenshot(options) {
      fs.mkdirSync(path.dirname(options.path), { recursive: true });
      fs.writeFileSync(options.path, "fake screenshot");
    }
  };
}

const browserType = {
  name: "chromium-stub",
  executablePath() { return process.execPath; },
  async launch() {
    return {
      async newContext() {
        return { async newPage() { return makePage(); } };
      },
      async close() {}
    };
  }
};

module.exports = {
  chromium: browserType,
  firefox: browserType,
  webkit: browserType,
  devices: {}
};
"""


def copy_scripts(tmp_path: Path) -> Path:
    scripts = tmp_path / "scripts"
    shutil.copytree(SCRIPTS_SRC, scripts)
    stub_dir = tmp_path / "node_modules" / "playwright"
    stub_dir.mkdir(parents=True)
    (stub_dir / "index.js").write_text(PLAYWRIGHT_STUB)
    return scripts


def run_node(scripts: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    if shutil.which("node") is None:
        pytest.skip("node is required for playwright-skill script tests")

    return subprocess.run(
        ["node", str(scripts / args[0]), *args[1:]],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )


def test_run_json_keeps_stdout_clean_and_preserves_cwd(tmp_path: Path) -> None:
    scripts = copy_scripts(tmp_path)

    result = run_node(
        scripts,
        "run.js",
        "--json",
        "const fs = require('fs'); "
        "console.log(JSON.stringify({ "
        "hasChromium: !!chromium, "
        "hasFs: !!fs.readFileSync, "
        "cwd: process.cwd() "
        "}))",
        cwd=tmp_path,
    )

    payload = json.loads(result.stdout)
    assert payload == {
        "hasChromium": True,
        "hasFs": True,
        "cwd": str(tmp_path),
    }
    assert result.stderr == ""
    assert not list(scripts.glob(".temp-execution-*.js"))


def test_run_file_can_explicitly_require_playwright(tmp_path: Path) -> None:
    scripts = copy_scripts(tmp_path)
    script = tmp_path / "check.js"
    script.write_text(
        'const { chromium } = require("playwright");\n'
        "console.log(JSON.stringify({ name: chromium.name, cwd: process.cwd() }));\n"
    )

    result = run_node(scripts, "run.js", "--json", str(script), cwd=tmp_path)

    payload = json.loads(result.stdout)
    assert payload == {"name": "chromium-stub", "cwd": str(tmp_path)}
    assert result.stderr == ""


def test_screenshot_url_writes_clean_json_and_manifest(tmp_path: Path) -> None:
    scripts = copy_scripts(tmp_path)
    screenshot = tmp_path / "shot.png"
    manifest = tmp_path / "manifest.json"

    result = run_node(
        scripts,
        "screenshot-url.js",
        "--url",
        "http://example.test",
        "--selector",
        "main",
        "--out",
        str(screenshot),
        "--manifest",
        str(manifest),
        "--json",
        cwd=tmp_path,
    )

    payload = json.loads(result.stdout)
    assert payload["title"] == "Fake Title"
    assert payload["screenshotPath"] == str(screenshot)
    assert payload["url"] == "http://example.test"
    assert screenshot.read_text() == "fake screenshot"
    assert json.loads(manifest.read_text()) == payload
    assert result.stderr == ""


def test_screenshot_sequence_writes_outputs_and_manifest(tmp_path: Path) -> None:
    scripts = copy_scripts(tmp_path)
    out_dir = tmp_path / "shots"

    result = run_node(
        scripts,
        "screenshot-sequence.js",
        "--url-template",
        "http://example.test/{n}",
        "--from",
        "1",
        "--to",
        "2",
        "--selector",
        "main",
        "--out-dir",
        str(out_dir),
        "--json",
        cwd=tmp_path,
    )

    payload = json.loads(result.stdout)
    assert [item["url"] for item in payload["results"]] == [
        "http://example.test/1",
        "http://example.test/2",
    ]
    assert (out_dir / "screenshot-01.png").read_text() == "fake screenshot"
    assert (out_dir / "screenshot-02.png").read_text() == "fake screenshot"
    assert json.loads((out_dir / "manifest.json").read_text()) == {
        key: value for key, value in payload.items() if key != "manifestPath"
    }
    assert result.stderr == ""


def test_screenshot_sequence_rejects_wrong_step_direction(tmp_path: Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node is required for playwright-skill script tests")

    scripts = copy_scripts(tmp_path)

    result = subprocess.run(
        [
            "node",
            str(scripts / "screenshot-sequence.js"),
            "--url-template",
            "http://example.test/{n}",
            "--from",
            "1",
            "--to",
            "3",
            "--step",
            "-1",
            "--json",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--step direction must move from --from toward --to" in result.stderr


def test_runtime_prefers_project_dependency_and_keeps_plugin_immutable(
    tmp_path: Path,
) -> None:
    scripts = copy_scripts(tmp_path)
    before = sorted(str(p.relative_to(scripts)) for p in scripts.rglob("*"))
    result = run_node(
        scripts,
        "run.js",
        "--json",
        "console.log(JSON.stringify({name: chromium.name}))",
        cwd=tmp_path,
    )
    assert json.loads(result.stdout)["name"] == "chromium-stub"
    assert sorted(str(p.relative_to(scripts)) for p in scripts.rglob("*")) == before


def test_runtime_installs_exact_package_only_in_user_cache(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    shutil.copytree(SCRIPTS_SRC, scripts)
    script = tmp_path / "check.js"
    cache = tmp_path / "cache"
    script.write_text(
        'const fs = require("fs"); const path = require("path");\n'
        f"const cache = {json.dumps(str(cache))};\n"
        "const calls = [];\n"
        'require("child_process").execFileSync = (command, args, options) => {\n'
        "calls.push({command,args,cwd:options.cwd});\n"
        'const moduleDir = path.join(cache,"node_modules/playwright");\n'
        "fs.mkdirSync(moduleDir,{recursive:true});\n"
        'fs.writeFileSync(path.join(moduleDir,"index.js"),"module.exports={marker:42}");\n'
        "};\n"
        f"const runtime = require({json.dumps(str(scripts / 'lib/runtime.js'))});\n"
        "const loaded = runtime.loadPlaywright({cacheDir:cache,quiet:true});\n"
        "console.log(JSON.stringify({calls,loaded}));\n"
    )
    result = subprocess.run(
        ["node", str(script)], cwd=tmp_path, capture_output=True, text=True, check=True
    )
    payload = json.loads(result.stdout)
    assert payload["loaded"] == {"marker": 42}
    assert payload["calls"][0]["command"] == "npm"
    assert "playwright@1.57.0" in payload["calls"][0]["args"]
    assert payload["calls"][0]["cwd"] == str(cache)
    assert not (scripts / "node_modules").exists()
    assert not (scripts / "package-lock.json").exists()


def test_missing_browser_reports_explicit_setup_without_install(tmp_path: Path) -> None:
    scripts = copy_scripts(tmp_path)
    stub = tmp_path / "node_modules/playwright/index.js"
    stub.write_text(
        PLAYWRIGHT_STUB.replace(
            "return process.execPath;", 'return "/missing/browser";'
        )
    )
    result = subprocess.run(
        [
            "node",
            str(scripts / "screenshot-url.js"),
            "--url",
            "http://example.test",
            "--json",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "package is ready but chromium is missing" in result.stderr
    assert "cli.js" in result.stderr
    assert "install chromium" in result.stderr
    assert not (scripts / "node_modules").exists()


@pytest.mark.parametrize(("opt_in", "sandbox"), [("0", True), ("1", False)])
def test_browser_sandbox_requires_explicit_opt_in(
    tmp_path: Path, opt_in: str, sandbox: bool
) -> None:
    scripts = copy_scripts(tmp_path)
    script = tmp_path / "check.js"
    script.write_text(
        f"process.env.PLAYWRIGHT_SKILL_NO_SANDBOX={json.dumps(opt_in)};\n"
        'require("playwright").chromium.launch=async (options)=>{'
        "console.log(JSON.stringify(options));return {};};\n"
        f"require({json.dumps(str(scripts / 'lib/helpers.js'))}).launchBrowser();\n"
    )
    result = subprocess.run(
        ["node", str(script)], cwd=tmp_path, capture_output=True, text=True, check=True
    )
    options = json.loads(result.stdout)
    assert options["chromiumSandbox"] is sandbox
    assert ("--no-sandbox" in options["args"]) is not sandbox
