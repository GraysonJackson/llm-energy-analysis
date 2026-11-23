"""Capture a Shelly trace for workstation idle with no model loaded."""

import argparse
import csv
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from power_monitor import PowerMonitor


ROOT = Path(__file__).resolve().parent.parent


def capture_trace(monitor, duration, path):
    """Save each read attempt immediately, including reads without usable watts."""
    fields = ["request_start_utc", "request_end_utc", "request_start_elapsed_sec",
              "request_end_elapsed_sec", "power_w", "status"]
    valid_reads = 0
    with path.open("x", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(fields)
        output.flush()
        origin = time.monotonic()
        end = origin + duration
        next_poll = origin
        while True:
            time.sleep(max(0, min(next_poll, end) - time.monotonic()))
            start_utc = datetime.now(timezone.utc)
            started = time.monotonic()
            watts = monitor.get_current_power()
            finished = time.monotonic()
            end_utc = datetime.now(timezone.utc)
            writer.writerow([start_utc.isoformat(), end_utc.isoformat(), started - origin,
                             finished - origin, watts, "ok" if watts is not None else "unavailable"])
            output.flush()
            if watts is not None:
                valid_reads += 1
            if started >= end:
                return valid_reads
            next_poll = max(started + monitor.polling_interval, finished)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=120, help="Capture duration in seconds (default: 120)")
    args = parser.parse_args()
    if args.seconds < 60:
        parser.error("--seconds must be at least 60 for the idle protocol")

    with (ROOT / "config.yaml").open(encoding="utf-8") as source:
        config = yaml.safe_load(source)
    try:
        monitor = PowerMonitor.from_config(config.get("shelly", {}))
    except ValueError as exc:
        parser.error(str(exc))
    if not math.isfinite(monitor.polling_interval) or monitor.polling_interval <= 0:
        parser.error("shelly.polling_interval must be positive and finite")

    destination = ROOT / "runs" / "baselines"
    destination.mkdir(parents=True, exist_ok=True)
    filename = datetime.now(timezone.utc).strftime("no_model_idle_%Y%m%dT%H%M%S_%fZ.csv")
    path = destination / filename
    print(f"Recording workstation idle. Raw trace: {path}", flush=True)
    try:
        count = capture_trace(monitor, args.seconds, path)
    except KeyboardInterrupt:
        print(f"Interrupted. Partial trace retained at {path}")
        return 130
    print(f"Saved raw trace with {count} usable watts readings. Review gaps and idle stability before use.")
    return 0 if count >= 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
