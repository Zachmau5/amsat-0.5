import numpy as np
import scipy.optimize
import constants as c
from TimeRoutines import GenerateTimeVec, Nth_day_to_date, JdayInternal, CalculateGMSTFromJD
from coordinate_conversions import ConvertKeplerToECI, ConvertECIToECEF
# etc.

###############################################################################
# Function: KeplerEquation
###############################################################################
def KeplerEquation(E, M, ecc):
    """
    Kepler's Equation in the form:

        M = E - ecc * sin(E)

    Rearranged to express the difference:

        f(E) = M - (E - ecc * sin(E))

    which is to be driven to zero.

    Parameters:
        E : float
            Eccentric anomaly (in radians), the unknown to solve for.
        M : float
            Mean anomaly (in radians), computed for a given time.
        ecc : float
            The orbit eccentricity (dimensionless).

    Returns:
        float: The residual f(E), which is zero when E is the correct eccentric anomaly.
    """
    return M - (E - ecc * np.sin(E))

###############################################################################
# Function: DKeplerEquation
###############################################################################
def DKeplerEquation(E, M, ecc):
    """
    Derivative of Kepler's Equation with respect to E.

    The derivative f'(E) is:

        f'(E) = d/dE [M - (E - ecc*sin(E))] = - (1 - ecc*cos(E))

    However, in this implementation it is given as:

        f'(E) = -1.0 + ecc * cos(E)

    which is mathematically equivalent.

    Parameters:
        E : float
            Eccentric anomaly (radians).
        M : float
            Mean anomaly (radians) (not used in the derivative but kept for the
            function signature consistent with the solver).
        ecc : float
            Eccentricity.

    Returns:
        float: The derivative of Kepler's Equation with respect to E.
    """
    return -1.0 + ecc * np.cos(E)

###############################################################################
# Function: GetTrueAnomaly
###############################################################################
def GetTrueAnomaly(E, ecc):
    """
    Calculate the True Anomaly from the eccentric anomaly.

    The true anomaly (ν) represents the actual angular position of the
    satellite in its elliptical orbit relative to perigee, as opposed to the
    mean anomaly which assumes constant motion.

    It is computed using the formulas:

        sin(ν) = sqrt(1 - ecc^2) * sin(E)
        cos(ν) = cos(E) - ecc

    and then taking the arctan2 of these values:

        ν = arctan2(sin(ν), cos(ν))

    Parameters:
        E : float or array
            Eccentric anomaly (in radians).
        ecc : float
            Eccentricity of the orbit.

    Returns:
        float or array: The true anomaly (ν in radians).
    """
    sinnu = np.sqrt(1.0 - ecc*ecc) * np.sin(E)
    cosnu = np.cos(E) - ecc
    return np.arctan2(sinnu, cosnu)

###############################################################################
# Function: ConvertTLEToKepElem
###############################################################################
def ConvertTLEToKepElem(tle_dict, utc_start_time, utc_end_time):
    """
    Converts parsed TLE data into evolving Keplerian orbital elements
    for a given prediction time range.

    The input TLE dictionary (tle_dict) is structured as:
        sat_name -> [epoch_year, epoch_days, inclination, RAAN, ecc, arg_perigee,
                      mean_anomaly, mean_motion, ftdmm]

    The output Keplerian elements for each satellite are provided as an array with
    9 columns corresponding to:
        Index 0: Semi-major axis (a) in meters (computed later)
        Index 1: Eccentricity (ecc)
        Index 2: Inclination (i) in radians
        Index 3: RAAN (Ω) in radians
        Index 4: Argument of perigee (ω) in radians
        Index 5: True anomaly (ν) in radians (computed from eccentric anomaly)
        Index 6: Eccentric anomaly (E) in radians (solution from Kepler's Equation)
        Index 7: The (full) epoch year (e.g., 2023 or 2024)
        Index 8: The TLE epoch as fractional day-of-year (epoch_days)

    Process Details:
      1. For each satellite in the TLE dictionary:
            - Extract raw values:
                epoch_year: last two digits from the epoch string.
                epoch_days: fractional day-of-year from the epoch.
                inclination, RAAN, arg_perigee, and mean_anomaly are given in degrees
                  and are converted to radians.
                mean_motion is given in rev/day and is converted to rad/s as:
                     mean_motion (rad/s) = mean_motion (rev/day) * 2π * day2sec.
                ftdmm is the drag term, scaled appropriately.
      2. Generate a time vector using GenerateTimeVec() that spans from utc_start_time to utc_end_time.
         This time vector (time_vec) is in days.
      3. Compute the time offset vector (delta_time_vec) in seconds by converting the difference
         (time_vec - epoch_days) from days to seconds.
      4. Propagate the mean anomaly over time:
             current_mm = mean_motion + 0.5 * ftdmm * delta_time_vec
             M(t) = mean_anomaly + current_mm * delta_time_vec, then modulo 2π.
      5. Compute the semi-major axis (a) from mean motion using Kepler's Third Law:
             a = (GM / current_mm^2)^(1/3)
      6. For each time point, solve Kepler's Equation numerically for the eccentric anomaly (E):
             Use the Newton-Raphson method (scipy.optimize.newton) with
             KeplerEquation and DKeplerEquation.
      7. Compute the true anomaly (ν) from the eccentric anomaly (E) using GetTrueAnomaly().
      8. Stack the resulting columns into an output array with 9 columns. Then save the array
         in the results dictionary keyed by satellite name.

    Parameters:
        tle_dict : dict
            Dictionary with TLE data per satellite.
        utc_start_time : str
            Start time in the format 'YYYY MM DD HH MM SS' for propagation.
        utc_end_time : str
            End time in the same format.

    Returns:
        tuple:
            - results (dict): Dictionary where each key (satellite name) maps to an ndarray of shape (N, 9)
              containing the computed Keplerian elements at each time step.
            - time_vec (ndarray): The vector of time points (in fractional days) used for propagation.
            - epoch_year_int (int): The adjusted full epoch year.
    """
    results = {}
    for sat_name in tle_dict:
        arr = tle_dict[sat_name]
        # Parse epoch information from TLE:
        epoch_year = int(arr[0])
        epoch_days = arr[1]
        # Convert angular quantities from degrees to radians.
        inclination = arr[2] * c.deg2rad
        raan = arr[3] * c.deg2rad
        ecc = arr[4]
        arg_perigee = arr[5] * c.deg2rad
        mean_anomaly = arr[6] * c.deg2rad
        # Convert mean motion from rev/day to rad/s:
        mean_motion = arr[7] * c.twoPi * c.day2sec
        # ftdmm is the drag/second derivative term (scaled appropriately).
        ftdmm = arr[8] * c.twoPi * c.day2sec * c.day2sec

        # Generate time vector (in days) for the propagation period.
        time_vec, epoch_year_int = GenerateTimeVec(utc_start_time, utc_end_time, epoch_year, epoch_days)

        # Calculate the time offset in seconds from the epoch.
        delta_time_vec = (time_vec - epoch_days) * (24.0 * 3600.0)
        # Adjust the mean motion for any change over time due to drag.
        current_mm = mean_motion + 0.5 * ftdmm * delta_time_vec
        # Propagate the mean anomaly: M(t) = mean_anomaly + current_mean_motion * time_offset.
        M = mean_anomaly + current_mm * delta_time_vec
        # Ensure mean anomaly wraps between 0 and 2π.
        M = np.mod(M, c.twoPi)

        # Compute the semi-major axis using the relation from Kepler's Third Law:
        #   a = (GM / (current_mm)^2)^(1/3)
        a = np.power(c.GM / (current_mm ** 2), 1.0 / 3.0)

        # Solve Kepler's equation to find the eccentric anomaly for each time step.
        E_arr = []
        for i in range(M.size):
            # Newton-Raphson method: starting guess is M[i].
            sol = scipy.optimize.newton(KeplerEquation, M[i], fprime=DKeplerEquation, args=(M[i], ecc))
            E_arr.append(sol)
        E_arr = np.array(E_arr)

        # Compute the true anomaly from the eccentric anomaly.
        nu_arr = GetTrueAnomaly(E_arr, ecc)
        # Stack all computed values into an array with 9 columns.
        # Columns: [a, ecc, inclination, RAAN, argument of perigee, true anomaly, eccentric anomaly, epoch_year, epoch_days]
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
