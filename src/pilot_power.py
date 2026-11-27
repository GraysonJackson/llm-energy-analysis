"""Bracket a local pilot workload with a continuously sampled wall-power trace."""

import csv
import math
import time
from datetime import datetime, timezone
from threading import Event, Thread


def integrate(samples, start, end, max_gap, min_interior=2):
    """Integrate inside the measured window, with interpolation only between valid samples."""
    inside = sum(start < stamp < end and watts is not None for stamp, watts in samples)
    if not samples or start < samples[0][0] or end > samples[-1][0] or end <= start:
        return None, 'missing boundary coverage'
    if inside < min_interior:
        return None, 'too few samples inside the window'

    joules = 0.0
    for (left, w_left), (right, w_right) in zip(samples, samples[1:]):
        lo, hi = max(start, left), min(end, right)
        if hi <= lo:
            continue
        if w_left is None or w_right is None or right - left > max_gap:
            return None, 'missing reading or sample gap exceeds the pilot limit'
        slope = (w_right - w_left) / (right - left)
        first = w_left + slope * (lo - left)
        last = w_left + slope * (hi - left)
        joules += (first + last) / 2 * (hi - lo)
    return joules, None


def record_window(monitor, path, action):
    """Save raw attempts while action runs, then summarize the bracketed interval."""
    interval = monitor.polling_interval
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError('shelly.polling_interval must be positive and finite')

    stopped = Event()
    samples = []
    worker_errors = []
    with path.open('x', newline='', encoding='utf-8') as output:
        writer = csv.writer(output)
        writer.writerow(['request_start_utc', 'request_end_utc', 'request_start_elapsed_sec',
                         'request_end_elapsed_sec', 'power_w', 'status'])
        origin = time.monotonic()

        def sample():
            utc_start = datetime.now(timezone.utc).isoformat()
            before = time.monotonic() - origin
            watts = monitor.get_current_power()
            after = time.monotonic() - origin
            utc_end = datetime.now(timezone.utc).isoformat()
            samples.append(((before + after) / 2, watts))
            writer.writerow([utc_start, utc_end, before, after, watts,
                             'ok' if watts is not None else 'unavailable'])
            output.flush()
            return before

        def collect(first):
            last_start = first
            try:
                while not stopped.wait(max(0, origin + last_start + interval - time.monotonic())):
                    last_start = sample()
            except Exception as exc:
                worker_errors.append(exc)

        first = sample()
        if samples[-1][1] is None:
            raise RuntimeError('No initial Shelly reading. The workload was not started.')
        worker = Thread(target=collect, args=(first,), daemon=True)
        worker.start()
        start = time.monotonic() - origin
        try:
            result = action(origin)
        finally:
            end = time.monotonic() - origin
            stopped.set()
            worker.join()
            sample()

    if worker_errors:
        raise RuntimeError('Power trace writer stopped during the run') from worker_errors[0]
    max_gap = 2.5 * interval
    energy, reason = integrate(samples, start, end, max_gap)
    segment_watts = []
    if energy is not None and end - start >= 30:
        part = (end - start) / 3
        for i in range(3):
            segment_energy, _ = integrate(samples, start + i * part, start + (i + 1) * part, max_gap)
            segment_watts.append(None if segment_energy is None else segment_energy / part)
    return result, {
        'started_elapsed_sec': start,
        'ended_elapsed_sec': end,
        'duration_sec': end - start,
        'attempted_samples': len(samples),
        'max_allowed_gap_sec': max_gap,
        'gross_joules': energy,
        'mean_watts': None if energy is None else energy / (end - start),
        'third_means_watts': segment_watts,
        'energy_unavailable_reason': reason,
        'trace_file': path.name,
    }
