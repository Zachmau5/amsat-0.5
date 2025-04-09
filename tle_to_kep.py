import numpy as np
import scipy.optimize
import constants as c
from TimeRoutines import GenerateTimeVec, Nth_day_to_date, JdayInternal, CalculateGMSTFromJD
from coordinate_conversions import ConvertKeplerToECI, ConvertECIToECEF
# etc.

def KeplerEquation(E, M, ecc):
    return M - (E - ecc * np.sin(E))

def DKeplerEquation(E, M, ecc):
    return -1.0 + ecc * np.cos(E)

def GetTrueAnomaly(E, ecc):
    sinnu = np.sqrt(1.0 - ecc*ecc) * np.sin(E)
    cosnu = np.cos(E) - ecc
    return np.arctan2(sinnu, cosnu)

def ConvertTLEToKepElem(tle_dict, utc_start_time, utc_end_time):
    """
    Converts TLE data from the parse (sat_name -> [ epoch_year, epoch_days, inclination, RAAN, ecc, arg_perigee, mean_anomaly, mean_motion, ftdmm ])
    into kepler elements for the requested time range.
    """
    results = {}
    for sat_name in tle_dict:
        arr = tle_dict[sat_name]
        epoch_year = int(arr[0])
        epoch_days = arr[1]
        inclination = arr[2]*c.deg2rad
        raan = arr[3]*c.deg2rad
        ecc = arr[4]
        arg_perigee = arr[5]*c.deg2rad
        mean_anomaly = arr[6]*c.deg2rad
        mean_motion = arr[7]*c.twoPi*c.day2sec  # rev/day -> rad/s
        ftdmm = arr[8]*c.twoPi*c.day2sec*c.day2sec

        time_vec, epoch_year_int = GenerateTimeVec(utc_start_time, utc_end_time, epoch_year, epoch_days)

        # current M(t)
        delta_time_vec = (time_vec - epoch_days) * (24.0 * 3600.0)
        current_mm = mean_motion + 0.5 * ftdmm * delta_time_vec
        M = mean_anomaly + current_mm * delta_time_vec
        M = np.mod(M, c.twoPi)

        # semi-major axis
        a = np.power(c.GM / (current_mm**2), 1.0/3.0)

        # solve E from M
        E_arr = []
        for i in range(M.size):
            sol = scipy.optimize.newton(KeplerEquation, M[i], fprime=DKeplerEquation, args=(M[i], ecc))
            E_arr.append(sol)
        E_arr = np.array(E_arr)

        # true anomaly
        nu_arr = GetTrueAnomaly(E_arr, ecc)
        # stack results
        n_rows = M.size
        tmp = np.zeros((n_rows, 9))
        tmp[:, 0] = a
        tmp[:, 1] = ecc
        tmp[:, 2] = inclination
        tmp[:, 3] = raan
        tmp[:, 4] = arg_perigee
        tmp[:, 5] = nu_arr
        tmp[:, 6] = E_arr
        tmp[:, 7] = epoch_year_int
        tmp[:, 8] = epoch_days

        results[sat_name] = tmp

    return results, time_vec, epoch_year_int
