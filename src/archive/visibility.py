# visibility.py
from datetime import datetime, timedelta, timezone
from skyfield.api import load, wgs84, EarthSatellite

# cache ephemeris/timescale so repeated calls are cheap
_TS = None
_EPH = None
def _get_ts_eph():
    global _TS, _EPH
    if _TS is None:
        _TS = load.timescale()
    if _EPH is None:
        _EPH = load("de421.bsp")   # small kernel; auto-cached by Skyfield
    return _TS, _EPH

def _sun_alt_degrees(topos, eph, t):
    """Return Sun altitude (degrees) at the observer for time t (scalar or array)."""
    alt, _, _ = (eph['sun'] - topos).at(t).altaz()
    return alt.degrees

def has_visible_pass_next_hour(name, l1, l2, lat, lon, elev_m=0.0,
                               window_min=60, step_s=30, min_el=10.0) -> bool:
    """
    True if any instant in the next `window_min` minutes satisfies:
      - satellite elevation ≥ min_el
      - observer Sun altitude < -6°
      - satellite is sunlit (not in Earth's shadow)
    """
    ts, eph = _get_ts_eph()
    topos = wgs84.latlon(lat, lon, elevation_m=elev_m)
    sat = EarthSatellite(l1, l2, name, ts)

    now = datetime.now(timezone.utc)
    t0 = ts.from_datetime(now)
    t1 = ts.from_datetime(now + timedelta(minutes=window_min))

    # build time grid
    n = int((window_min * 60) / step_s) + 1
    tg = ts.linspace(t0, t1, n)

    # satellite elevation at observer
    alt = (sat - topos).at(tg).altaz()[0].degrees
    # sun altitude at observer
    sun_alt_obs = _sun_alt_degrees(topos, eph, tg)
    # true illumination (Earth-shadow) test
    is_lit = sat.at(tg).is_sunlit(eph)

    ok = (alt >= min_el) & (sun_alt_obs < -6.0) & is_lit
    return bool(ok.any())

def visible_flags_for_tle(tle_dict, lat, lon, elev_m=0.0, window_min=60, step_s=30, min_el=10.0):
    """Batch: {sat_name: True/False} for all entries in tle_dict = {name: (L1,L2)}."""
    flags = {}
    for name, (l1, l2) in tle_dict.items():
        try:
            flags[name] = has_visible_pass_next_hour(name, l1, l2, lat, lon, elev_m,
                                                     window_min, step_s, min_el)
        except Exception:
            flags[name] = False
    return flags
