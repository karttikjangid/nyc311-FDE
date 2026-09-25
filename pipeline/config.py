"""Configuration lives in config/pipeline.json, not in code."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "pipeline.json"


def load_config(path=CONFIG_PATH):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    cfg["_root"] = str(ROOT)
    return cfg


def path(cfg, key):
    """Resolve a configured path relative to the project root."""
    return Path(cfg["_root"]) / cfg["paths"][key]
