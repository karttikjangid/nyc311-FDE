"""SAVE: publish a run-date partition atomically.

Files are written to output/.tmp_run_date=X, then swapped in with two renames. A failed run never
touches the existing partition. Re-running the same date replaces it with identical content.
"""
import json
import os
import shutil
from pathlib import Path


def dump_json(p, obj):
    Path(p).write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def publish(tmp_dir, final_dir):
    tmp_dir, final_dir = Path(tmp_dir), Path(final_dir)
    old = final_dir.with_name(final_dir.name + ".old")
    if old.exists():
        shutil.rmtree(old)
    if final_dir.exists():
        os.rename(final_dir, old)
    os.rename(tmp_dir, final_dir)
    if old.exists():
        shutil.rmtree(old)
