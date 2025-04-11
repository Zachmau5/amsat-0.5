# import numpy as np
# from datetime import datetime, timedelta
#
# import constants as c
#
# from tle_to_kep import ConvertTLEToKepElem
# from TimeRoutines import Nth_day_to_date, JdayInternal, CalculateGMSTFromJD
# from coordinate_conversions import (
#     ConvertKeplerToECI,
#     ConvertECIToECEF,
#     ComputeGeodeticLon,
#     ComputeGeodeticLat2
# )
#
#
# def ConvertKepToStateVectors(tle_dict):
#     """
#     Converts a TLE dictionary into satellite lat/lon prediction tracks over time.
#
#     Returns:
#         latslons_dict: Dictionary mapping satellite name to Nx2 array of [lon_deg, lat_deg]
#     """
#     # Use current UTC time as both the start and end time input
#
#     utc_now = datetime.utcnow()
#     utc_start_time = utc_now.strftime('%Y %m %d %H %M %S')
#     utc_future = utc_now + timedelta(minutes=90)
#     utc_end_time = utc_future.strftime('%Y %m %d %H %M %S')
#
#     # Convert TLEs to orbital elements
#     kep_elem_dict, _, epoch_year = ConvertTLEToKepElem(tle_dict, utc_start_time, utc_end_time)
#
#     # Get a representative epoch_days from the first satellite in the dict
#     any_key = next(iter(kep_elem_dict))
#     epoch_days = kep_elem_dict[any_key][:, 8][0]
#
#     # Build a time vector from epoch_days forward 10 minutes
#     # Build a time vector from current UTC time forward 90 minutes
#     now = datetime.utcnow()
#     now_array = np.array([[now.year, now.month, now.day, now.hour, now.minute, now.second]])
#     now_jday = JdayInternal(now_array)[0]
#
#     delta_days = (90 * 60) / (24.0 * 3600.0)  # 90 minutes
#     start_day = now_jday - (int(epoch_year) * 1000)
#     end_day = start_day + delta_days
#     time_vec = np.linspace(start_day, end_day, num=c.num_time_pts)
#
#
#     # Get UTC time array in Y M D H M S
#     time_array = Nth_day_to_date(epoch_year, time_vec)
#
#     # Compute Julian date and GMST
#     jday = JdayInternal(time_array)
#     gmst = CalculateGMSTFromJD(jday, time_vec)
#
#     latslons_dict = {}
#     # print(f"[DEBUG] Satellites received: {list(kep_elem_dict.keys())}")
#     # print(f"[DEBUG] Time vector range: {time_vec[0]:.5f} to {time_vec[-1]:.5f} ({len(time_vec)} steps)")
#
#     for key in kep_elem_dict:
#         values = kep_elem_dict[key]
#
#         a = values[:, 0]  # semi-major axis
#         e = values[:, 1]  # eccentricity
#         i = values[:, 2]  # inclination
#         Omega = values[:, 3]  # RA of ascending node
#         w = values[:, 4]  # argument of perigee
#         nu = values[:, 5]  # true anomaly
#         epoch_days = values[:, 8]  # epoch (in days) per sat
#
#         # Time difference from TLE epoch to prediction times
#         delta_time_vec = time_vec - epoch_days
#
#         # ECI position/velocity
#         X_eci, Y_eci, Z_eci, Xdot_eci, Ydot_eci, Zdot_eci = ConvertKeplerToECI(
#             a, e, i, Omega, w, nu, delta_time_vec
#         )
#
#         # Convert to ECEF
#         X_ecef, Y_ecef, Z_ecef = ConvertECIToECEF(X_eci, Y_eci, Z_eci, gmst)
#
#         # Compute geodetic coordinates
#         lons = ComputeGeodeticLon(X_ecef, Y_ecef)
#         lats = ComputeGeodeticLat2(X_ecef, Y_ecef, Z_ecef, a, e)
#
#         # Convert radians to degrees
#         lons *= c.rad2deg
#         lats *= c.rad2deg
#
#         # Store in array
#         n_rows = len(lats)
#         results = np.zeros((n_rows, 2), dtype=float)
#         results[:, 0] = lons
#         results[:, 1] = lats
#         # print(f"[{key}] Track shape: {results.shape}")
#         # print(f"[{key}] Lon range: {np.min(lons):.2f}° to {np.max(lons):.2f}°")
#         # print(f"[{key}] Lat range: {np.min(lats):.2f}° to {np.max(lats):.2f}°")
#         # print(f"[{key}] Inclination (deg): {i[0] * 180/np.pi:.2f}")
#
#         # Pull the final predicted point (most recent)
#         cur_lon = results[-1, 0]
#         cur_lat = results[-1, 1]
#
#         # Estimate "altitude" from semi-major axis (minus Earth's radius)
#         alt_km = a[0] / 1000.0 - c.Re / 1000.0  # Convert m to km
#         speed_kms = np.linalg.norm([Xdot_eci[-1], Ydot_eci[-1], Zdot_eci[-1]]) / 1000.0  # m/s to km/s
#
#         # Simulated N2YO-style printout
#         print("\n--- N2YO Comparison Style ---")
#         print(f"Satellite:     {key}")
#         print(f"UTC Time:      {utc_now.strftime('%H:%M:%S')}")
#         print(f"LATITUDE:      {cur_lat:.2f}°")
#         print(f"LONGITUDE:     {cur_lon:.2f}°")
#         print(f"ALTITUDE [km]: {alt_km:.2f}")
#         print(f"SPEED [km/s]:  {speed_kms:.2f}")
#         print(f"INCLINATION:   {i[0] * 180 / np.pi:.2f}°")
#         print(f"-----------------------------\n")
#
#         latslons_dict[key] = results
#
#     return latslons_dict



import numpy as np
from datetime import datetime, timedelta

import constants as c
from skyfield_predictor import load_satellite_from_tle, get_groundtrack
from tle_to_kep import ConvertTLEToKepElem
from TimeRoutines import Nth_day_to_date, JdayInternal, CalculateGMSTFromJD
from coordinate_conversions import (
    ConvertKeplerToECI,
    ConvertECIToECEF,
    ComputeGeodeticLon,
    ComputeGeodeticLat2
)


def ConvertKepToStateVectors(tle_dict, use_skyfield=False):
    """
    Converts TLE dictionary into satellite lat/lon predictions.
    If use_skyfield=True, uses Skyfield instead of custom orbital math.
    """
    if use_skyfield:
        latslons_dict = {}
        for sat_name in tle_dict:
            try:
                ts, sat = load_satellite_from_tle("amateur.tle", sat_name)
                track = get_groundtrack(sat, ts)
                latslons_dict[sat.name] = track
            except Exception as e:
                print(f"[Skyfield ERROR] {sat_name}: {e}")
        return latslons_dict

    # === Fixed Live Mode Prediction ===
    utc_now = datetime.utcnow()
    utc_start_time = utc_now.strftime('%Y %m %d %H %M %S')
    utc_future = utc_now + timedelta(minutes=90)
    utc_end_time = utc_future.strftime('%Y %m %d %H %M %S')

    # Get elements from TLE (still needed)
    kep_elem_dict, _, epoch_year = ConvertTLEToKepElem(tle_dict, utc_start_time, utc_end_time)

    # Use current year for epoch
    epoch_year = utc_now.year
# this plots it to the rear
    # # Calculate fractional day-of-year from utc_now
    # day_of_year = utc_now.timetuple().tm_yday
    # fractional_day = (
    #     day_of_year +
    #     utc_now.hour / 24.0 +
    #     utc_now.minute / 1440.0 +
    #     utc_now.second / 86400.0
    # )
    #
    # # Prediction range: now → now + 90 minutes
    # delta_days = (90 * 60) / (24.0 * 3600.0)  # 90 minutes in days
    # start_day = fractional_day
    # end_day = start_day + delta_days
    # time_vec = np.linspace(start_day, end_day, num=c.num_time_pts)
    #
    # # Convert fractional day to full UTC format array
    # time_array = Nth_day_to_date(epoch_year, time_vec)
    #
    # # GMST for ECI → ECEF conversion
    # jday = JdayInternal(time_array)
    # gmst = CalculateGMSTFromJD(jday, time_vec)
    #
    # latslons_dict = {}
    # Calculate fractional day-of-year from utc_now
    utc_now = datetime.utcnow()
    year = utc_now.year
    day_of_year = utc_now.timetuple().tm_yday
    fractional_day = (
        day_of_year +
        utc_now.hour / 24.0 +
        utc_now.minute / 1440.0 +
        utc_now.second / 86400.0
    )

    # Prediction range: now → now + 90 minutes
    delta_days = (90 * 60) / (24.0 * 3600.0)  # 90 minutes in days
    start_day = fractional_day
    end_day = start_day + delta_days
    time_vec = np.linspace(start_day, end_day, num=c.num_time_pts)

    # Convert fractional day-of-year to full UTC array (Y M D H M S)
    time_array = Nth_day_to_date(year, time_vec)

    # GMST for ECI → ECEF conversion
    jday = JdayInternal(time_array)
    gmst = CalculateGMSTFromJD(jday, time_vec)

    latslons_dict = {}
    epoch_days = kep_elem_dict["ISS (ZARYA)"][0, 8]
    print(f"TLE Epoch Day of Year: {epoch_days:.5f}")
    print(f"Current fractional day: {fractional_day:.5f}")

    for key in kep_elem_dict:
        values = kep_elem_dict[key]
        a = values[:, 0]
        e = values[:, 1]
        i = values[:, 2]
        Omega = values[:, 3]
        w = values[:, 4]
        nu = values[:, 5]
        # epoch_days = values[:, 8]

        delta_time_vec = time_vec - epoch_days
        X_eci, Y_eci, Z_eci, Xdot_eci, Ydot_eci, Zdot_eci = ConvertKeplerToECI(
            a, e, i, Omega, w, nu, delta_time_vec)

        X_ecef, Y_ecef, Z_ecef = ConvertECIToECEF(X_eci, Y_eci, Z_eci, gmst)
        lons = ComputeGeodeticLon(X_ecef, Y_ecef) * c.rad2deg
        lats = ComputeGeodeticLat2(X_ecef, Y_ecef, Z_ecef, a, e) * c.rad2deg

        results = np.column_stack((lons, lats))

        # Altitude from semi-major axis
        alt_km = a[0] / 1000.0 - c.Re / 1000.0
        speed_kms = np.linalg.norm([Xdot_eci[-1], Ydot_eci[-1], Zdot_eci[-1]]) / 1000.0

        print("\n--- N2YO Comparison Style ---")
        print(f"Satellite:     {key}")
        print(f"UTC Time:      {utc_now.strftime('%H:%M:%S')}")
        print(f"LATITUDE:      {results[-1, 1]:.2f}°")
        print(f"LONGITUDE:     {results[-1, 0]:.2f}°")
        print(f"ALTITUDE [km]: {alt_km:.2f}")
        print(f"SPEED [km/s]:  {speed_kms:.2f}")
        print(f"INCLINATION:   {i[0] * c.rad2deg:.2f}°")
        print(f"-----------------------------\n")

        latslons_dict[key] = results
    # Print TLE epoch



    return latslons_dict
