import numpy as np
from tle_to_kep import ConvertTLEToKepElem
from TimeRoutines import Nth_day_to_date, JdayInternal, CalculateGMSTFromJD
from coordinate_conversions import ConvertKeplerToECI, ConvertECIToECEF, ComputeGeodeticLon, ComputeGeodeticLat2
from datetime import datetime
import constants as c


def ConvertKepToStateVectors(tle_dict):
    """
    Converts TLE dictionary (parsed by ParseTwoLineElementFile) into
    satellite latitude and longitude positions for visualization.

    Returns:
        latslons_dict: dict where each key is a satellite name, and value is
                       a Nx2 numpy array of [lon_deg, lat_deg] positions.
    """
    # Use current UTC time as start/end
    utc_now = datetime.utcnow()
    utc_start_time = utc_now.strftime('%Y %m %d %H %M %S')
    utc_end_time = utc_start_time

    # Convert TLE data to keplerian elements
    kep_elem_dict, time_vec, epoch_year = ConvertTLEToKepElem(tle_dict, utc_start_time, utc_end_time)

    # Get start/end days based on epoch + 10 minutes
    delta_days = (10 * 60) / (24.0 * 3600.0)  # 10 minutes in days
    start_day = epoch_days
    end_day = start_day + delta_days
    time_vec = np.linspace(start_day, end_day, num=c.num_time_pts)

    time_array = Nth_day_to_date(epoch_year, time_vec)

    # Get Julian Date and Greenwich Mean Sidereal Time
    jday = JdayInternal(time_array)
    gmst = CalculateGMSTFromJD(jday, time_vec)

    latslons_dict = {}

    for key in kep_elem_dict:
        values = kep_elem_dict[key]

        a = values[:, 0]  # semi-major axis
        e = values[:, 1]  # eccentricity
        i = values[:, 2]  # inclination
        Omega = values[:, 3]  # RA of ascending node
        w = values[:, 4]  # argument of perigee
        nu = values[:, 5]  # true anomaly
        epoch_days = values[:, 8]  # days from epoch

        # Compute time difference from epoch
        delta_time_vec = time_vec - epoch_days

        # Convert to ECI
        X_eci, Y_eci, Z_eci, Xdot_eci, Ydot_eci, Zdot_eci = ConvertKeplerToECI(
            a, e, i, Omega, w, nu, delta_time_vec
        )

        # Convert to ECEF
        X_ecef, Y_ecef, Z_ecef = ConvertECIToECEF(X_eci, Y_eci, Z_eci, gmst)
        print(f"[DEBUG] X_ecef: {X_ecef[:3]}")
        print(f"[DEBUG] Y_ecef: {Y_ecef[:3]}")
        print(f"[DEBUG] Z_ecef: {Z_ecef[:3]}")
        print(f"[DEBUG] a: {a[:3]}")
        print(f"[DEBUG] e: {e[:3]}")

        # Convert ECEF to geodetic lat/lon (in radians)
        lons = ComputeGeodeticLon(X_ecef, Y_ecef)
        lats = ComputeGeodeticLat2(X_ecef, Y_ecef, Z_ecef, a, e)

        # Convert to degrees
        lats *= c.rad2deg
        lons *= c.rad2deg

        # Build result array [lon, lat]
        n_rows = len(lats)
        results = np.zeros((n_rows, 2), dtype=float)
        results[:, 0] = lons
        results[:, 1] = lats
        latslons_dict[key] = results

    return latslons_dict
