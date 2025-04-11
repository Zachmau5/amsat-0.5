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

# Load TLEs from saved file
tle_dict = ParseTwoLineElementFile("amateur.tle")

# Ground station location (Ogden, Utah)
my_lat = 41.19494
my_lon = -111.94153

# Setup map figure
fig = plt.figure()
ax = fig.add_subplot(111)
myMap = Basemap(
    projection='mill',
    llcrnrlat=-90, urcrnrlat=90,
    llcrnrlon=-180, urcrnrlon=180,
    resolution='c', ax=ax
)

myMap.drawmapboundary(fill_color='white')
myMap.fillcontinents(color='gray', lake_color='black')
myMap.drawcoastlines()
ax.set_zorder(0)
ax.patch.set_facecolor('black')

# Plot the ground station
x_qth, y_qth = myMap(my_lon, my_lat)  # lon, lat
myMap.plot(x_qth, y_qth, 'go', markersize=8, label='My Location')
ax.annotate('Me', xy=(x_qth, y_qth), xytext=(x_qth + 5, y_qth + 5), color='white')

# Global lists to clear dynamic objects per frame
track_lines = []
track_labels = []

def split_segments(lons, lats, max_jump=180):
    segments = []
    start = 0
    for i in range(1, len(lons)):
        if abs(lons[i] - lons[i-1]) > max_jump:
            segments.append((lons[start:i], lats[start:i]))
            start = i
    segments.append((lons[start:], lats[start:]))
    return segments

def animate(ii, selected_tle_dict):
    global track_lines, track_labels

    # Clear previous plot elements
    for ln in track_lines:
        try:
            ln.remove()
        except:
            pass
    track_lines = []

    for label in track_labels:
        try:
            label.remove()
        except:
            pass
    track_labels = []

    date_now = datetime.utcnow()
    latslons_dict = ConvertKepToStateVectors(selected_tle_dict, use_skyfield=False)

    for sat_name in selected_tle_dict:
        arr = latslons_dict[sat_name]
        raw_lons = arr[:, 0]
        raw_lats = arr[:, 1]

        if np.any(np.isnan(raw_lons)) or np.any(np.isnan(raw_lats)):
            print(f"[{sat_name}] ❌ NaNs in lat/lon!")
            continue

        wrapped_lons = raw_lons
        segments = split_segments(wrapped_lons, raw_lats)

        # Plot the satellite's position at the beginning of the trace (first point)
        first_lon = raw_lons[0]
        first_lat = raw_lats[0]
        xx, yy = myMap(first_lon, first_lat)
        pt, = ax.plot(xx, yy, 'r*', markersize=10, zorder=10)
        track_lines.append(pt)

        # Plot the trace for the satellite
        for idx, (seg_lon, seg_lat) in enumerate(segments):
            if len(seg_lon) < 2:
                continue

            x, y = myMap(seg_lon, seg_lat)
            line, = ax.plot(x, y, color='lime', linewidth=2, zorder=5)
            dots, = ax.plot(x, y, 'wo', markersize=2, zorder=6)
            track_lines.extend([line, dots])

        # Add label for satellite
        label = ax.annotate(sat_name, xy=(xx, yy), xytext=(xx + 6, yy + 6),
                            color='yellow', fontsize=9, zorder=11)
        track_labels.append(label)

    ax.set_xlim(myMap.xmin, myMap.xmax)
    ax.set_ylim(myMap.ymin, myMap.ymax)
    plt.title(f"Amateur Satellite Tracking\nUTC: {date_now:%Y-%m-%d %H:%M:%S}")
    fig.canvas.draw()
    fig.canvas.flush_events()

    return track_lines


def runPredictionTool(checkbox_dict, tle_dict):
    selected_tle_dict = {k: tle_dict[k] for k, v in checkbox_dict.items() if v.get() == 1}

    if not selected_tle_dict:
        print("No satellites selected. Exiting.")
        sys.exit(0)

    ani = animation.FuncAnimation(fig, animate, fargs=(selected_tle_dict,),
                                  interval=1000, blit=False, repeat=False)
    plt.legend(loc='lower left', frameon=True, facecolor='grey', edgecolor='white')
    print(f"[DEBUG] Selected satellites: {list(selected_tle_dict.keys())}")
    plt.show()

def SetupWindow(root, tle_dict):
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
    root = tk.Tk()
    SetupWindow(root, tle_dict)
    root.mainloop()
