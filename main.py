import numpy as np
import tkinter as tk
import tkinter.font as tkFont
import sys
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from matplotlib import animation
from datetime import datetime

# Import from your local modules
from keplerian_parser import ParseTwoLineElementFile
from kep_to_state import ConvertKepToStateVectors

my_lat = 41.19494     # degrees North
my_lon = -111.94153   # degrees East (negative for West)


fig = plt.figure()
ax = fig.add_subplot(111)
myMap = Basemap(
    projection='mill',
    llcrnrlat=-90, urcrnrlat=90,
    llcrnrlon=-180, urcrnrlon=180,
    resolution='c', ax=ax
)
myMap.drawparallels(np.arange(-90, 91, 30), labels=[1,0,0,0])
myMap.drawmeridians(np.arange(-180, 181, 60), labels=[0,0,0,1])
myMap.bluemarble()
myMap.drawcoastlines()

# Plot ground station
x_qth, y_qth = myMap(my_lon, my_lat)
myMap.plot(x_qth, y_qth, 'go', markersize=8, label='My Location')  # green dot
ax.annotate('Me', xy=(x_qth, y_qth), xytext=(x_qth + 5, y_qth + 5), color='white')


# We'll hold line objects so we can remove them each frame
track_lines = []

def split_segments(lons, lats, max_jump=180):
    """
    Splits the array into segments if consecutive longitudes differ by more than max_jump degrees.
    Returns list of (seg_lons, seg_lats) tuples.
    """
    segments = []
    start = 0
    for i in range(1, len(lons)):
        if abs(lons[i] - lons[i-1]) > max_jump:
            segments.append((lons[start:i], lats[start:i]))
            start = i
    segments.append((lons[start:], lats[start:]))
    return segments

def animate(ii, selected_tle_dict):
    global track_lines
    # Remove older lines
    for ln in track_lines:
        try:
            ln.remove()
        except:
            pass
    track_lines = []

    # Convert TLE -> lat/lon for each chosen sat
    latslons_dict = ConvertKepToStateVectors(selected_tle_dict)
    date_now = datetime.utcnow()

    for sat_name in selected_tle_dict:
        arr = latslons_dict[sat_name]
        raw_lons = arr[:,0]
        raw_lats = arr[:,1]

        # 1) unwrap
        unwrapped_lons = np.degrees(np.unwrap(np.radians(raw_lons)))
        # 2) segments
        segments = split_segments(unwrapped_lons, raw_lats)
        # 3) for each segment, re-wrap to [-180,180]
        for seg_lon, seg_lat in segments:
            seg_lon_wrapped = ((seg_lon + 180) % 360) - 180
            x, y = myMap(seg_lon_wrapped, seg_lat)
            line, = ax.plot(x, y, 'b-', linewidth=2)
            track_lines.append(line)

        # final point marker
        last_lon = raw_lons[-1]
        last_lat = raw_lats[-1]
        last_lon_wrapped = ((last_lon + 180) % 360) - 180
        xx, yy = myMap(last_lon_wrapped, last_lat)
        pt, = ax.plot(xx, yy, 'ro', markersize=5)
        track_lines.append(pt)
        # annotation
        ax.annotate(sat_name, xy=(xx, yy), xytext=(xx+5, yy+5), color='yellow')

    plt.title(f"Amateur Satellite Tracking\nUTC: {date_now:%Y-%m-%d %H:%M:%S}")
    return track_lines

def runPredictionTool(checkbox_dict, tle_dict):
    # Collect selected satellites
    selected_tle_dict = {}
    for k, v in checkbox_dict.items():
        if v.get() == 1:
            selected_tle_dict[k] = tle_dict[k]
    if not selected_tle_dict:
        print("No satellites selected. Exiting.")
        sys.exit(0)

    ani = animation.FuncAnimation(fig, animate, fargs=(selected_tle_dict,),
                                  interval=1000, blit=False, repeat=False)
    plt.legend(loc='lower left', frameon=True, facecolor='black', edgecolor='white')

    plt.show()

def SetupWindow(root):
    root.title("Amateur Radio Satellite Tracking")
    helv36 = tkFont.Font(size=12, weight=tkFont.BOLD)

    # parse TLE
    tle_dict = ParseTwoLineElementFile()

    frame_1 = tk.Frame(root)
    frame_1.grid(row=0, column=0, padx=10, pady=10)

    checkbox_dict = {}
    row_counter = 0
    col_counter = 0
    # Sort to have consistent ordering
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
    run_btn = tk.Button(frame_2, text="Run Prediction", font=helv36, bg="green",
                        command=lambda: runPredictionTool(checkbox_dict, tle_dict))
    run_btn.grid(row=0, column=0, padx=5, pady=5)
    quit_btn = tk.Button(frame_2, text="Quit Program", font=helv36, bg="red",
                         command=root.quit)
    quit_btn.grid(row=0, column=1, padx=5, pady=5)

if __name__ == "__main__":
    root = tk.Tk()
    SetupWindow(root)
    root.mainloop()
