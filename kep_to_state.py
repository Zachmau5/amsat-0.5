import numpy as np
from datetime import datetime
import constants as c

from tle_to_kep import ConvertTLEToKepElem
from TimeRoutines import Nth_day_to_date, JdayInternal, CalculateGMSTFromJD
from coordinate_conversions import (
    ConvertKeplerToECI,
    ConvertECIToECEF,
    ComputeGeodeticLon,
    ComputeGeodeticLat2
)


def ConvertKepToStateVectors(tle_dict):
    """
    Converts a TLE dictionary into satellite lat/lon prediction tracks over time.

    Returns:
        latslons_dict: Dictionary mapping satellite name to Nx2 array of [lon_deg, lat_deg]
    """
    # Use current UTC time as both the start and end time input
    utc_now = datetime.utcnow()
    utc_start_time = utc_now.strftime('%Y %m %d %H %M %S')
    utc_end_time = utc_start_time

    # Convert TLEs to orbital elements
    kep_elem_dict, _, epoch_year = ConvertTLEToKepElem(tle_dict, utc_start_time, utc_end_time)

    # Get a representative epoch_days from the first satellite in the dict
    any_key = next(iter(kep_elem_dict))
    epoch_days = kep_elem_dict[any_key][:, 8][0]

    # Build a time vector from epoch_days forward 10 minutes
    delta_days = (10 * 60) / (24.0 * 3600.0)  # 10 minutes in fractional days
    start_day = epoch_days
    end_day = start_day + delta_days
    time_vec = np.linspace(start_day, end_day, num=c.num_time_pts)

    # Get UTC time array in Y M D H M S
    time_array = Nth_day_to_date(epoch_year, time_vec)

    # Compute Julian date and GMST
    jday = JdayInternal(time_array)
    gmst = CalculateGMSTFromJD(jday, time_vec)

    latslons_dict = {}
    print(f"[DEBUG] Satellites received: {list(kep_elem_dict.keys())}")
    print(f"[DEBUG] Time vector range: {time_vec[0]:.5f} to {time_vec[-1]:.5f} ({len(time_vec)} steps)")

    for key in kep_elem_dict:
        values = kep_elem_dict[key]

        a = values[:, 0]  # semi-major axis
        e = values[:, 1]  # eccentricity
        i = values[:, 2]  # inclination
        Omega = values[:, 3]  # RA of ascending node
        w = values[:, 4]  # argument of perigee
        nu = values[:, 5]  # true anomaly
        epoch_days = values[:, 8]  # epoch (in days) per sat

        # Time difference from TLE epoch to prediction times
        delta_time_vec = time_vec - epoch_days

        # ECI position/velocity
        X_eci, Y_eci, Z_eci, Xdot_eci, Ydot_eci, Zdot_eci = ConvertKeplerToECI(
            a, e, i, Omega, w, nu, delta_time_vec
        )

        # Convert to ECEF
        X_ecef, Y_ecef, Z_ecef = ConvertECIToECEF(X_eci, Y_eci, Z_eci, gmst)

        # Compute geodetic coordinates
        lons = ComputeGeodeticLon(X_ecef, Y_ecef)
        lats = ComputeGeodeticLat2(X_ecef, Y_ecef, Z_ecef, a, e)

        # Convert radians to degrees
        lons *= c.rad2deg
        lats *= c.rad2deg

        # Store in array
        n_rows = len(lats)
        results = np.zeros((n_rows, 2), dtype=float)
        results[:, 0] = lons
        results[:, 1] = lats
        print(f"[{key}] Track shape: {results.shape}")
        print(f"[{key}] Lon range: {np.min(lons):.2f}° to {np.max(lons):.2f}°")
        print(f"[{key}] Lat range: {np.min(lats):.2f}° to {np.max(lats):.2f}°")

        latslons_dict[key] = results

    return latslons_dict
