from sgp4.api import Satrec, jday
from datetime import datetime, timedelta

def propagate_ecef_from_tle(tle_lines, start_time, num_samples=90, step_secs=60):
    sat = Satrec.twoline2rv(tle_lines[0], tle_lines[1])
    positions = []

    for i in range(num_samples):
        timestamp = start_time + timedelta(seconds=i * step_secs)
        jd, fr = jday(timestamp.year, timestamp.month, timestamp.day,
                      timestamp.hour, timestamp.minute, timestamp.second + timestamp.microsecond / 1e6)
        e, r, v = sat.sgp4(jd, fr)
        if e == 0:
            positions.append((timestamp, tuple(r)))  # r = (x, y, z) in km
        else:
            positions.append((timestamp, None))  # propagation error
    return positions
