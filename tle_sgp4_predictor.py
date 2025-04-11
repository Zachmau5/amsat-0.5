import datetime
from sgp4.earth_gravity import wgs84
from sgp4.io import twoline2rv

def propagate_satellite(tle_line1, tle_line2, start_time, timestep_us, num_samples):
    satellite = twoline2rv(tle_line1, tle_line2, wgs84)
    positions = []

    for i in range(num_samples):
        seconds = start_time.second + start_time.microsecond / 1e6
        pos, _ = satellite.propagate(
            start_time.year, start_time.month, start_time.day,
            start_time.hour, start_time.minute, seconds
        )
        positions.append((start_time, pos))
        start_time += datetime.timedelta(microseconds=timestep_us)

    return positions
