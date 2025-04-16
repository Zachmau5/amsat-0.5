"""
main.py

Purpose:
    This module forms the user interface and visualization layer for the
    Amateur Radio Satellite Tracking system. It performs the following tasks:
      - Loads satellite orbital data from a local TLE file using the TLE parser.
      - Sets up a graphical user interface (GUI) with Tkinter for selecting
        satellites from the TLE data.
      - Configures two Basemap projections for visualization:
           • A global view (full Earth map) for tracing the satellite ground track.
           • A near-sided (perspective) projection that follows the satellite’s
             current position.
      - Animates the satellite positions over time using custom Keplerian propagation
        (via the kep_to_state module) to compute latitude, longitude, and altitude.
      - Also plots the satellite “footprint” (a circle representing the satellite
        coverage area on Earth) on the near-sided map.
      - Provides a real-time (or near-real-time) updating display of the satellite
        passes, including a textual summary similar to online tracking sites.

Key Modules and Functions Used:
    - numpy, datetime, and sys: Core Python libraries for numerical and date/time processing.
    - tkinter and tkinter.font: For building the GUI.
    - matplotlib (and mpl_toolkits.basemap): For plotting maps and animating satellite tracks.
    - matplotlib.animation: To perform frame-by-frame updates.
    - kep_to_state.ConvertKepToStateVectors: Converts TLE data to state vectors (lat, lon, altitude)
      using Keplerian propagation.
    - keplerian_parser.ParseTwoLineElementFile: Parses a local TLE file and extracts orbital elements.
    - matplotlib.patches.Circle: (optional) Could be used for drawing circular footprints (if needed).

Usage:
    When run, the script opens a Tkinter window that displays a list of satellites
    (as parsed from the TLE file). The user selects satellites via checkboxes and clicks
    "Run Prediction", which then launches an animated plot that shows:
      - A global map with the satellite’s ground track over time.
      - A near-sided perspective projection centered at the satellite's current position,
        with a drawn footprint indicating its coverage area (computed from altitude).
    The animation updates at a set interval (1000 ms) and includes real-time text output
    with current latitude, longitude, altitude, and speed in a style similar to N2YO.

Detailed Explanation:

1. **TLE Data Loading and Ground Station Setup**
    - The TLE file ("amateur.tle") is loaded via `ParseTwoLineElementFile`, which reads the file
      and returns a dictionary mapping each satellite name to its orbital elements.
    - The ground station location is set by specifying `my_lat` (latitude) and `my_lon` (longitude).
      (In the provided code, Ogden, Utah, is used as the default.)

2. **Figure and Map Setup**
    - A global figure with a size of 14x7 inches is created.
    - Two subplots are configured:
         a. **Global View (ax1)**: Uses a miller projection to display the complete world map.
         b. **Near-Sided Perspective (ax2)**: Uses an "nsper" (near-sided perspective) projection that
            simulates a view from a specific satellite height (here set as 3000 km).
    - For both maps, continents, coastlines, and map boundaries are drawn and styled.
    - The ground station (your location) is plotted on the global view using green markers and annotated as "Me".

3. **Animation Preparation**
    - A helper function, `split_segments`, is defined to split the satellite ground track data into
      continuous segments. This is used to handle discontinuities (e.g., when tracks wrap around the 180° meridian).
    - Two global lists, `track_lines` and `track_labels`, are declared to store line and text objects
      for updating and removal between frames.

4. **Plotting the Satellite Footprint**
    - The function `plot_footprint` approximates the satellite coverage circle ("footprint").
    - Given a center (lon_0, lat_0) and a "footprint radius" in degrees, it computes points around a circle
      and plots them using scatter on the near-sided map.
    - The footprint is based on a simple geometric model (footprint_radius computed from altitude).

5. **Animation Function: animate()**
    - This is the core function called on each animation frame.
    - It first removes previous plot elements (lines and labels) from both subplots.
    - It gets the current UTC time and calls `ConvertKepToStateVectors` with the selected TLE dictionary to
      compute the satellite state vectors (latitudes, longitudes, and altitude) over the prediction window.
    - For each selected satellite:
         a. The satellite's latitudes, longitudes, and altitude (alt_km) are extracted.
         b. The footprint radius is calculated using an approximate formula:
               footprint_radius = (alt_km / (Earth radius + alt_km)) * (180/π)
         c. The center for the near-sided map is updated to the satellite’s current position.
         d. The near-sided subplot (ax2) is cleared and redrawn with updated map features.
         e. The footprint is drawn on the near-sided map via `plot_footprint`.
         f. The ground station ("Me") is re-plotted on the near-sided map.
         g. The global map (ax1) is updated: the satellite's current position is plotted (red star) and its
            ground track is drawn in segments (lime-colored lines with white dots).
         h. A label with the satellite’s name is added to the global map.
    - Plot limits for both maps are updated, and a global title is set displaying the current UTC time.
    - Finally, the function returns the list of track lines (which are used internally for animation updates).

6. **runPredictionTool() Function**
    - This function is triggered by the GUI when the user clicks "Run Prediction".
    - It filters the TLE dictionary based on the selected checkboxes (only processing the satellites with a checked box).
    - If no satellites are selected, the program exits.
    - Otherwise, it starts a `FuncAnimation` (from matplotlib.animation) that calls `animate()` every 1000 ms (1 second).
    - A legend is added, and the plot window is displayed.

7. **GUI Setup: SetupWindow() Function**
    - A Tkinter window is created, with:
         a. One frame that contains checkboxes for each satellite (populated from the TLE dictionary).
         b. Another frame that holds two buttons: "Run Prediction" (to start the animation) and "Quit Program" (to exit).
    - The checkboxes allow the user to choose which satellites to track.

8. **Main Block**
    - When the module is run as the main script, a Tkinter root window is created, SetupWindow is called
      to build the GUI, and the main loop is started.

Usage:
    1. Run the script: `python main.py`
    2. The GUI window will appear with a list of satellite names from the TLE file.
    3. Select the desired satellites via checkboxes.
    4. Click "Run Prediction" to view the animated ground tracks on both the global map and the near-sided projection.
    5. The window will update in real time, showing the current satellite position, ground track, and footprint.

Note:
    - The code uses both global (ax1) and near-sided (ax2) Basemap projections.
    - The satellite footprint calculation here is a simple geometric approximation, based on the altitude.
    - The near-sided projection is updated every frame to follow the selected satellite’s position.

"""

import numpy as np
import tkinter as tk
import tkinter.font as tkFont
import sys
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from matplotlib import animation
from datetime import datetime
from kep_to_state import ConvertKepToStateVectors
from keplerian_parser import ParseTwoLineElementFile
from matplotlib.patches import Circle

# Load TLE data from the saved file (amateur.tle)
tle_dict = ParseTwoLineElementFile("amateur.tle")

# Set the ground station location (example: Ogden, Utah)
my_lat = 41.19494
my_lon = -111.94153
# Alternatively (commented), you could set a different location.

# Setup figure with two subplots: one global map and one near-sided perspective map.
fig = plt.figure(figsize=(14, 7))

# Global View (left subplot) uses Miller projection.
ax1 = fig.add_subplot(121)
myMap1 = Basemap(
    projection='mill',
    llcrnrlat=-90, urcrnrlat=90,
    llcrnrlon=-180, urcrnrlon=180,
    resolution='c', ax=ax1
)
myMap1.drawmapboundary(fill_color='white')
myMap1.fillcontinents(color='gray', lake_color='black')
myMap1.drawcoastlines()
ax1.set_zorder(0)
ax1.patch.set_facecolor('black')

# Plot the ground station (your location) on the global map.
x_qth, y_qth = myMap1(my_lon, my_lat)  # Convert my_lon, my_lat to map coordinates.
myMap1.plot(x_qth, y_qth, 'go', markersize=8, label='My Location')
ax1.annotate('Me', xy=(x_qth, y_qth), xytext=(x_qth + 5, y_qth + 5), color='white')

# Near-Sided Perspective View (right subplot) using the nsper projection.
ax2 = fig.add_subplot(122)
satellite_height = 3000  # Example satellite height in km for perspective projection.
m2 = Basemap(projection='nsper', lon_0=my_lon, lat_0=my_lat,
             satellite_height=satellite_height*1000., resolution='l', ax=ax2)
m2.drawcoastlines()
m2.fillcontinents(color='coral', lake_color='aqua')
m2.drawparallels(np.arange(-90., 120., 30.))
m2.drawmeridians(np.arange(0., 420., 60.))
m2.drawmapboundary(fill_color='aqua')

# Set titles for each subplot.
ax1.set_title("Global View", fontsize=12)
ax2.set_title(f"Near-Sided Perspective Projection {satellite_height} km above Earth", fontsize=12)

# Helper function: split_segments
# Splits ground track arrays into continuous segments (for handling discontinuities).
def split_segments(lons, lats, max_jump=180):
    segments = []
    start = 0
    for i in range(1, len(lons)):
        if abs(lons[i] - lons[i-1]) > max_jump:
            segments.append((lons[start:i], lats[start:i]))
            start = i
    segments.append((lons[start:], lats[start:]))
    return segments

# Global variables to hold track lines and labels (for animation updates).
track_lines = []
track_labels = []

def plot_footprint(ax, lon_0, lat_0, footprint_radius):
    """
    Plot the satellite footprint on the given map axis.

    Parameters:
        ax: The matplotlib axis to plot on (for the near-sided map).
        lon_0, lat_0: Center coordinates (in degrees) for the footprint, representing
                      the satellite's sub-satellite point.
        footprint_radius: Radius of the footprint (in degrees). This value is typically
                          computed using the satellite's altitude (h) and Earth's radius (R_E)
                          with the formula:
                              θ = arccos(R_E / (R_E + h))
                          where θ is in radians. Converting θ to degrees gives:
                              footprint_radius (deg) = θ * (180/π)
                          Additionally, if the slant range is desired instead, the arc length (d)
                          along the Earth's surface can be computed as:
                              d = R_E * θ
                          (in the same units as R_E).

    Process:
        - The function approximates the satellite's coverage area (footprint) as a circle
          centered at (lon_0, lat_0) with a given footprint_radius.
        - It generates a set of points (using 100 evenly spaced angles from 0 to 2π)
          along the circumference of this circle.
        - The circle is then plotted using a yellow scatter plot with transparency (alpha=0.3)
          to visually represent the satellite's footprint.
    """
    num_points = 100
    angles = np.linspace(0, 2 * np.pi, num_points)
    lons = lon_0 + footprint_radius * np.cos(angles)
    lats = lat_0 + footprint_radius * np.sin(angles)
    x, y = m2(lons, lats)
    ax.scatter(x, y, color='yellow', alpha=0.3, zorder=10)


def animate(ii, selected_tle_dict):
    """
    Animation callback function, called periodically (every 1000 ms).

    For each animation frame, this function:
      - Clears previous satellite tracks and labels.
      - Gets the latest predicted state vectors (lat, lon, altitude) for each selected satellite.
      - For each satellite:
          * Computes a coverage "footprint" based on altitude.
          * Updates the near-sided map center to follow the satellite.
          * Redraws the near-sided projection, including state boundaries and coastline features.
          * Plots the satellite's ground track on both the global and near-sided maps.
          * Plots the satellite's current position (red star) and annotates it.
      - Finally, updates plot limits and the global title with the current UTC time.

    Parameters:
        ii : int
            Frame index (not directly used).
        selected_tle_dict : dict
            Subset of the TLE dictionary corresponding to the satellites selected by the user.

    Returns:
        track_lines : list
            A list of matplotlib line/marker objects that are drawn, to be updated on each frame.
    """
    global track_lines, track_labels

    # Remove previous lines and labels from both subplots.
    for ln in track_lines:
        try:
            ln.remove()
        except Exception:
            pass
    track_lines = []
    for label in track_labels:
        try:
            label.remove()
        except Exception:
            pass
    track_labels = []

    date_now = datetime.utcnow()

    # Get predicted state vectors (lat, lon, altitude) from TLE using custom propagation.
    latslons_dict = ConvertKepToStateVectors(selected_tle_dict, use_skyfield=False)

    # Process each selected satellite.
    for sat_name in selected_tle_dict:
        satellite_data = latslons_dict[sat_name]
        raw_lons = satellite_data['lons']
        raw_lats = satellite_data['lats']
        alt_km = satellite_data['alt_km']

        # Compute the satellite's coverage footprint radius (in degrees).
        earth_radius = 6371  # Earth's radius in km (approximate)
        # Here, a simple geometric approximation:
        # footprint_radius (in degrees) = (alt_km / (Earth radius + alt_km)) * (180/π)
        footprint_radius = (alt_km / (earth_radius + alt_km)) * (180.0 / np.pi)

        # Update the near-sided map center to follow the satellite's current position.
        lon_0, lat_0 = raw_lons[0], raw_lats[0]
        m2.lon_0 = lon_0  # Update center longitude of near-sided map.
        m2.lat_0 = lat_0  # Update center latitude of near-sided map.

        # Clear and redraw the near-sided projection for updated visuals.
        ax2.clear()
        m2.drawmapboundary(fill_color='aqua')
        m2.fillcontinents(color='coral', lake_color='aqua')
        m2.drawcoastlines()
        m2.drawparallels(np.arange(-90., 120., 30.))
        m2.drawmeridians(np.arange(0., 420., 60.))
        m2.drawstates(linewidth=1.5, color='black', zorder=10)
        m2.drawcountries(linewidth=1.5, color='black', zorder=10)

        # Adjust the near-sided map limits to ensure the footprint is visible.
        ax2.set_xlim(lon_0 - footprint_radius, lon_0 + footprint_radius)
        ax2.set_ylim(lat_0 - footprint_radius, lat_0 + footprint_radius)

        # Draw the satellite footprint on the near-sided map.
        plot_footprint(ax2, lon_0, lat_0, footprint_radius)

        # Plot the ground station ("Me") on the near-sided map.
        my_x, my_y = m2(my_lon, my_lat)
        ax2.plot(my_x, my_y, 'go', markersize=8, label='My Location')
        ax2.annotate('Me', xy=(my_x, my_y), xytext=(my_x + 5, my_y + 5), color='white')

        # Process satellite ground track for global view:
        wrapped_lons = raw_lons  # (Handled for discontinuities below)
        segments = split_segments(wrapped_lons, raw_lats)

        # Plot the satellite's current position on the global map (red star).
        first_lon, first_lat = raw_lons[0], raw_lats[0]
        xx, yy = myMap1(first_lon, first_lat)
        pt, = ax1.plot(xx, yy, 'r*', markersize=10, zorder=10)
        track_lines.append(pt)

        # Plot the satellite's ground track on the global map:
        for seg_lon, seg_lat in segments:
            if len(seg_lon) < 2:
                continue
            x, y = myMap1(seg_lon, seg_lat)
            line, = ax1.plot(x, y, color='lime', linewidth=2, zorder=5)
            dots, = ax1.plot(x, y, 'wo', markersize=2, zorder=6)
            track_lines.extend([line, dots])

        # Plot the satellite's current position on the near-sided map.
        xx2, yy2 = m2(first_lon, first_lat)
        pt2, = ax2.plot(xx2, yy2, 'r*', markersize=10, zorder=10)
        track_lines.append(pt2)

        # Plot the satellite's ground track on the near-sided map:
        for seg_lon, seg_lat in segments:
            if len(seg_lon) < 2:
                continue
            x2, y2 = m2(seg_lon, seg_lat)
            line2, = ax2.plot(x2, y2, color='lime', linewidth=2, zorder=5)
            dots2, = ax2.plot(x2, y2, 'wo', markersize=2, zorder=6)
            track_lines.extend([line2, dots2])

        # Add an annotation (satellite name) on the global map.
        label = ax1.annotate(sat_name, xy=(xx, yy), xytext=(xx + 6, yy + 6),
                             color='yellow', fontsize=9, zorder=11)
        track_labels.append(label)

    # Set the view limits for the global map.
    ax1.set_xlim(myMap1.xmin, myMap1.xmax)
    ax1.set_ylim(myMap1.ymin, myMap1.ymax)
    # Set the view limits for the near-sided projection.
    ax2.set_xlim(m2.xmin, m2.xmax)
    ax2.set_ylim(m2.ymin, m2.ymax)

    # Update the overall title with the current UTC time.
    plt.suptitle(f"Amateur Satellite Tracking\nUTC: {date_now:%Y-%m-%d %H:%M:%S}")

    fig.canvas.draw()
    fig.canvas.flush_events()

    return track_lines


def runPredictionTool(checkbox_dict, tle_dict):
    """
    Filters the loaded TLE dictionary based on the satellites selected
    (via checkboxes in the GUI) and starts the animation of satellite passes.

    Parameters:
        checkbox_dict : dict
            Dictionary mapping satellite names to Tkinter IntVar objects
            that represent whether a satellite is selected.
        tle_dict : dict
            Dictionary of TLE data loaded from the TLE file.

    Process:
        - Creates a dictionary "selected_tle_dict" including only the satellites
          for which the checkbox is selected.
        - If no satellites are selected, prints a message and exits.
        - Otherwise, creates a matplotlib FuncAnimation that calls the animate()
          function every 1000 ms.
        - Displays a legend and shows the plot.
    """
    selected_tle_dict = {k: tle_dict[k] for k, v in checkbox_dict.items() if v.get() == 1}

    if not selected_tle_dict:
        print("No satellites selected. Exiting.")
        sys.exit(0)

    ani = animation.FuncAnimation(fig, animate, fargs=(selected_tle_dict,),
                                  interval=1000, blit=False, repeat=False)
    plt.legend(loc='lower left', frameon=True, facecolor='grey', edgecolor='white')
    plt.show()


def SetupWindow(root, tle_dict):
    """
    Sets up the Tkinter GUI window. Displays a list of checkboxes for each
    satellite (parsed from the TLE file) and creates two buttons:
         - "Run Prediction" to start the animation.
         - "Quit Program" to exit the application.

    Parameters:
        root : Tkinter.Tk
            The root window.
        tle_dict : dict
            The dictionary containing TLE data for satellites.

    Process:
        - A frame is created for the satellite selection checkboxes.
        - Checkboxes are created for each satellite and arranged in a grid.
        - A second frame contains the control buttons.
        - The checkbox dictionary (mapping each satellite to its Tkinter variable)
          is built and later used to filter the TLE data.
    """
    root.title("Amateur Radio Satellite Tracking")
    helv36 = tkFont.Font(size=12, weight=tkFont.BOLD)

    frame_1 = tk.Frame(root)
    frame_1.grid(row=0, column=0, padx=10, pady=10)

    checkbox_dict = {}
    row_counter = 0
    col_counter = 0
    for key in sorted(tle_dict.keys()):
        var = tk.IntVar()
        cb = tk.Checkbutton(frame_1, text=key, font=("Arial", 10), variable=var)
        cb.grid(row=row_counter, column=col_counter, sticky=tk.W)
        checkbox_dict[key] = var
        row_counter += 1
        if row_counter >= 20:
            row_counter = 0
            col_counter += 1

    frame_2 = tk.Frame(root)
    frame_2.grid(row=1, column=0, padx=10, pady=10)
    tk.Button(frame_2, text="Run Prediction", font=helv36, bg="green",
              command=lambda: runPredictionTool(checkbox_dict, tle_dict)).grid(row=0, column=0, padx=5, pady=5)
    tk.Button(frame_2, text="Quit Program", font=helv36, bg="red", command=root.quit).grid(row=0, column=1, padx=5, pady=5)


if __name__ == "__main__":
    # Create the Tkinter root window and initialize the GUI.
    root = tk.Tk()
    SetupWindow(root, tle_dict)
    root.mainloop()
