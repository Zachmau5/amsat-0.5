# import numpy as np
# import tkinter as tk
# import tkinter.font as tkFont
# import sys
# import matplotlib.pyplot as plt
# from mpl_toolkits.basemap import Basemap
# from matplotlib import animation
# from datetime import datetime
#
# from kep_to_state import ConvertKepToStateVectors
# from keplerian_parser import ParseTwoLineElementFile
#
# # Load TLEs from saved file
# tle_dict = ParseTwoLineElementFile("amateur.tle")
#
# # Ground station location (Ogden, Utah)
# my_lat = 41.19494
# my_lon = -111.94153
#
# # Setup map figure
# fig = plt.figure()
# ax = fig.add_subplot(111)
# myMap = Basemap(
#     projection='mill',
#     llcrnrlat=-90, urcrnrlat=90,
#     llcrnrlon=-180, urcrnrlon=180,
#     resolution='c', ax=ax
# )
# #
# myMap.drawmapboundary(fill_color='white')
# myMap.fillcontinents(color='gray', lake_color='black')
# myMap.drawcoastlines()
# ax.set_zorder(0)
# ax.patch.set_facecolor('black')
# #
# # myMap.bluemarble(scale=0.5)  # 0.2, 0.5, or 1.0
# # myMap.drawcoastlines()
# # myMap.drawcountries()
# # myMap.drawrivers()
#
#
#
# # Plot the ground station
# x_qth, y_qth = myMap(my_lon, my_lat)  # lon, lat
# myMap.plot(x_qth, y_qth, 'go', markersize=8, label='My Location')
# ax.annotate('Me', xy=(x_qth, y_qth), xytext=(x_qth + 5, y_qth + 5), color='white')
#
# # Global lists to clear dynamic objects per frame
# track_lines = []
# track_labels = []
#
# def split_segments(lons, lats, max_jump=180):
#     segments = []
#     start = 0
#     for i in range(1, len(lons)):
#         if abs(lons[i] - lons[i-1]) > max_jump:
#             segments.append((lons[start:i], lats[start:i]))
#             start = i
#     segments.append((lons[start:], lats[start:]))
#     return segments
#
# def animate(ii, selected_tle_dict):
#     global track_lines, track_labels
#
#     # Clear previous plot elements
#     for ln in track_lines:
#         try:
#             ln.remove()
#         except:
#             pass
#     track_lines = []
#
#     for label in track_labels:
#         try:
#             label.remove()
#         except:
#             pass
#     track_labels = []
#
#     # Compute new tracks
#     # latslons_dict = ConvertKepToStateVectors(selected_tle_dict)
#     date_now = datetime.utcnow()
#     latslons_dict = ConvertKepToStateVectors(selected_tle_dict, use_skyfield=False)
#
#     for sat_name in selected_tle_dict:
#         arr = latslons_dict[sat_name]
#         raw_lons = arr[:, 0]
#         raw_lats = arr[:, 1]
#
#         # # 🚨 Debugging prints
#         # print(f"[{sat_name}] ΔLon: {raw_lons[-1] - raw_lons[0]:.4f}°, ΔLat: {raw_lats[-1] - raw_lats[0]:.4f}°")
#         # print(f"[{sat_name}] Lon min/max: {raw_lons.min():.2f} / {raw_lons.max():.2f}")
#         # print(f"[{sat_name}] Lat min/max: {raw_lats.min():.2f} / {raw_lats.max():.2f}")
#         if np.any(np.isnan(raw_lons)) or np.any(np.isnan(raw_lats)):
#             print(f"[{sat_name}] ❌ NaNs in lat/lon!")
#             continue
#
#         # Don't wrap yet — leave as-is for debug
#         wrapped_lons = raw_lons
#
#         segments = split_segments(wrapped_lons, raw_lats)
#         # print(f"[{sat_name}] Total segments: {len(segments)}")
#
#         for idx, (seg_lon, seg_lat) in enumerate(segments):
#             if len(seg_lon) < 2:
#                 # print(f"[{sat_name}] Skipping segment {idx} (too short)")
#                 continue
#
#             # print(f"  Segment {idx}: {len(seg_lon)} points")
#             x, y = myMap(seg_lon, seg_lat)
#             # print(f"  [Map coords] x: {x[:3]}, y: {y[:3]}")
#             # print(f"  X range: {x.min():.1f} → {x.max():.1f}, Y range: {y.min():.1f} → {y.max():.1f}")
#
#             # Actual track rendering
#             line, = ax.plot(x, y, color='lime', linewidth=2, zorder=5)
#             dots, = ax.plot(x, y, 'wo', markersize=2, zorder=6)
#             track_lines.extend([line, dots])
#
#         # Current satellite position
#         last_lon = raw_lons[-1]
#         last_lat = raw_lats[-1]
#         xx, yy = myMap(last_lon, last_lat)
#         pt, = ax.plot(xx, yy, 'r*', markersize=10, zorder=10)
#         track_lines.append(pt)
#
#         label = ax.annotate(sat_name, xy=(xx, yy), xytext=(xx + 6, yy + 6),
#                             color='yellow', fontsize=9, zorder=11)
#         track_labels.append(label)
#
#     ax.set_xlim(myMap.xmin, myMap.xmax)
#     ax.set_ylim(myMap.ymin, myMap.ymax)
#     plt.title(f"Amateur Satellite Tracking\nUTC: {date_now:%Y-%m-%d %H:%M:%S}")
#     fig.canvas.draw()
#     fig.canvas.flush_events()
#
#     return track_lines
#
#
# # def animate(ii, selected_tle_dict):
# #     global track_lines, track_labels
# #
# #     for obj in track_lines:
# #         try: obj.remove()
# #         except: pass
# #     track_lines = []
# #
# #     for lbl in track_labels:
# #         try: lbl.remove()
# #         except: pass
# #     track_labels = []
# #
# #     latslons_dict = ConvertKepToStateVectors(selected_tle_dict)
# #     date_now = datetime.utcnow()
# #
# #     for sat_name in selected_tle_dict:
# #         arr = latslons_dict[sat_name]
# #         raw_lons = arr[:, 0]
# #         raw_lats = arr[:, 1]
# #
# #         print(f"[{sat_name}] ΔLon: {raw_lons[-1] - raw_lons[0]:.4f}°, ΔLat: {raw_lats[-1] - raw_lats[0]:.4f}°")
# #
# #         wrapped_lons = ((raw_lons + 180) % 360) - 180
# #         segments = split_segments(wrapped_lons, raw_lats)
# #         print(f"[{sat_name}] Total segments: {len(segments)}")
# #
# #         for seg_lon, seg_lat in segments:
# #             x, y = myMap(seg_lon, seg_lat)  # lon, lat
# #             line, = ax.plot(x, y, color='lime', linewidth=2, zorder=10)
# #             dots, = ax.plot(x, y, 'wo', markersize=3, zorder=11)
# #             track_lines.extend([line, dots])
# #             # (after line, dots = ax.plot(...))
# #             print(f"  [DEBUG PLOT] Track line X range: {x.min()} to {x.max()}")
# #             print(f"  [DEBUG PLOT] Track line Y range: {y.min()} to {y.max()}")
# #
# #             ax.set_xlim(x.min() - 1000000, x.max() + 1000000)
# #             ax.set_ylim(y.min() - 1000000, y.max() + 1000000)
# #
# #
# #
# #         # Last known position marker
# #         last_lon = raw_lons[-1]
# #         last_lat = raw_lats[-1]
# #         x_last, y_last = myMap(last_lon, last_lat)
# #         pt, = ax.plot(x_last, y_last, 'r*', markersize=10, zorder=12)
# #         track_lines.append(pt)
# #
# #         label = ax.annotate(sat_name, xy=(x_last, y_last), xytext=(x_last + 5, y_last + 5), color='yellow')
# #         track_labels.append(label)
# #
# #     plt.title(f"Amateur Satellite Tracking\nUTC: {date_now:%Y-%m-%d %H:%M:%S}")
# #     fig.canvas.draw()
# #     fig.canvas.flush_events()
# #     return track_lines
#
# def runPredictionTool(checkbox_dict, tle_dict):
#     # selected_tle_dict = {k: v for k, v in checkbox_dict.items() if v.get() == 1}
#     selected_tle_dict = {k: tle_dict[k] for k, v in checkbox_dict.items() if v.get() == 1}
#
#     if not selected_tle_dict:
#         print("No satellites selected. Exiting.")
#         sys.exit(0)
#
#     ani = animation.FuncAnimation(fig, animate, fargs=(selected_tle_dict,),
#                                   interval=1000, blit=False, repeat=False)
#     plt.legend(loc='lower left', frameon=True, facecolor='grey', edgecolor='white')
#     # Debug test — draw once
#     # def draw_static_path_once(selected_tle_dict):
#     #     for sat_name in selected_tle_dict:
#     #         arr = ConvertKepToStateVectors({sat_name: selected_tle_dict[sat_name]})[sat_name]
#     #         raw_lons, raw_lats = arr[:, 0], arr[:, 1]
#     #         wrapped_lons = ((raw_lons + 180) % 360) - 180
#     #         x, y = myMap(wrapped_lons, raw_lats)
#     #         ax.plot(x, y, 'magenta', linewidth=2, zorder=3)
#     #         print(f"[DEBUG] Drew static path for {sat_name}")
#     #         break  # only draw one
#
#
#     # draw_static_path_once(selected_tle_dict)
#     print(f"[DEBUG] Selected satellites: {list(selected_tle_dict.keys())}")
#
#
#     plt.show()
#
# def SetupWindow(root, tle_dict):
#     root.title("Amateur Radio Satellite Tracking")
#     helv36 = tkFont.Font(size=12, weight=tkFont.BOLD)
#
#     frame_1 = tk.Frame(root)
#     frame_1.grid(row=0, column=0, padx=10, pady=10)
#
#     checkbox_dict = {}
#     row_counter = 0
#     col_counter = 0
#     for key in sorted(tle_dict.keys()):
#         var = tk.IntVar()
#         cb = tk.Checkbutton(frame_1, text=key, font=("Arial", 10), variable=var)
#         cb.grid(row=row_counter, column=col_counter, sticky=tk.W)
#         checkbox_dict[key] = var
#         row_counter += 1
#         if row_counter >= 20:
#             row_counter = 0
#             col_counter += 1
#
#     frame_2 = tk.Frame(root)
#     frame_2.grid(row=1, column=0, padx=10, pady=10)
#     tk.Button(frame_2, text="Run Prediction", font=helv36, bg="green",
#               command=lambda: runPredictionTool(checkbox_dict, tle_dict)).grid(row=0, column=0, padx=5, pady=5)
#     tk.Button(frame_2, text="Quit Program", font=helv36, bg="red", command=root.quit).grid(row=0, column=1, padx=5, pady=5)
#
# if __name__ == "__main__":
#     root = tk.Tk()
#     SetupWindow(root, tle_dict)
#     root.mainloop()


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
