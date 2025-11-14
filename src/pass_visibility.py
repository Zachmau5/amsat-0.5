#!/usr/bin/env python3
"""
pass_visibility.py

Precompute elevation-based visibility passes for all satellites in a TLE file.

This is for PLANNING / METADATA only:
  - "Which sats have a pass in the next N minutes?"
  - "When does the pass start/peak/end?"

It does NOT replace the live 600 ms pointing loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from skyfield.api import load, wgs84, EarthSatellite

# Use a local timescale; no dependency on skyfield_predictor here
_ts = load.timescale()


@dataclass
class PassInterval:
    """One continuous interval with elevation above min_el_deg."""
    start: datetime
    peak: datetime
    end: datetime
    max_el_deg: float


@dataclass
class SatPassSummary:
    """All passes for a single satellite over the lookahead window."""
    name: str
    passes: List[PassInterval]

    @property
    def has_pass(self) -> bool:
        return bool(self.passes)

    @property
    def next_pass(self) -> Optional[PassInterval]:
        return self.passes[0] if self.passes else None


def _read_tle_file(tle_path: str) -> List[Tuple[str, str, str]]:
    """
    Read a 3-line-per-satellite TLE file and return a list of:
        (name, line1, line2)
    """
    with open(tle_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    sats: List[Tuple[str, str, str]] = []
    i = 0
    while i <= len(lines) - 3:
        name = lines[i]
        l1 = lines[i + 1]
        l2 = lines[i + 2]

        if l1.startswith("1 ") and l2.startswith("2 "):
            sats.append((name, l1, l2))
            i += 3
        else:
            i += 1

    return sats


def _compute_passes_for_sat(
    sat: EarthSatellite,
    my_lat: float,
    my_lon: float,
    start_dt: datetime,
    end_dt: datetime,
    dt_sec: float,
    min_el_deg: float,
) -> List[PassInterval]:
    """
    Scan from start_dt to end_dt in steps of dt_sec and find intervals
    where elevation >= min_el_deg for this EarthSatellite.
    """
    # Ensure timezone-aware UTC
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)

    qth = wgs84.latlon(my_lat, my_lon, elevation_m=0.0)

    passes: List[PassInterval] = []
    in_pass = False
    pass_start: Optional[datetime] = None
    pass_peak: Optional[datetime] = None
    pass_peak_el: float = -999.0

    t = start_dt
    step = timedelta(seconds=dt_sec)

    while t <= end_dt:
        t_sf = _ts.from_datetime(t)
        alt, az, _rng = (sat - qth).at(t_sf).altaz()
        el_deg = alt.degrees

        if el_deg >= min_el_deg:
            if not in_pass:
                in_pass = True
                pass_start = t
                pass_peak = t
                pass_peak_el = el_deg
            else:
                if el_deg > pass_peak_el:
                    pass_peak_el = el_deg
                    pass_peak = t
        else:
            if in_pass and pass_start is not None and pass_peak is not None:
                passes.append(
                    PassInterval(
                        start=pass_start,
                        peak=pass_peak,
                        end=t,
                        max_el_deg=pass_peak_el,
                    )
                )
            in_pass = False
            pass_start = None
            pass_peak = None
            pass_peak_el = -999.0

        t += step

    # Edge case: still in pass at end of window
    if in_pass and pass_start is not None and pass_peak is not None:
        passes.append(
            PassInterval(
                start=pass_start,
                peak=pass_peak,
                end=end_dt,
                max_el_deg=pass_peak_el,
            )
        )

    return passes


def compute_pass_visibility_for_file(
    tle_path: str,
    my_lat: float,
    my_lon: float,
    window_minutes: float = 30.0,
    min_el_deg: float = 20.0,
    dt_sec: float = 20.0,
    look_back_minutes: float = 5.0,   # NEW: how far into the past we scan
) -> Dict[str, SatPassSummary]:
    """
    For all satellites in the TLE file at `tle_path`, compute visibility
    passes above `min_el_deg` elevation over a window that starts a bit
    before 'now' and extends into the future.

    Only passes whose PEAK time is >= now are kept, so passes that have
    already gone overhead and are descending do NOT count.
    """
    now = datetime.now(timezone.utc)

    # Look slightly into the past so we see full passes and their true peaks
    start_dt = now - timedelta(minutes=look_back_minutes)
    end_dt = now + timedelta(minutes=window_minutes)

    tle_blocks = _read_tle_file(tle_path)
    summaries: Dict[str, SatPassSummary] = {}

    for name, l1, l2 in tle_blocks:
        sat = EarthSatellite(l1, l2, name, _ts)

        # Compute all passes in the extended window
        all_passes = _compute_passes_for_sat(
            sat=sat,
            my_lat=my_lat,
            my_lon=my_lon,
            start_dt=start_dt,
            end_dt=end_dt,
            dt_sec=dt_sec,
            min_el_deg=min_el_deg,
        )

        # Keep only passes whose PEAK is in the future (or right now)
        future_passes = [p for p in all_passes if p.peak >= now]

        summaries[name] = SatPassSummary(
            name=name,
            passes=future_passes,
        )

    return summaries



