import datetime
import numpy as np
import pytz
import sys
import constants as c

###############################################################################
# Function: ConvertLocalTimeToUTC
###############################################################################
def ConvertLocalTimeToUTC(local_time, used_format='%Y %m %d %H %M %S'):
    """
    Convert a local time string into a UTC time string in the same format.

    The local time is assumed to be in the timezone America/New_York (here adjusted using
    "Etc/GMT+6", which may be appropriate depending on daylight saving rules).

    Parameters:
        local_time (str): The local time as a string (e.g., "2023 05 18 06 00 00").
        used_format (str): The format of the date/time string. Default is '%Y %m %d %H %M %S'.

    Process:
        1. Parse the local time string to a datetime object.
        2. Set the timezone for the local datetime object (here "Etc/GMT+6"). Note that
           using "Etc/GMT+6" might be equivalent to some US Eastern time zone settings,
           but verify this for your region and daylight savings.
        3. Convert the localized datetime to UTC.
        4. Return the UTC time as a string in the same format.

    Returns:
        str: The UTC time string.
    """
    local_dt = datetime.datetime.strptime(local_time, used_format)
    local_tz = pytz.timezone("Etc/GMT+6")
    local_dt = local_tz.localize(local_dt, is_dst=True)
    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt.strftime(used_format)

###############################################################################
# Function: GenerateTimeVec
###############################################################################
def GenerateTimeVec(utc_start_time, utc_end_time, tle_epoch_year, tle_epoch_days):
    """
    Create a time vector (in days) from utc_start_time to utc_end_time, ensuring
    that the generated times do not precede the TLE epoch.

    This function does the following:
      1. Adjusts the TLE epoch year: If the provided TLE year is less than 57, it is
         assumed to be in the 2000s; otherwise, in the 1900s. (This is a convention for
         TLEs with two-digit years.)
      2. Extracts the year from the utc_start_time and utc_end_time strings.
      3. If the start or end year is inconsistent with the TLE epoch year, prints a warning and
         forces the year to be the same as the TLE epoch.
      4. Converts the utc_start_time and utc_end_time to "nth day" of the year (a fractional day
         number) using Date_to_nth_day().
      5. Checks that the start time is not later than the end time.
      6. Ensures that the start day is not before the TLE epoch day.
      7. Uses numpy.linspace to create a vector of times, in days, from the (possibly adjusted)
         start day to end day, with a total number of points given by c.num_time_pts.

    Parameters:
        utc_start_time (str): Start time in the used_format (e.g. 'YYYY MM DD HH MM SS').
        utc_end_time (str): End time in the used_format.
        tle_epoch_year (int): The two-digit year from the TLE epoch.
        tle_epoch_days (float): The day-of-year (plus fractional part) from the TLE epoch.

    Returns:
        tuple:
            - time_vec (ndarray): A linearly spaced vector (in fractional days) for prediction.
            - tle_epoch_year (int): The adjusted full four-digit year of the TLE epoch.
    """
    # Adjust the TLE epoch year to full year (e.g., if <57, then add 2000; otherwise add 1900)
    if tle_epoch_year < 57:  # Convention: e.g., if "23" then it means 2023.
        tle_epoch_year += 2000
    else:
        tle_epoch_year += 1900

    # Extract the year from the utc_start and utc_end strings.
    future_start_year = float(utc_start_time[0:4])
    future_end_year = float(utc_end_time[0:4])
    if future_start_year > future_end_year:
        future_start_year = tle_epoch_year
        future_end_year = tle_epoch_year
        print("Forcing entered start and end year to be same as TLE epoch year")

    if future_start_year < tle_epoch_year:
        future_start_year = tle_epoch_year
        print("Forcing entered start year to be same as TLE epoch year")

    if future_end_year < tle_epoch_year:
        future_end_year = tle_epoch_year
        print("Max future end year forced to be same as TLE epoch year")

    # Convert the start and end times to fractional day-of-year.
    future_start_days = Date_to_nth_day(utc_start_time)
    future_end_days = Date_to_nth_day(utc_end_time)

    if future_start_days > future_end_days:
        print("Cannot choose future start time to be greater than end time.")
        sys.exit()

    if future_start_days < tle_epoch_days:
        future_start_days = tle_epoch_days
        print(f"Entered start day forced to TLE epoch: {tle_epoch_days}")

    # Create a vector of times (in days) spanning the prediction period.
    time_vec = np.linspace(future_start_days, future_end_days,
                           num=c.num_time_pts, endpoint=True)
    return time_vec, tle_epoch_year

###############################################################################
# Function: Date_to_nth_day
###############################################################################
def Date_to_nth_day(date_str, used_format='%Y %m %d %H %M %S'):
    """
    Convert a date string into the "nth day" of the year (with a fractional part).

    For example, "2023 05 18 06 00 00" is converted to a number representing the day
    of the year plus a fraction corresponding to the time of day (e.g., 138.25 if it is 6:00 AM on the 138th day).

    Parameters:
        date_str (str): A date string (e.g., "2023 05 18 06 00 00").
        used_format (str): The format string for parsing the date. Default is '%Y %m %d %H %M %S'.

    Returns:
        float: The "nth day" of the year, where the integer part is the day number
               and the fractional part represents the time.
    """
    dt = datetime.datetime.strptime(date_str, used_format)
    new_year_day = datetime.datetime(dt.year, 1, 1, 0, 0, 0)
    delta = dt - new_year_day
    # Note: Adding 1 because January 1st is considered day 1
    num_days = (delta.days + 1) + (delta.seconds / (24.0 * 3600.0))
    return num_days

###############################################################################
# Function: Nth_day_to_date
###############################################################################
def Nth_day_to_date(year, ndays):
    """
    Convert a fractional day-of-year (ndays) into an array of [year, month, day, hour, minute, second].

    This function works for both scalar and vector inputs.
    For a given year (or array of years) and fractional days (ndays),
    it returns a 2D array of shape (len(ndays), 6) where each row corresponds to
    a date in the format: [Year, Month, Day, Hour, Minute, Second].

    Parameters:
        year : int or ndarray
            The year corresponding to the day(s).
        ndays : float or ndarray
            Fractional day-of-year; e.g., 138.25 for 6:00 AM on the 138th day.

    Returns:
        ndarray: An array of integers of shape (N, 6), where N is the number of dates,
                 in the order [year, month, day, hour, minute, second].
    """
    year_array_len = np.size(year)
    days_array_len = np.size(ndays)
    results = np.zeros((days_array_len, 6), dtype=int)

    # If a single year is given and multiple days,
    # create an array of the same year for each day.
    if year_array_len == 1 and days_array_len > 1:
        year = year * np.ones((days_array_len,), dtype=int)
        for ii in range(days_array_len):
            # ndays[ii] is the fractional day-of-year; subtract 1 because January 1st is day 1.
            this_date = datetime.datetime(year[ii], 1, 1) + datetime.timedelta(ndays[ii] - 1.0)
            s = this_date.strftime('%Y %m %d %H %M %S')
            tmp = np.fromstring(s, dtype=int, sep=' ')
            results[ii, :] = tmp

    # If both year and ndays are scalars:
    elif year_array_len == 1 and days_array_len == 1:
        this_date = datetime.datetime(year, 1, 1) + datetime.timedelta(ndays[0] - 1.0)
        s = this_date.strftime('%Y %m %d %H %M %S')
        tmp = np.fromstring(s, dtype=int, sep=' ')
        results[0, :] = tmp

    return results

###############################################################################
# Function: JdayInternal
###############################################################################
def JdayInternal(ymdhms):
    """
    Convert an array of date/time values (Nx6: [year, month, day, hour, min, sec])
    into a corresponding 1D array of Julian Dates.

    The formula used here is a variant of the standard conversion formula:

        JD = 367 * year - floor(7 * (year + floor((month+9)/12))/4)
             + floor(275 * month/9) + day + 1721013.5 + fraction_of_day

    Parameters:
        ymdhms : ndarray
            A 2D NumPy array of shape (N,6) where each row is [year, month, day, hour, minute, second].

    Returns:
        ndarray: A 1D array of Julian Dates for each input date.
    """
    year = ymdhms[:, 0]
    mon = ymdhms[:, 1]
    day = ymdhms[:, 2]
    hr = ymdhms[:, 3]
    minute = ymdhms[:, 4]
    sec = ymdhms[:, 5]

    # Compute the integral part of the Julian date.
    jday = (367.0 * year) - np.floor(7.0 * (year + np.floor((mon + 9.0) / 12.0)) * 0.25) \
          + np.floor(275.0 * mon / 9.0) + day + 1721013.5
    # Add the fractional day (time portion).
    jdfrac = (sec + minute * 60.0 + hr * 3600.0) / 86400.0
    jday += jdfrac
    return jday

###############################################################################
# Function: CalculateGMSTFromJD
###############################################################################
def CalculateGMSTFromJD(jdut1, time_vec):
    """
    Calculate the Greenwich Mean Sidereal Time (GMST) for a given Julian Date array.

    For each element in jdut1, this function computes GMST using an empirical formula:

        GMST_seconds = -6.2e-6*T^3 + 0.093104*T^2 + 8640184.812866*T + 24110.548416,

    where T is the centuries since J2000:

        T = (JD0 - 2451545.0) / 36525.0,

    and JD0 is chosen as either the floor of JDut1 minus 0.5 or plus 0.5 (whichever is appropriate).

    The GMST (initial value) is then converted from seconds to radians.

    Finally, the fractional part of the day (from time_vec) is used to adjust GMST by the Earth's
    rotation rate (omega_earth), and the result is taken modulo 2π.

    Parameters:
        jdut1 : ndarray
            1D array of Julian Dates.
        time_vec : ndarray
            Time vector in fractional days corresponding to jdut1.

    Returns:
        ndarray: A 1D array of GMST values in radians for each time entry.
    """
    gmst = np.zeros((jdut1.size,), dtype=float)
    for ii in range(jdut1.size):
        # Determine JD0: the reference Julian date at which the rotation resets.
        JDmin = np.floor(jdut1[ii]) - 0.5
        JDmax = np.floor(jdut1[ii]) + 0.5
        if jdut1[ii] > JDmin:
            JD0 = JDmin
        if jdut1[ii] > JDmax:
            JD0 = JDmax

        # T is the number of Julian centuries since J2000.0.
        T = (JD0 - 2451545.0) / 36525.0
        # GMST calculated in seconds (formula is an empirical approximation).
        gmst00 = (-6.2e-6 * T**3) + (0.093104 * T**2) + (8640184.812866 * T) + 24110.548416
        # Convert the GMST from seconds to radians.
        gmst00 *= (360.0 / 86400.0) * c.deg2rad

        # The fractional part of the day (in seconds) is added in.
        fractional_part = (time_vec[ii] - np.floor(time_vec[ii])) * (24.0 * 3600.0)
        gmst[ii] = (gmst00 + c.omega_earth * fractional_part) % c.twoPi

    return gmst
