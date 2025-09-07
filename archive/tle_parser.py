# tle_parser.py

import numpy as np
import scipy.optimize
import constants as c
from TimeRoutines import GenerateTimeVec
from coordinate_conversions import ConvertKeplerToECI, ConvertECIToECEF

###############################################################################
# Kepler’s Equation and Helpers
###############################################################################
def KeplerEquation(E, M, ecc):
    """
    Kepler's Equation:  M = E - ecc*sin(E)
    """
    return E - ecc * np.sin(E) - M

def DKeplerEquation(E, M, ecc):
    """
    Derivative w.r.t. E:  d/dE [E - ecc*sin(E) - M] = 1 - ecc*cos(E)
    """
    return 1 - ecc * np.cos(E)

def GetTrueAnomaly(E, ecc):
    """
    Compute true anomaly ν from eccentric anomaly E and eccentricity ecc.
    """
    sin_v = np.sqrt(1 - ecc ** 2) * np.sin(E) / (1 - ecc * np.cos(E))
    cos_v = (np.cos(E) - ecc) / (1 - ecc * np.cos(E))
    return np.arctan2(sin_v, cos_v)

###############################################################################
# 1) Parse TLE File into Raw Elements
###############################################################################
def ParseTwoLineElementFile(filename):
    """
    Parses a TLE file (3 lines per satellite) into a dict:
      sat_name -> np.array([epoch_year, epoch_days,
                            incl_deg, raan_deg, ecc,
                            argp_deg, m0_deg, mm_rev_per_day, bstar])
    """
    results_dict = {}
    with open(filename, 'r') as f:
        lines = [L.strip() for L in f if L.strip()]

    counter = 0
    results = np.zeros(9, dtype=float)

    for line in lines:
        split_line = line.split()

        if counter == 0:
            # Satellite name
            sat_name = line if line else "UNKNOWN"

        elif counter == 1:
            # Epoch and drag term
            #   Field 3: epoch (YYDDD.FFFFFF)
            #   Field 4: B* drag term
            epoch_full    = float(split_line[3])
            epoch_year    = int(str(split_line[3]).split('.')[0])
            epoch_days    = epoch_full
            bstar         = float(split_line[4])

            results[0] = epoch_year
            results[1] = epoch_days
            results[8] = bstar

        elif counter == 2:
            # Orbital elements line:
            #   [2]=inclination (deg), [3]=RAAN (deg),
            #   [4]=ecc (no leading 0), [5]=argp (deg),
            #   [6]=m0 (deg), [7]=mm (rev/day)
            incl        = float(split_line[2])
            raan        = float(split_line[3])
            ecc_str     = split_line[4]
            if not ecc_str.startswith('.'):
                ecc_str = '.' + ecc_str
            ecc         = float(ecc_str)
            arg_perigee = float(split_line[5])
            m0          = float(split_line[6])
            mm          = float(split_line[7])

            results[2] = incl
            results[3] = raan
            results[4] = ecc
            results[5] = arg_perigee
            results[6] = m0
            results[7] = mm

            # Save and reset
            results_dict[sat_name] = results.copy()
            results = np.zeros(9, dtype=float)

        counter = (counter + 1) % 3

    return results_dict

###############################################################################
# 2) Convert Parsed TLEs → Time‐Stamped Keplerian Elements
###############################################################################
def ConvertTLEToKepElem(tle_dict, utc_start_time, utc_end_time):
    """
    For each satellite in tle_dict, propagate its Keplerian elements over the time range.
    Returns:
      results    dict sat_name -> ndarray of shape (N,9)
      time_vec   np.array of N UTC times (in fractional days)
      epoch_year int final processed epoch year (two-digit)
    """
    results = {}

    # Use the first entry to pull epoch info for the time vector
    first = next(iter(tle_dict.values()))
    epoch_year  = int(first[0])
    epoch_days  = first[1]
    time_vec, epoch_year_int = GenerateTimeVec(
        utc_start_time, utc_end_time, epoch_year, epoch_days
    )

    # Propagate each satellite
    for sat_name, arr in tle_dict.items():
        epoch_year   = int(arr[0])
        epoch_days   = arr[1]
        i_rad        = arr[2] * c.deg2rad
        raan_rad     = arr[3] * c.deg2rad
        ecc          = arr[4]
        argp_rad     = arr[5] * c.deg2rad
        m0_rad       = arr[6] * c.deg2rad
        mm_rad_s     = arr[7] * c.twoPi * c.day2sec
        ftdmm        = arr[8] * c.twoPi * c.day2sec * c.day2sec

        # Time since epoch (s)
        dt_vec = (time_vec - epoch_days) * (24.0 * 3600.0)
        # Drag‐adjusted mean motion
        mm_curr = mm_rad_s + 0.5 * ftdmm * dt_vec
        # Mean anomaly propagation
        M = m0_rad + mm_curr * dt_vec
        M = np.mod(M, c.twoPi)
        # Semi-major axis from Kepler’s 3rd law
        a = np.power(c.GM / (mm_curr**2), 1.0 / 3.0)

        # Solve Kepler’s equation → E
        E_arr = np.array([
            scipy.optimize.newton(
                KeplerEquation, M[k], fprime=DKeplerEquation, args=(M[k], ecc)
            )
            for k in range(M.size)
        ])
        # True anomaly
        nu_arr = GetTrueAnomaly(E_arr, ecc)

        # Bundle into an (N×9) array: [a, ecc, i, raan, argp, nu, E, epoch_year, epoch_days]
        N = M.size
        mat = np.zeros((N, 9))
        mat[:, 0] = a
        mat[:, 1] = ecc
        mat[:, 2] = i_rad
        mat[:, 3] = raan_rad
        mat[:, 4] = argp_rad
        mat[:, 5] = nu_arr
        mat[:, 6] = E_arr
        mat[:, 7] = epoch_year_int
        mat[:, 8] = epoch_days

        results[sat_name] = mat

    return results, time_vec, epoch_year_int

###############################################################################
# 3) One‐Line Wrapper: Parse + Convert
###############################################################################
def parse_and_convert_tle(filename, utc_start_time, utc_end_time):
    """
    Convenience function:  
      1) Parse a TLE file  
      2) Propagate all entries over [utc_start_time, utc_end_time]  
    Returns the same (results, time_vec, epoch_year) as ConvertTLEToKepElem.
    """
    tle_dict = ParseTwoLineElementFile(filename)
    return ConvertTLEToKepElem(tle_dict, utc_start_time, utc_end_time)

