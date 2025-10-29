# amsat
## Features
<img width="800" height="470" alt="image" src="https://github.com/user-attachments/assets/2634a2b6-add2-4bc3-a064-322594a1592e" />

<!--- **TLE Parsing:** Reads TLE files and extracts orbital parameters (Epoch, Inclination, RAAN, Eccentricity, Argument of Perigee, Mean Anomaly, Mean Motion) for each satellite.
- **Keplerian Propagation:** Uses Kepler's equations to propagate the satellite's orbit. This includes:
  - Calculating the evolving Mean Anomaly over time.
  - Solving Kepler’s Equation with the Newton-Raphson method to obtain the Eccentric Anomaly.
  - Converting the Eccentric Anomaly to the True Anomaly.
  - Computing the semi-major axis from mean motion using Kepler’s Third Law.
- **Coordinate Conversions:** Transforms orbital coordinates through these steps:
  - **Perifocal (PQW) Frame → Earth-Centered Inertial (ECI):** Applies rotations using the inclination, RAAN, and argument of perigee.
  - **ECI → Earth-Centered Earth-Fixed (ECEF):** Uses Greenwich Mean Sidereal Time (GMST) to account for Earth’s rotation.
  - **ECEF → Geodetic Coordinates:** Converts ECEF coordinates to latitude, longitude, and altitude using methods such as Bowring’s formula.
- **Visualization:** Animates the satellite ground tracks on a global (Miller projection) map and a near-sided perspective projection. It also draws a satellite footprint (coverage area) based on the satellite’s altitude.
- **Graphical User Interface:** A Tkinter-based GUI allows you to select satellites from the loaded TLE file and run the tracking prediction.
- **Optional TLE Fetching:** A module can download updated TLE data from public sources (e.g., CelesTrak).
## File Structure

- **constants.py:**
  Defines physical and mathematical constants (e.g., Earth’s gravitational parameter, Earth’s radius, conversion factors).

- **coordinate_conversions.py:**
  Contains functions to perform coordinate transformations:
  - `ConvertKeplerToECI`: Converts orbital elements from the perifocal (PQW) frame to the Earth-Centered Inertial (ECI) system.
  - `ConvertECIToECEF`: Converts ECI coordinates to Earth-Centered Earth-Fixed (ECEF) coordinates using GMST.
  - `ComputeGeodeticLon` and `ComputeGeodeticLat2`: Convert ECEF coordinates to geodetic coordinates (longitude and latitude).

- **TimeRoutines.py:**
  Provides utilities for time conversion:
  - `ConvertLocalTimeToUTC`: Converts a local time string to a UTC time string.
  - `GenerateTimeVec`: Generates a time vector (in fractional days) between specified start and end times.
  - `Date_to_nth_day` and `Nth_day_to_date`: Convert between date strings and fractional day-of-year values.
  - `JdayInternal`: Converts an array of [year, month, day, hour, min, sec] into Julian Dates.
  - `CalculateGMSTFromJD`: Computes Greenwich Mean Sidereal Time (GMST) from Julian Dates.

- **tle_to_kep.py:**
  Converts parsed TLE data into evolving Keplerian elements (semi-major axis, eccentricity, inclination, RAAN, argument of perigee, true anomaly, eccentric anomaly, etc.) for a specified time range. Uses the Newton-Raphson method to solve Kepler’s Equation.

- **keplerian_parser.py:**
  Parses a TLE text file and returns a dictionary where each satellite name maps to an array of orbital elements: sat_name: {[epoch_year, epoch_days, inclination, RAAN, eccentricity, arg_perigee, mean_anomaly, mean_motion, drag]}

- **kep_to_state.py:**
Converts the Keplerian elements produced by tle_to_kep.py into state vectors (position and velocity). This includes:
- Computing the satellite’s position in ECI coordinates.
- Converting ECI to ECEF using GMST.
- Converting ECEF to geodetic coordinates (latitude, longitude, altitude).

- **fetch_tle.py:**
(Optional) Downloads TLE data from an online source (e.g., CelesTrak) and saves it to a local file.

- **sgp4_predictor.py / tle_sgp4_predictor.py:**
(Optional) Provide alternative propagation methods using the SGP4 model to account for perturbations.

- **skyfield_predictor.py:**
(Optional) Uses the Skyfield library to load and propagate satellite positions from TLE data.

- **main.py:**
The main application that:
- Loads TLE data.
- Provides a Tkinter-based GUI for selecting satellites.
- Sets up animated maps (global view and near-sided perspective) to visualize satellite ground tracks and footprints.
  ## Installation-->

### Requirements
- Python 3.7+
- numpy
- scipy
- matplotlib
- Basemap (e.g., installed via conda from conda-forge)
- tkinter (bundled with Python)
- pytz
- (Optional) skyfield

### Installation Steps

1. **Clone the Repository:**
   ```bash
   git clone <repository_url>
   cd <repository_directory>

2. **Create and Activate Virtual Environment:**
   ```bash
   conda env create -f amsat.yml
   conda activate amsat

3. **Run Tracking Software:**
  ```bash
  python3 main_gs232.py



##  Antenna Boresight Wizard

A standalone Tkinter-based tool for aligning the Yaesu G-5500DC/GS-232B antenna rotator system before satellite tracking.

### Overview

This tool performs a structured **boresight sequence** independent of the main tracking GUI:
1. **Point to True North:**
   Sends `W000 000` and allows the user to verify azimuth alignment.
2. **Point to Due South:**
   Sends `W180 000` and allows confirmation of travel range.
3. **Full 360° Sweep (Speed-Based):**
   Uses rotation speed commands (`X1`–`X4`) and a continuous clockwise rotation (`R`) to confirm smooth motion and limits.
4. **Stage / Park:**
   Lets the user select a fixed azimuth (0–345° in 15° steps) to park the array before exit.

### Usage

Run independently from the repository root:
```bash
python3 calibration_wizard.py
```

### Simulation Mode
If no GS-232B hardware is connected, check **“Simulate (no hardware)”** during the sweep step.
This bypasses serial polling and emulates rotation to verify UI behavior.



---

##  Repository Structure

```
amsat/
├── main_gs232b.py           # Main tracking GUI and
├── calibration_wizard.py    # Standalone GS-232B
├── FILL ME IN WHEN I'VE DECIDED TO CLEAN UP MY MESS...
```



