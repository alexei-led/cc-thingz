"""Keep validation and publication independent of shared Actions caches."""

from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT

CACHE_INPUTS = {
    "actions/setup-go": ("cache", False),
    "actions/setup-node": ("package-manager-cache", False),
    "astral-sh/setup-uv": ("enable-cache", False),
    "oven-sh/setup-bun": ("no-cache", True),
}


@pytest.mark.parametrize(
    "workflow_path", sorted((REPO_ROOT / ".github/workflows").glob("*.yml"))
)
def test_workflows_do_not_use_shared_actions_caches(workflow_path: Path) -> None:
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    for job_name, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            action = step.get("uses", "").split("@", 1)[0]
            location = f"{workflow_path.name}:{job_name}:{action}"
            assert not action.startswith("actions/cache"), location
            inputs = step.get("with", {})
            if action in CACHE_INPUTS:
                name, disabled = CACHE_INPUTS[action]
                assert inputs.get(name) is disabled, location
            if action in {"actions/setup-node", "actions/setup-python"}:
                assert not inputs.get("cache"), location
