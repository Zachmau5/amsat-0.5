"""
constants.py

This module defines various physical and mathematical constants
required for amateur radio satellite tracking. These constants are used
throughout the codebase to convert units, perform coordinate
transformations, and compute orbital parameters using the Keplerian
model.

Constants include:
- Gravitational parameters
- Earth parameters (radius, flattening factors)
- Conversion factors (between degrees and radians, days to seconds)
- The Earth rotation rate (omega_earth)
- A preset number of time points for propagation, and
  initial observer latitude for computations.

All constants are defined using SI units unless otherwise noted.
"""

import numpy as np

# Gravitational constant times the Earth’s mass (mu factor)
# GM has units of m^3/s^2. It is used for calculating orbital velocities
# and the semi-major axis from the mean motion.
GM = 3.986004418e14

# J2 is the second zonal harmonic coefficient for the Earth's gravitational
# field, representing the oblateness (flattening) of the Earth.
J2 = 1.0827e-3

# Re is the Earth's equatorial radius in meters. This parameter is used in
# converting between different coordinate systems (e.g., ECI and ECEF),
# and in computing the satellite's altitude above Earth's surface.
Re = 6.378137e6

# Conversion factors:
deg2rad = np.pi / 180.0    # Convert degrees to radians
rad2deg = 180.0 / np.pi    # Convert radians to degrees
twoPi   = 2.0 * np.pi      # Full circle in radians

# Conversion from days to seconds (there are 24*3600 seconds in one day)
day2sec = 1.0 / (24.0 * 3600.0)

# Number of time points to be used in propagation/prediction grids.
# Adjust this value based on the resolution needed for prediction plots.
num_time_pts = 1000

# Earth's rotation (angular) velocity.
# Originally given in deg/min, converted here to rad/s.
# omega_earth: 0.2506844773746215 (deg/min) converted to rad/s.
omega_earth = 0.2506844773746215 * (deg2rad / 60)

# Default observer latitude (in radians).
# Used perhaps in computing local coordinates or elevation angles.
lat0 = 45.0 * deg2rad

# For clarity, alias Earth's equatorial radius and
# provide Earth's polar radius (which is lower than equatorial).
earthEquatorialRadius = Re
earthPolarRadius = 6.356752e6

