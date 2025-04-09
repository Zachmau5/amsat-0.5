import numpy as np
import constants as c

def RAANPrecession(a, e, i):
    eSq = e * e
    precession = np.divide(
        -1.5 * c.J2 * np.sqrt(c.GM) * (c.Re * c.Re) * np.cos(i),
        np.power(a, 3.5) * (1.0 - eSq) * (1.0 - eSq)
    )
    return precession

def ArgPerigeePrecession(a, e, i):
    eSq = e * e
    sini = np.sin(i)
    sin_i_sq = sini * sini
    precession = np.divide(
        0.75 * c.J2 * np.sqrt(c.GM) * (c.Re * c.Re) * (5.0 * sin_i_sq - 1.0),
        np.power(a, 3.5) * (1.0 - eSq) * (1.0 - eSq)
    )
    return precession

def ConvertKeplerToECI(a, e, i, Omega, w, nu, time_vec):
    """
    Convert orbital elements to ECI.
    a = semi-major axis
    e = eccentricity
    i = inclination
    Omega = RAAN
    w = argument of perigee
    nu = true anomaly
    time_vec = times offset from TLE epoch (days)
    """
    # Update RAAN and argument of perigee based on precession
    w_precession = ArgPerigeePrecession(a, e, i)
    w = w + (time_vec * (24.0 * 3600.0)) * w_precession

    Omega_precession = RAANPrecession(a, e, i)
    Omega = Omega + (time_vec * (24.0 * 3600.0)) * Omega_precession

    # Pre-calculate
    sinnu = np.sin(nu)
    cosnu = np.cos(nu)
    sini = np.sin(i)
    cosi = np.cos(i)
    sinw = np.sin(w)
    cosw = np.cos(w)
    sinOmega = np.sin(Omega)
    cosOmega = np.cos(Omega)

    # get distance in PQW frame
    eSq = e * e
    r = np.divide(a * (1.0 - eSq), 1.0 + e * cosnu)
    x_PQW = r * cosnu
    y_PQW = r * sinnu

    # Rotation matrix terms
    R11 = cosw * cosOmega - sinw * cosi * sinOmega
    R12 = -(sinw * cosOmega + cosw * cosi * sinOmega)
    R21 = cosw * sinOmega + sinw * cosi * cosOmega
    R22 = -sinw * sinOmega + cosw * cosi * cosOmega
    R31 = sinw * sini
    R32 = cosw * sini

    # ECI coords
    X_eci = R11 * x_PQW + R12 * y_PQW
    Y_eci = R21 * x_PQW + R22 * y_PQW
    Z_eci = R31 * x_PQW + R32 * y_PQW

    # Velocity
    coeff = np.sqrt(c.GM * a) / r
    sinE = (sinnu * np.sqrt(1.0 - eSq)) / (1.0 + e * cosnu)
    cosE = (e + cosnu) / (1.0 + e * cosnu)
    local_vx = coeff * (-sinE)
    local_vy = coeff * (np.sqrt(1.0 - eSq) * cosE)

    Xdot_eci = R11 * local_vx + R12 * local_vy
    Ydot_eci = R21 * local_vx + R22 * local_vy
    Zdot_eci = R31 * local_vx + R32 * local_vy

    return X_eci, Y_eci, Z_eci, Xdot_eci, Ydot_eci, Zdot_eci

def ConvertECIToECEF(X_eci, Y_eci, Z_eci, gmst):
    """
    Convert ECI coords to ECEF coords for each point, using gmst in radians.
    """
    X_ecef = X_eci * np.cos(gmst) + Y_eci * np.sin(gmst)
    Y_ecef = -X_eci * np.sin(gmst) + Y_eci * np.cos(gmst)
    Z_ecef = Z_eci
    return X_ecef, Y_ecef, Z_ecef

def ComputeGeodeticLon(X_ecef, Y_ecef):
    """
    Compute longitude from ECEF X/Y.
    """
    return np.arctan2(Y_ecef, X_ecef)

def ComputeGeodeticLat2(X_ecef, Y_ecef, Z_ecef, a, e):
    """
    Computes geodetic latitude from ECEF using Bowring’s method.

    X_ecef, Y_ecef, Z_ecef: ECEF coordinates
    a: semi-major axis (array)
    e: eccentricity (array)

    Returns geodetic latitude in radians.
    """
    asq = a * a
    esq = e * e
    b = a * np.sqrt(1.0 - esq)
    bsq = b * b
    p = np.sqrt(X_ecef * X_ecef + Y_ecef * Y_ecef)
    ep = np.sqrt(asq - bsq) / b
    theta = np.arctan2(a * Z_ecef, b * p)
    sintheta = np.sin(theta)
    costheta = np.cos(theta)

    # This is Bowring’s formula for geodetic latitude
    phi = np.arctan2(
        Z_ecef + ep * ep * b * sintheta ** 3,
        p - esq * a * costheta ** 3
    )

    return phi

