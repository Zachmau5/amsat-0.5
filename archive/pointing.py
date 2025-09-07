 
from __future__ import annotations
import math

# WGS-84 constants
_A  = 6378137.0                    # semi-major axis [m]
_F  = 1.0 / 298.257223563          # flattening
_E2 = _F * (2.0 - _F)              # first eccentricity^2

def geodetic_to_ecef(lat_deg: float, lon_deg: float, h_m: float) -> tuple[float, float, float]:
    """Convert geodetic (deg, deg, m) to ECEF (m)."""
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sinp = math.sin(lat); cosp = math.cos(lat)
    sinl = math.sin(lon); cosl = math.cos(lon)
    N = _A / math.sqrt(1.0 - _E2 * sinp*sinp)
    x = (N + h_m) * cosp * cosl
    y = (N + h_m) * cosp * sinl
    z = (N*(1.0 - _E2) + h_m) * sinp
    return x, y, z

def ecef_to_enu(dx: float, dy: float, dz: float, gs_lat_deg: float, gs_lon_deg: float) -> tuple[float, float, float]:
    """Rotate ECEF delta vector into local ENU frame at ground site (deg inputs)."""
    lat = math.radians(gs_lat_deg)
    lon = math.radians(gs_lon_deg)
    sinp = math.sin(lat); cosp = math.cos(lat)
    sinl = math.sin(lon); cosl = math.cos(lon)
    e = -sinl*dx + cosl*dy
    n = -sinp*cosl*dx - sinp*sinl*dy + cosp*dz
    u =  cosp*cosl*dx + cosp*sinl*dy + sinp*dz
    return e, n, u

def az_el_from_enu(e: float, n: float, u: float) -> tuple[float, float]:
    """Compute (azimuth, elevation) from ENU meters."""
    az = math.degrees(math.atan2(e, n)) % 360.0
    el = math.degrees(math.atan2(u, math.hypot(e, n)))
    return az, el

def az_el_from_geodetic(sat_lat_deg: float, sat_lon_deg: float, sat_alt_km: float,
                        gs_lat_deg: float, gs_lon_deg: float, gs_h_m: float = 0.0) -> tuple[float, float]:
    """Azimuth/Elevation from site (deg,deg,m) to satellite (deg,deg,km)."""
    xs, ys, zs = geodetic_to_ecef(sat_lat_deg, sat_lon_deg, sat_alt_km*1000.0)
    xg, yg, zg = geodetic_to_ecef(gs_lat_deg, gs_lon_deg, gs_h_m)
    e, n, u = ecef_to_enu(xs - xg, ys - yg, zs - zg, gs_lat_deg, gs_lon_deg)
    return az_el_from_enu(e, n, u)

def az_el_range_from_geodetic(sat_lat_deg: float, sat_lon_deg: float, sat_alt_km: float,
                              gs_lat_deg: float, gs_lon_deg: float, gs_h_m: float = 0.0) -> tuple[float, float, float]:
    """Azimuth/Elevation/Slant-Range (km) from site to satellite."""
    xs, ys, zs = geodetic_to_ecef(sat_lat_deg, sat_lon_deg, sat_alt_km*1000.0)
    xg, yg, zg = geodetic_to_ecef(gs_lat_deg, gs_lon_deg, gs_h_m)
    dx, dy, dz = xs - xg, ys - yg, zs - zg
    e, n, u = ecef_to_enu(dx, dy, dz, gs_lat_deg, gs_lon_deg)
    az, el = az_el_from_enu(e, n, u)
    rng_km = math.sqrt(dx*dx + dy*dy + dz*dz) / 1000.0
    return az, el, rng_km
