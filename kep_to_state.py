"""
kep_to_state.py

Purpose:
    This module converts a dictionary of TLE data for one or more satellites
    into predicted ground tracks and state vectors (position and velocity)
    using a Keplerian propagation model. It uses custom orbital math (via the
    tle_to_kep module and coordinate conversion routines) to generate position
    predictions over a selected time range. The resulting data includes latitudes,
    longitudes, and altitudes, which can be used to plot satellite passes or for
    further analysis.

Modules and Functions Used:
    - constants: For physical constants, conversion factors, etc.
    - skyfield_predictor: Provides an alternative (Skyfield-based) approach.
      (Note: In this file, the Skyfield option is commented out by default.)
    - tle_to_kep (ConvertTLEToKepElem): Converts parsed TLE data into Keplerian
      elements (semi-major axis, eccentricity, inclination, RAAN, argument of perigee,
      true anomaly, etc.) over a time range.
    - TimeRoutines (Nth_day_to_date, JdayInternal, CalculateGMSTFromJD):
      Handles time conversion (fractional day, Julian Date, and GMST).
    - coordinate_conversions (ConvertKeplerToECI, ConvertECIToECEF, ComputeGeodeticLon,
      ComputeGeodeticLat2): Performs coordinate conversions:
         • From orbital elements (PQW) to Earth-Centered Inertial (ECI) using rotation matrices,
         • From ECI to Earth-Centered Earth-Fixed (ECEF) using Greenwich Mean Sidereal Time,
         • And from ECEF to geodetic coordinates (longitude, latitude) using Bowring’s method.

Usage:
    When this module is run, it generates predictions for the selected satellites
    based on their TLE data, computes their positions (lat, lon, altitude), and prints
    out a “N2YO comparison style” summary of each satellite's current status. It then
    returns a dictionary of latitude/longitude arrays (and altitude) for further use
    (for example, plotting in a map).

Overview of the Steps:
    1. Get the current UTC time and calculate a future time (usually +90 minutes)
       to form a prediction range.
    2. Convert the times into the necessary formats:
         • Strings formatted as "YYYY MM DD HH MM SS",
         • Fractional day-of-year for propagation,
         • Julian dates for GMST calculations.
    3. Call ConvertTLEToKepElem() from the tle_to_kep module to compute the evolving
       Keplerian orbital elements over that prediction time window.
    4. For each satellite:
         a. Extract orbital elements (semi-major axis 'a', eccentricity 'e',
            inclination 'i', RAAN, argument of perigee, true anomaly, epoch day).
         b. Compute the time offset vector (delta_time_vec) relative to the TLE epoch.
         c. Convert the updated Keplerian elements to ECI coordinates using ConvertKeplerToECI().
         d. Convert ECI to ECEF coordinates using the calculated GMST.
         e. Convert the ECEF coordinates to geodetic longitude and latitude.
         f. Compute the altitude from the semi-major axis and Earth's radius.
         g. Print a comparison summary (similar to the N2YO website data).
         h. Store the lat/lon arrays (and altitude) in a dictionary.
    5. Return the resulting dictionary of state vectors (latitudes, longitudes, altitudes)
       keyed by satellite name.

Author:
    [Your Name], [Your Affiliation or Lab Name]
    Date: [Your Date]

"""

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


def ConvertKepToStateVectors(tle_dict, use_skyfield=True):
    """
    Converts a TLE dictionary into predictions of satellite state vectors,
    including geodetic latitude, longitude, and altitude. Optionally, the
    Skyfield library can be used instead of custom Keplerian propagation,
    though by default the custom orbital math is used ("Fixed Live Mode").

    Parameters:
        tle_dict : dict
            Dictionary where each key is a satellite name and each value is an array
            of orbital elements parsed from its TLE. The array typically includes:
              [semi-major axis (a), eccentricity (e), inclination (i),
               RAAN (Omega), argument of perigee (w), true anomaly (nu),
               (eccentric anomaly, if computed), mean motion, epoch (fractional day)]
        use_skyfield : bool, optional
            If True, uses Skyfield-based propagation (code commented out by default).
            Otherwise, uses custom Keplerian math.

    Returns:
        latslons_dict : dict
            Dictionary keyed by satellite name. For each satellite, returns a dict
            containing:
                - 'lons': an array of longitudes (in degrees)
                - 'lats': an array of latitudes (in degrees)
                - 'alt_km': a scalar altitude (in kilometers), computed from semi-major axis

    Detailed Steps:
        1. Get the current UTC time ("utc_now") and define a prediction window
           of 90 minutes into the future. Convert these times to formatted strings.
        2. Call ConvertTLEToKepElem():
             - This function computes the evolving Keplerian elements over the prediction
               time range, including the semi-major axis, eccentricity, inclination,
               RAAN, argument of perigee, true anomaly, and epoch day.
        3. Reset the epoch year using the current year from utc_now.
        4. Compute the current fractional day-of-year from utc_now for propagation:
             fractional_day = day + (hour/24 + minute/1440 + second/86400)
        5. Define the prediction range (start_day to end_day) in fractional days
           corresponding to now and now+90 minutes. Generate a time vector ("time_vec")
           using np.linspace with a resolution set by c.num_time_pts.
        6. Convert the fractional day-of-year vector to a full UTC date array using Nth_day_to_date.
        7. Compute Julian Dates from the date array using JdayInternal and then GMST (in radians)
           from these Julian Dates using CalculateGMSTFromJD.
        8. For each satellite in the kep_elem_dict:
             a. Extract orbital elements: semi-major axis (a), eccentricity (e), inclination (i),
                RAAN (Omega), argument of perigee (w), true anomaly (nu), and epoch day.
             b. Compute the time offset vector ("delta_time_vec") as time_vec minus epoch_day.
             c. Call ConvertKeplerToECI() with the orbital elements and delta_time_vec:
                - This computes the satellite's position in the Earth-Centered Inertial (ECI)
                  coordinate system, as well as its velocity.
             d. Convert the ECI coordinates to Earth-Centered Earth-Fixed (ECEF) using
                ConvertECIToECEF() and the computed GMST.
             e. Compute geodetic longitude (lons) via ComputeGeodeticLon() (and convert to degrees),
                and latitude (lats) via ComputeGeodeticLat2() (converted to degrees).
             f. Calculate the altitude in kilometers as:
                alt_km = (first value of semi-major axis in km) – (Earth radius in km)
             g. Store the latitudes, longitudes, and altitude in the latslons_dict.
             h. Print a comparison summary (N2YO style) with satellite name, current UTC time,
                latitude, longitude, altitude, and speed (computed from the final velocity vector).
        9. Return latslons_dict.

    Note:
        - The use_skyfield flag is provided for future convenience or alternate mode;
          the Skyfield option is currently commented out.
    """
    # Get current UTC and predict 90 minutes into the future
    utc_now = datetime.utcnow()
    utc_start_time = utc_now.strftime('%Y %m %d %H %M %S')
    utc_future = utc_now + timedelta(minutes=90)
    utc_end_time = utc_future.strftime('%Y %m %d %H %M %S')

    # Compute Keplerian elements over the prediction window.
    # ConvertTLEToKepElem returns a dictionary keyed by satellite name.
    kep_elem_dict, _, epoch_year = ConvertTLEToKepElem(tle_dict, utc_start_time, utc_end_time)

    # For current prediction, reset epoch_year to the current year.
    epoch_year = utc_now.year

    # Recompute the current fractional day-of-year from utc_now.
    utc_now = datetime.utcnow()
    year = utc_now.year
    day_of_year = utc_now.timetuple().tm_yday
    fractional_day = (day_of_year +
                      utc_now.hour / 24.0 +
                      utc_now.minute / 1440.0 +
                      utc_now.second / 86400.0)

    # Define prediction range: from now to now + 90 minutes (in days)
    delta_days = (90 * 60) / (24.0 * 3600.0)
    start_day = fractional_day
    end_day = start_day + delta_days
    time_vec = np.linspace(start_day, end_day, num=c.num_time_pts)

    # Convert fractional day-of-year into full UTC dates (Y M D H M S)
    time_array = Nth_day_to_date(year, time_vec)

    # Calculate Julian Dates and then Greenwich Mean Sidereal Time (gmst) for the time vector.
    jday = JdayInternal(time_array)
    gmst = CalculateGMSTFromJD(jday, time_vec)

    # Initialize dictionary to store the results for each satellite.
    latslons_dict = {}

    # Process each satellite's Keplerian elements.
    for key in kep_elem_dict:
        values = kep_elem_dict[key]
        a = values[:, 0]          # Semi-major axis
        e = values[:, 1]          # Eccentricity
        i = values[:, 2]          # Inclination (radians)
        Omega = values[:, 3]      # RAAN (radians)
        w = values[:, 4]          # Argument of perigee (radians)
        nu = values[:, 5]         # True anomaly (radians)
        epoch_days = values[:, 8] # Epoch day (fractional day-of-year)

        # Compute the time offset from TLE epoch for each step in time_vec.
        delta_time_vec = time_vec - epoch_days

        # Convert Keplerian elements and the time offsets to ECI position and velocity vectors.
        X_eci, Y_eci, Z_eci, Xdot_eci, Ydot_eci, Zdot_eci = ConvertKeplerToECI(
            a, e, i, Omega, w, nu, delta_time_vec
        )

        # Rotate ECI coordinates into the ECEF frame using the computed GMST.
        X_ecef, Y_ecef, Z_ecef = ConvertECIToECEF(X_eci, Y_eci, Z_eci, gmst)

        # Compute geodetic longitude and latitude (in radians), then convert to degrees.
        lons = ComputeGeodeticLon(X_ecef, Y_ecef) * c.rad2deg
        lats = ComputeGeodeticLat2(X_ecef, Y_ecef, Z_ecef, a, e) * c.rad2deg

        # Compute altitude (in kilometers) from the semi-major axis.
        # Here, we assume the first value of a represents the orbit and subtract Earth's radius.
        alt_km = a[0] / 1000.0 - c.Re / 1000.0

        # Store the computed latitudes, longitudes, and altitude in the result dictionary.
        latslons_dict[key] = {
            'lons': lons,
            'lats': lats,
            'alt_km': alt_km
        }

        # Also prepare a combined array for printing purposes.
        results = np.column_stack((lons, lats))
        # Compute speed (in km/s) from the final velocity vector components.
        speed_kms = np.linalg.norm([Xdot_eci[-1], Ydot_eci[-1], Zdot_eci[-1]]) / 1000.0

        # Print out a summary style similar to N2YO for comparison.
        print("\n--- N2YO Comparison Style ---")
        print(f"Satellite:     {key}")
        print(f"UTC Time:      {utc_now.strftime('%H:%M:%S')}")
        print(f"LATITUDE:      {results[0, 1]:.2f}°")
        print(f"LONGITUDE:     {results[0, 0]:.2f}°")
        print(f"ALTITUDE [km]: {alt_km:.2f}")
        print(f"SPEED [km/s]:  {speed_kms:.2f}")
        print(f"-----------------------------\n")

    # Return the dictionary containing state vector information (lat, lon, altitude).
    return latslons_dict
