# amsat
## Features

- **TLE Parsing:** Reads TLE files and extracts orbital parameters (Epoch, Inclination, RAAN, Eccentricity, Argument of Perigee, Mean Anomaly, Mean Motion) for each satellite.
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
  ## Installation

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
    python -m venv venv
    source venv/bin/activate      # For Unix/MacOS
    venv\Scripts\activate         # For Windows
3. **Install Required Packages:**
    ```bash
    pip install -r requirements.txt
  
