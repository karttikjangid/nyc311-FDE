"""Controlled failures, applied to the loaded snapshot in memory only (raw files are never touched)."""
import pandas as pd

CHAOS = ["missing_column", "duplicate_order", "conflicting_duplicate", "stale_data", "unmapped_notes"]


def apply(name, frames, manifest):
    sr = frames["service_requests"]
    if name == "missing_column":
        frames["service_requests"] = sr.drop(columns=["status"])
    elif name == "duplicate_order":
        frames["service_requests"] = pd.concat([sr, sr.head(100)], ignore_index=True)
    elif name == "conflicting_duplicate":
        clone = sr.head(1).copy()
        clone["status"] = "Open" if clone["status"].iloc[0] != "Open" else "Closed"
        frames["service_requests"] = pd.concat([sr, clone], ignore_index=True)
    elif name == "stale_data":
        manifest["as_of_utc"] = (pd.Timestamp(manifest["as_of_utc"]) - pd.Timedelta(days=30)).isoformat()
    elif name == "unmapped_notes":
        hpd = sr["agency"].eq("HPD")
        idx = sr[hpd].sample(frac=0.5, random_state=0).index
        sr = sr.copy()
        sr.loc[idx, "resolution_description"] = sr.loc[idx, "resolution_description"] + " [new wording]"
        frames["service_requests"] = sr
    else:
        raise ValueError(f"unknown chaos scenario {name}; choose from {CHAOS}")
    return frames, manifest
