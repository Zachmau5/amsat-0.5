"""
coordinate_conversions.py

This module performs the conversion of satellite orbital data from Keplerian
elements to various coordinate systems used in satellite tracking. It includes:
    • Precession calculations for RAAN and argument of perigee due to Earth’s oblateness.
    • Conversion from Keplerian orbital elements to Earth-Centered Inertial (ECI) coordinates.
    • Conversion from ECI coordinates to Earth-Centered Earth-Fixed (ECEF) coordinates.
    • Conversion of ECEF coordinates to geodetic coordinates (longitude and latitude)
      using Bowring’s method.

The transformations involve a series of rotations using the orbital elements:
    - Inclination (i)
    - Right Ascension of the Ascending Node (Ω)
    - Argument of perigee (w)
and they account for small secular variations (precession) induced by the Earth’s
oblate shape (represented by the J2 constant).
"""

import numpy as np
import constants as c


def RAANPrecession(a, e, i):
    """
    Compute the secular precession of the Right Ascension of the Ascending Node (RAAN)
    due to the Earth's oblateness (J2 effect).

    Parameters:
        a : float or ndarray
            Semi-major axis of the orbit (in meters).
        e : float or ndarray
            Eccentricity of the orbit (dimensionless).
        i : float or ndarray
            Inclination of the orbit (in radians).

    Returns:
        precession : float or ndarray
            RAAN precession rate (radians per second), computed using the formula:

                precession = -1.5 * J2 * sqrt(GM) * (Re^2) * cos(i)
                             ------------------------------------------------
                              a^(7/2) * (1 - e^2)^2

    Explanation:
        This function implements the standard formula for the nodal precession (change
        in RAAN) that arises from the J2 effect — the Earth's equatorial bulge. The
        formula shows that the precession rate is faster for lower orbits (smaller a)
        and depends on the cosine of the inclination.
    """
    eSq = e * e
    precession = np.divide(
        -1.5 * c.J2 * np.sqrt(c.GM) * (c.Re * c.Re) * np.cos(i),
        np.power(a, 3.5) * (1.0 - eSq) * (1.0 - eSq)
    )
    return precession


def ArgPerigeePrecession(a, e, i):
    """
    Compute the secular precession of the argument of perigee due to the Earth's oblateness (J2 effect).

    Parameters:
        a : float or ndarray
            Semi-major axis (in meters).
        e : float or ndarray
            Eccentricity of the orbit (dimensionless).
        i : float or ndarray
            Inclination (in radians).

    Returns:
        precession : float or ndarray
            Argument of perigee precession rate (radians per second), computed as:

                precession = 0.75 * J2 * sqrt(GM) * (Re^2) * (5 sin²(i) - 1)
                             -----------------------------------------------------
                              a^(7/2) * (1 - e^2)^2

    Explanation:
        The function calculates how the perigee rotates within the orbital plane due to
        Earth’s oblateness. The rate depends strongly on the inclination (through sin²(i))
        and decreases with increasing semi-major axis.
    """
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
    Convert Keplerian orbital elements to Earth-Centered Inertial (ECI) coordinates.

    Parameters:
        a       : ndarray
                  Semi-major axis (m).
        e       : ndarray
                  Eccentricity (unitless).
        i       : ndarray
                  Inclination (radians).
        Omega   : ndarray
                  Right Ascension of the Ascending Node (radians).
        w       : ndarray
                  Argument of perigee (radians).
        nu      : ndarray
                  True anomaly (radians).
        time_vec: ndarray
                  Array of time offsets from the TLE epoch (in days).

    Returns:
        X_eci, Y_eci, Z_eci        : ndarray
                                    Cartesian ECI position coordinates (km or m, depending on a).
        Xdot_eci, Ydot_eci, Zdot_eci: ndarray
                                    Velocity components in ECI.

    Process:
      1. Update RAAN and argument of perigee to account for precession:
            - Calculate w_precession using ArgPerigeePrecession.
            - Calculate Omega_precession using RAANPrecession.
            - Adjust w and Omega:  w = w + (time_vec in seconds) * w_precession
                                      Omega = Omega + (time_vec in seconds) * Omega_precession

      2. Pre-calculate sine and cosine for:
            - True anomaly (nu)
            - Inclination (i)
            - Updated w and Omega

      3. Calculate the orbital radius 'r' in the perifocal (PQW) frame:
            r = a*(1 - e^2) / (1 + e*cos(nu))

      4. Express the position in the PQW frame:
            x_PQW = r * cos(nu), y_PQW = r * sin(nu)

      5. Compute the rotation matrix elements to transform from PQW to ECI:
            They combine the rotations around z (for w), x (for i), and z (for Omega).

      6. Apply the rotation matrix to get ECI position:
            [X_eci, Y_eci, Z_eci]^T = Rotation_Matrix * [x_PQW, y_PQW, 0]^T

      7. Compute velocity:
            - A coefficient based on orbital speed: coeff = sqrt(GM * a) / r.
            - Estimate sin(E) and cos(E) indirectly from nu.
            - Compute local velocities (in the orbital plane) and then rotate them
              using the same rotation matrix.

    Explanation:
       This function performs the critical transformation from the orbital elements,
       which naturally define an ellipse in its own plane (PQW), to the three-dimensional
       inertial coordinate frame (ECI) used in further tracking and ground-based predictions.
    """
    # Update argument of perigee for precession due to Earth's oblateness.
    # The time offset is converted from days to seconds.
    w_precession = ArgPerigeePrecession(a, e, i)
    w = w + (time_vec * (24.0 * 3600.0)) * w_precession

    # Similarly, update RAAN for precession.
    Omega_precession = RAANPrecession(a, e, i)
    Omega = Omega + (time_vec * (24.0 * 3600.0)) * Omega_precession

    # Pre-calculate trigonometric functions for true anomaly, inclination, and updated angles.
    sinnu = np.sin(nu)
    cosnu = np.cos(nu)
    sini = np.sin(i)
    cosi = np.cos(i)
    sinw = np.sin(w)
    cosw = np.cos(w)
    sinOmega = np.sin(Omega)
    cosOmega = np.cos(Omega)

    # Calculate orbital radius in the Perifocal (PQW) frame.
    eSq = e * e
    r = np.divide(a * (1.0 - eSq), 1.0 + e * cosnu)
    x_PQW = r * cosnu
    y_PQW = r * sinnu

    # Compute the rotation matrix elements. The rotations are applied in sequence:
    # First, rotate by -w about the Z-axis, then by -i about the X-axis,
    # finally by -Omega about the Z-axis.
    R11 = cosw * cosOmega - sinw * cosi * sinOmega
    R12 = -(sinw * cosOmega + cosw * cosi * sinOmega)
    R21 = cosw * sinOmega + sinw * cosi * cosOmega
    R22 = -sinw * sinOmega + cosw * cosi * cosOmega
    R31 = sinw * sini
    R32 = cosw * sini

    # Rotate the position vector from PQW to ECI using the rotation matrix.
    X_eci = R11 * x_PQW + R12 * y_PQW
    Y_eci = R21 * x_PQW + R22 * y_PQW
    Z_eci = R31 * x_PQW + R32 * y_PQW

    # Calculate the local (orbital plane) velocity components. The 'coeff' provides a factor derived
    # from energy conservation in the orbit.
    coeff = np.sqrt(c.GM * a) / r
    # Using geometric relations: sin(E) and cos(E) are approximated from nu.
    sinE = (sinnu * np.sqrt(1.0 - eSq)) / (1.0 + e * cosnu)
    cosE = (e + cosnu) / (1.0 + e * cosnu)
    local_vx = coeff * (-sinE)
    local_vy = coeff * (np.sqrt(1.0 - eSq) * cosE)

    # Rotate velocity components using the same rotation matrix.
    Xdot_eci = R11 * local_vx + R12 * local_vy
    Ydot_eci = R21 * local_vx + R22 * local_vy
    Zdot_eci = R31 * local_vx + R32 * local_vy

    return X_eci, Y_eci, Z_eci, Xdot_eci, Ydot_eci, Zdot_eci


def ConvertECIToECEF(X_eci, Y_eci, Z_eci, gmst):
    """
    Convert Earth-Centered Inertial (ECI) coordinates to
    Earth-Centered Earth-Fixed (ECEF) coordinates using Greenwich
    Mean Sidereal Time (GMST).

    Parameters:
        X_eci, Y_eci, Z_eci : ndarray
            The position components in ECI coordinates.
        gmst : float or ndarray
            Greenwich Mean Sidereal Time in radians.

    Returns:
        X_ecef, Y_ecef, Z_ecef : ndarray
            The converted ECEF coordinates.

    Explanation:
        The conversion applies a rotation about the Z-axis by the GMST angle
        to account for the Earth's rotation since the epoch.
    """
    X_ecef = X_eci * np.cos(gmst) + Y_eci * np.sin(gmst)
    Y_ecef = -X_eci * np.sin(gmst) + Y_eci * np.cos(gmst)
    Z_ecef = Z_eci
    return X_ecef, Y_ecef, Z_ecef


def ComputeGeodeticLon(X_ecef, Y_ecef):
    """
    Compute geodetic longitude from ECEF X and Y components.

    Parameters:
        X_ecef, Y_ecef : ndarray
            The ECEF X and Y coordinates.

    Returns:
        lon : ndarray (radians)
            Longitude computed using the arctan2 function.

    Explanation:
        Longitude is defined as the angle from the prime meridian to the
        projection of the point onto the equatorial plane.
    """
    return np.arctan2(Y_ecef, X_ecef)


def ComputeGeodeticLat2(X_ecef, Y_ecef, Z_ecef, a, e):
    """
    Compute geodetic latitude from ECEF coordinates using Bowring’s method.

    Parameters:
        X_ecef, Y_ecef, Z_ecef : ndarray
            The ECEF coordinates.
        a : ndarray or float
            The semi-major axis, typically Earth's equatorial radius.
        e : ndarray or float
            The eccentricity of the Earth ellipsoid.

    Returns:
        phi : ndarray
            The geodetic latitude in radians.

    Explanation:
        Bowring’s method is an iterative non-linear formula that accurately converts
        Cartesian ECEF coordinates to geodetic latitude (accounting for the Earth's
        ellipsoidal shape). The method computes an initial estimate (theta) and then adjusts
        it by a factor that depends on the eccentricity and geometry of the Earth.
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

    # Bowring’s formula for geodetic latitude (phi)
    phi = np.arctan2(
        Z_ecef + ep * ep * b * sintheta ** 3,
        p - esq * a * costheta ** 3
    )

    return phi
