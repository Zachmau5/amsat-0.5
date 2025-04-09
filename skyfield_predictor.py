 
from skyfield.api import load
from datetime import datetime, timedelta

def load_satellite_from_tle(tle_file_path, sat_name="ISS (ZARYA)"):
    ts = load.timescale()
    with open(tle_file_path, 'r') as f:
        lines = f.readlines()
    sats = load.tle_file(tle_file_path)
    sats_by_name = {sat.name: sat for sat in sats}
    return ts, sats_by_name[sat_name]

def get_groundtrack(satellite, ts, duration_minutes=90, steps=1000):
    now = datetime.utcnow()
    times = ts.utc(now.year, now.month, now.day, now.hour, now.minute,
                   range(steps))
    lats = []
    lons = []

    for t in times:
        geocentric = satellite.at(t)
        subpoint = geocentric.subpoint()
        lats.append(subpoint.latitude.degrees)
        lons.append(subpoint.longitude.degrees)

    import numpy as np
    return np.column_stack((lons, lats))
