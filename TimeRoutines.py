import datetime
import numpy as np
import pytz
import sys
import constants as c

def ConvertLocalTimeToUTC(local_time, used_format='%Y %m %d %H %M %S'):
    """
    Convert local_time (a string) in 'used_format' from local (America/New_York)
    to a UTC time string of the same format.
    """
    local_dt = datetime.datetime.strptime(local_time, used_format)
    local_tz = pytz.timezone("Etc/GMT+6")
    local_dt = local_tz.localize(local_dt, is_dst=True)
    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt.strftime(used_format)

def GenerateTimeVec(utc_start_time, utc_end_time, tle_epoch_year, tle_epoch_days):
    """
    Creates a time vector (in days) from utc_start_time to utc_end_time,
    ensuring it's not earlier than the TLE epoch.
    """
    if tle_epoch_year < 57:  # e.g. if 23 means 2023
        tle_epoch_year += 2000
    else:
        tle_epoch_year += 1900

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

    future_start_days = Date_to_nth_day(utc_start_time)
    future_end_days = Date_to_nth_day(utc_end_time)

    if future_start_days > future_end_days:
        print("Cannot choose future start time to be greater than end time.")
        sys.exit()

    if future_start_days < tle_epoch_days:
        future_start_days = tle_epoch_days
        print(f"Entered start day forced to TLE epoch: {tle_epoch_days}")

    # create a vector of times in days
    time_vec = np.linspace(future_start_days, future_end_days,
                           num=c.num_time_pts, endpoint=True)
    return time_vec, tle_epoch_year

def Date_to_nth_day(date_str, used_format='%Y %m %d %H %M %S'):
    """
    Convert a date string into the 'nth day' of the year with fractional part.
    E.g. "2023 05 18 06 00 00" -> 138.25 if it was 6:00 AM on the 138th day.
    """
    dt = datetime.datetime.strptime(date_str, used_format)
    new_year_day = datetime.datetime(dt.year, 1, 1, 0, 0, 0)
    delta = dt - new_year_day
    num_days = (delta.days + 1) + (delta.seconds / (24.0 * 3600.0))
    return num_days

def Nth_day_to_date(year, ndays):
    """
    Convert 'ndays' (Nth day of year, float) into a structured array of [Y M D H M S].
    If year is an array, this must handle that, else if it's scalar, apply to all.
    """
    year_array_len = np.size(year)
    days_array_len = np.size(ndays)
    results = np.zeros((days_array_len, 6), dtype=int)

    if year_array_len == 1 and days_array_len > 1:
        # apply the single year to multiple ndays
        year = year * np.ones((days_array_len,), dtype=int)
        for ii in range(days_array_len):
            this_date = datetime.datetime(year[ii], 1, 1) + \
                        datetime.timedelta(ndays[ii] - 1.0)
            s = this_date.strftime('%Y %m %d %H %M %S')
            tmp = np.fromstring(s, dtype=int, sep=' ')
            results[ii, :] = tmp

    elif year_array_len == 1 and days_array_len == 1:
        # single year, single day
        this_date = datetime.datetime(year, 1, 1) + \
                    datetime.timedelta(ndays[0] - 1.0)
        s = this_date.strftime('%Y %m %d %H %M %S')
        tmp = np.fromstring(s, dtype=int, sep=' ')
        results[0, :] = tmp

    return results

def JdayInternal(ymdhms):
    """
    Convert an Nx6 array [year, month, day, hour, min, sec] -> Nx1 array of Julian Dates.
    """
    year = ymdhms[:, 0]
    mon = ymdhms[:, 1]
    day = ymdhms[:, 2]
    hr = ymdhms[:, 3]
    minute = ymdhms[:, 4]
    sec = ymdhms[:, 5]

    jday = (367.0 * year) - np.floor(7.0 * (year + np.floor((mon + 9.0) / 12.0)) * 0.25) \
          + np.floor(275.0 * mon / 9.0) + day + 1721013.5
    jdfrac = (sec + minute * 60.0 + hr * 3600.0) / 86400.0
    jday += jdfrac
    return jday

def CalculateGMSTFromJD(jdut1, time_vec):
    """
    For each element in jdut1 (the Julian date), compute GMST,
    add fraction from time_vec's fractional part, and mod by 2 pi.
    """
    gmst = np.zeros((jdut1.size,), dtype=float)
    for ii in range(jdut1.size):
        JDmin = np.floor(jdut1[ii]) - 0.5
        JDmax = np.floor(jdut1[ii]) + 0.5
        if jdut1[ii] > JDmin:
            JD0 = JDmin
        if jdut1[ii] > JDmax:
            JD0 = JDmax

        T = (JD0 - 2451545.0) / 36525.0
        gmst00 = (-6.2e-6 * T**3) + (0.093104 * T**2) \
                 + (8640184.812866 * T) + 24110.548416
        # convert to degrees, then radians
        gmst00 *= (360.0 / 86400.0) * c.deg2rad

        fractional_part = (time_vec[ii] - np.floor(time_vec[ii])) * (24.0 * 3600.0)
        gmst[ii] = (gmst00 + c.omega_earth * fractional_part) % c.twoPi

    return gmst
