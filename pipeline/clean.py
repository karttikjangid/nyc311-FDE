"""CLEAN: type the raw strings and add flags. Nothing is overwritten or silently fixed.

- Original string columns are kept as they came.
- Parsed timestamps go in new *_ts columns (naive, assumed America/New_York; see config).
- Only exact duplicate rows are removed (same key, every field identical). Conflicting duplicates are kept
  and reported, because choosing between them needs an owner.
"""
import hashlib
from zoneinfo import ZoneInfo

import pandas as pd

DATE_COLS = ["created_date", "closed_date", "due_date", "resolution_action_updated_date"]
MOJIBAKE = r"Ã|â€|â\x80|Â°"


def note_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if isinstance(text, str) else None


def as_of_local(as_of_utc, tz_name):
    t = pd.Timestamp(as_of_utc)
    return t.tz_convert(ZoneInfo(tz_name)).tz_localize(None)


def clean_service_requests(raw, as_of_local_ts):
    df = raw.copy()
    report = {"rows_in": int(len(df))}
    exact_dup = df.duplicated(keep="first")
    report["exact_duplicate_rows_removed"] = int(exact_dup.sum())
    df = df[~exact_dup].copy()
    key_dup = df["unique_key"].duplicated(keep=False)
    report["conflicting_duplicate_keys"] = int(df.loc[key_dup, "unique_key"].nunique())

    for c in DATE_COLS:
        if c in df.columns:
            ts = pd.to_datetime(df[c], format="ISO8601", errors="coerce")
            report[f"{c}_unparseable"] = int((df[c].notna() & ts.isna()).sum())
            df[c.replace("_date", "") + "_ts"] = ts
        else:
            df[c.replace("_date", "") + "_ts"] = pd.NaT
    df = df.rename(columns={"resolution_action_updated_ts": "last_action_ts"})

    created, closed, last = df["created_ts"], df["closed_ts"], df["last_action_ts"]
    # A timestamp at exactly 00:00:00 on the creation date is date-only precision, not an impossible order.
    # Those rows are flagged separately (flag_*_date_only_same_day) instead of being called errors.
    def date_only_same_day(ts):
        return ts.notna() & (ts == ts.dt.normalize()) & (ts.dt.normalize() == created.dt.normalize())
    df["flag_closed_date_only_same_day"] = closed.notna() & (closed < created) & date_only_same_day(closed)
    df["flag_action_date_only_same_day"] = last.notna() & (last < created) & date_only_same_day(last)
    df["flag_closed_before_created"] = closed.notna() & (closed < created) & ~df["flag_closed_date_only_same_day"]
    df["flag_action_before_created"] = last.notna() & (last < created) & ~df["flag_action_date_only_same_day"]
    is_closed = df["status"].eq("Closed")
    df["flag_status_date_conflict"] = (is_closed & closed.isna()) | (~is_closed & closed.notna())
    df["flag_midnight_close"] = closed.notna() & (closed == closed.dt.normalize())
    df["flag_future_date"] = (created > as_of_local_ts) | (closed > as_of_local_ts) | (last > as_of_local_ts)
    note = df["resolution_description"]
    df["flag_note_missing"] = note.isna() | note.str.strip().isin(["", "N/A"])
    df["flag_note_mojibake"] = note.str.contains(MOJIBAKE, regex=True, na=False)
    ends_clean = note.str.rstrip().str[-1:].isin([".", ")", "!", "?", '"'])
    df["flag_note_truncated_500"] = note.str.len().eq(500) & ~ends_clean.fillna(False)
    df["note_hash"] = note.map(note_hash)
    report["rows_out"] = int(len(df))
    return df, report


def clean_call_center(raw):
    df = raw.copy()
    df["call_ts"] = pd.to_datetime(df["date_time"] if "date_time" in df else df["date"], format="ISO8601", errors="coerce")
    return df


def clean_survey(raw):
    df = raw.copy()
    df["year_i"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["month_i"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")
    return df
