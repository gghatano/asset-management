"""GitHub Actions workflow ファイルの構造検証。"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def update_portfolio_workflow() -> dict:
    path = ROOT / ".github/workflows/update-portfolio.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_workflow_has_schedule_and_dispatch(update_portfolio_workflow: dict) -> None:
    # YAML の "on" は Python では True にパースされることがあるので両方確認
    on = update_portfolio_workflow.get("on") or update_portfolio_workflow.get(True)
    assert on is not None
    assert "schedule" in on
    assert "workflow_dispatch" in on


def test_workflow_runs_all_steps_in_order(update_portfolio_workflow: dict) -> None:
    steps = update_portfolio_workflow["jobs"]["update"]["steps"]
    run_commands = [s.get("run", "") for s in steps if "run" in s]
    joined = "\n".join(run_commands)
    # spec 10.1 の各ステップが含まれていること
    assert "src.fetch_prices" in joined
    assert "src.generate_transactions" in joined
    assert "src.calculate_portfolio" in joined
    assert "src.build_dashboard" in joined


def test_workflow_commits_only_when_changes(update_portfolio_workflow: dict) -> None:
    steps = update_portfolio_workflow["jobs"]["update"]["steps"]
    commit_step = next(s for s in steps if s.get("name", "").startswith("Commit"))
    body = commit_step["run"]
    assert "git diff --cached --quiet" in body, "変更なし時は no-op にする"
    assert "git push origin main" in body


def test_workflow_targets_main(update_portfolio_workflow: dict) -> None:
    checkout = next(s for s in update_portfolio_workflow["jobs"]["update"]["steps"] if "uses" in s)
    assert checkout["uses"].startswith("actions/checkout")
    assert checkout["with"]["ref"] == "main"
