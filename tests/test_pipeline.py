"""End-to-end: one-command run, idempotent rerun, and chaos scenarios on a tiny snapshot."""
import filecmp
import json
from pathlib import Path

import run_pipeline


def run(cfg_path, *extra):
    return run_pipeline.run(run_pipeline.parse_args(["--run-date", "2026-09-26", "--config", str(cfg_path), *extra]))


def outputs(tmp):
    return tmp / "output" / "run_date=2026-09-26"


def test_run_publishes_and_rerun_is_identical(workspace):
    tmp, cfg = workspace
    assert run(cfg) == 0
    first = outputs(tmp)
    copy = tmp / "first_copy"
    import shutil
    shutil.copytree(first, copy)
    assert run(cfg) == 0
    cmp = filecmp.dircmp(copy, first)
    assert not cmp.diff_files and not cmp.left_only and not cmp.right_only
    report = json.loads((first / "validation_report.json").read_text())
    rules = {r["id"]: r for r in report["rules"]}
    assert rules["R09"]["value"] == 1                      # only the real ordering error, not the date-only one
    assert rules["R10"]["live"] == "FAIL" and rules["R10"]["reporting"] in ("WARN", "FAIL")
    assert report["gate"]["live_answer_gate"] == "NOT READY"


def test_missing_column_blocks_and_keeps_previous_output(workspace):
    tmp, cfg = workspace
    assert run(cfg) == 0
    before = (outputs(tmp) / "metrics.json").read_text()
    assert run(cfg, "--chaos", "missing_column") == 2
    assert (outputs(tmp) / "metrics.json").read_text() == before
    failed = json.loads((tmp / "logs" / "failed_run_2026-09-26_missing_column.json").read_text())
    assert "R03" in failed["gate"]["blocking_failures"]


def test_stale_snapshot_blocks(workspace):
    tmp, cfg = workspace
    assert run(cfg, "--chaos", "stale_data") == 2
    assert not outputs(tmp).exists()


def test_conflicting_duplicate_blocks_exact_duplicate_warns(workspace):
    tmp, cfg = workspace
    assert run(cfg, "--chaos", "conflicting_duplicate") == 2
    assert run(cfg, "--chaos", "duplicate_order") == 0
    rules = {r["id"]: r for r in json.loads((outputs(tmp) / "validation_report.json").read_text())["rules"]}
    assert rules["R05"]["reporting"] == "WARN"


def test_unmapped_notes_become_unknown_not_dropped(workspace):
    tmp, cfg = workspace
    assert run(cfg, "--chaos", "unmapped_notes") == 2      # coverage falls below the blocking threshold
    failed = json.loads((tmp / "logs" / "failed_run_2026-09-26_unmapped_notes.json").read_text())
    assert "R17" in failed["gate"]["blocking_failures"]
