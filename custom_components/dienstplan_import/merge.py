"""
Pure-Python ICS merge logic for the Dienstplan Import integration.

No Home Assistant imports here on purpose: this module runs in a worker thread
(via hass.async_add_executor_job), so everything must be ordinary synchronous
Python. `merge_ics_file()` is the single entry point.
"""

import os
import shutil
import hashlib
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

from icalendar import Calendar


def _as_date(value):
    """Return a `date` for either a `date` or a `datetime` (datetime is a subclass)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _event_bounds(component):
    """Start and (exclusive) end date of a VEVENT, as `date` objects."""
    start = _as_date(component.decoded("dtstart"))
    if component.get("dtend") is not None:
        end = _as_date(component.decoded("dtend"))
    elif component.get("duration") is not None:
        end = _as_date(start + component.decoded("duration"))
    else:
        end = start + timedelta(days=1)
    return start, end


def _ensure_meta(component):
    """Guarantee every event has a UID and DTSTAMP (safety net)."""
    if not component.get("uid"):
        try:
            base = component.decoded("dtstart").isoformat() + str(component.get("summary", ""))
        except Exception:
            base = str(component.get("summary", "")) + datetime.now().isoformat()
        component.add("uid", hashlib.md5(base.encode("utf-8")).hexdigest() + "@dienstplan-import")
    if not component.get("dtstamp"):
        component.add("dtstamp", datetime.now(timezone.utc))


def _rotate_backups(backup_dir, max_backups):
    backups = sorted(Path(backup_dir).glob("local_calendar.*.ics"))
    for old in backups[:-max_backups]:
        try:
            old.unlink()
        except OSError:
            pass


def merge_ics_file(ics_content, cal_file, backup_dir, max_backups=30):
    """
    Merge `ics_content` into the local_calendar file `cal_file`.

    Strategy "replace the covered range, keep the rest":
      1. Determine the new file's date range = [min(DTSTART) .. max(DTEND)).
      2. Drop existing events whose start falls inside that range.
      3. Keep existing events outside the range (history/archive).
      4. Add all events from the new file.

    Returns a summary dict. Raises ValueError on invalid input.
    """
    new_cal = Calendar.from_ical(ics_content)
    new_events = [c for c in new_cal.walk("VEVENT")]
    if not new_events:
        raise ValueError("The uploaded ICS file contains no events (VEVENT).")

    starts, ends = [], []
    for ev in new_events:
        s, e = _event_bounds(ev)
        starts.append(s)
        ends.append(e)
        _ensure_meta(ev)
    range_start = min(starts)        # inclusive
    range_end = max(ends)            # exclusive

    cal_path = Path(cal_file)
    if cal_path.exists():
        existing_cal = Calendar.from_ical(cal_path.read_bytes())
    else:
        existing_cal = Calendar()
        existing_cal.add("prodid", "-//Dienstplan Import//HA//EN")
        existing_cal.add("version", "2.0")

    out = Calendar()
    for key, value in existing_cal.items():
        out.add(key, value)
    if not out.get("version"):
        out.add("version", "2.0")
    if not out.get("prodid"):
        out.add("prodid", "-//Dienstplan Import//HA//EN")

    for comp in existing_cal.subcomponents:
        if comp.name != "VEVENT":
            out.add_component(comp)

    kept = 0
    removed = 0
    for ev in existing_cal.walk("VEVENT"):
        ev_start, _ = _event_bounds(ev)
        if ev_start is None or ev_start < range_start or ev_start >= range_end:
            out.add_component(ev)
            kept += 1
        else:
            removed += 1

    for ev in new_events:
        out.add_component(ev)

    os.makedirs(backup_dir, exist_ok=True)
    if cal_path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(cal_path, Path(backup_dir) / f"local_calendar.{stamp}.ics")
        _rotate_backups(backup_dir, max_backups)

    tmp_path = cal_path.with_suffix(cal_path.suffix + ".tmp")
    tmp_path.write_bytes(out.to_ical())
    os.replace(tmp_path, cal_path)

    return {
        "added": len(new_events),
        "kept": kept,
        "removed": removed,
        "range_start": range_start.isoformat(),
        "range_end": (range_end - timedelta(days=1)).isoformat(),
    }
