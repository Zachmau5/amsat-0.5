#!/usr/bin/env python3
import sys
import tkinter as tk

def runPredictionTool(checkbox_dict, tle_dict, my_lat, my_lon):
    """
    Called when you press “Run Prediction.”  Gathers the checked satellites,
    then imports everything from Matplotlib/Basemap/animation, builds the figure,
    and starts the FuncAnimation loop.
    """
    # 1) Gather satellites with IntVar == 1
    selected = {name: tle_dict[name] for name, var in checkbox_dict.items() if var.get() == 1}
    if not selected:
        from tkinter import messagebox
        messagebox.showwarning("No Satellites Selected", "Please check at least one satellite before running.")
        return

    # 2) Now import Matplotlib/Basemap/etc. and animate
    import numpy as np
    import matplotlib.pyplot as plt
    from mpl_toolkits.basemap import Basemap
    from matplotlib import animation
    from datetime import datetime
    from collections import deque

    from keplerian_parser import ParseTwoLineElementFile
    from kep_to_state import ConvertKepToStateVectors

    # ────────────────────────────────────────────────────────────────────────
    # Build the 2×2 figure + axes
    fig = plt.figure(figsize=(14, 7))

    # Top-Left: Global View
    ax1 = fig.add_subplot(2, 2, 1)
    map1 = Basemap(
        projection='mill',
        llcrnrlat=-90, urcrnrlat=90,
        llcrnrlon=-180, urcrnrlon=180,
        resolution='c',
        ax=ax1
    )
    map1.drawmapboundary(fill_color='black')
    map1.fillcontinents(color='gray', lake_color='black')
    map1.drawcoastlines()
    ax1.set_facecolor('black')
    ax1.set_title("Global View", color='white')

    x_qth, y_qth = map1(my_lon, my_lat)
    map1.plot(x_qth, y_qth, 'go', markersize=8)
    ax1.annotate('Me', xy=(x_qth, y_qth), xytext=(x_qth + 5, y_qth + 5), color='white')

    # Top-Right: Near-Sided Perspective
    ax2 = fig.add_subplot(2, 2, 2)
    initial_height = 2000  # km (will update each frame)
    map2 = Basemap(
        projection='nsper',
        lon_0=my_lon,
        lat_0=my_lat,
        satellite_height=initial_height * 1000.0,
        resolution='l',
        ax=ax2
    )
    map2.drawcoastlines()
    map2.fillcontinents(color='coral', lake_color='aqua')
    map2.drawparallels(np.arange(-90, 120, 30))
    map2.drawmeridians(np.arange(0, 420, 60))
    map2.drawmapboundary(fill_color='aqua')
    ax2.set_facecolor('black')
    ax2.set_title(f"Near-Sided Perspective @ {initial_height} km", color='white')

    # Bottom-Left: Text Info
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.set_facecolor('darkslategray')
    ax3.axis('off')
    text_handle = ax3.text(
        0.02, 0.5,
        "",
        color='white',
        fontsize=12,
        family='monospace',
        va='center',
        ha='left'
    )
    ax3.set_title("Satellite Status", color='white')

    # Bottom-Right: Altitude vs. Time
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.set_facecolor('darkslategray')
    ax4.set_title("Altitude vs. Time (rolling)", color='white')
    ax4.set_xlabel("Frame #", color='white')
    ax4.set_ylabel("Altitude (km)", color='white')
    ax4.tick_params(colors='white')
    max_history = 100
    alt_hist = deque(maxlen=max_history)
    frame_hist = deque(maxlen=max_history)
    line4, = ax4.plot([], [], 'y-', linewidth=2)

    # ────────────────────────────────────────────────────────────────────────
    # Utility to split “wrapping” ground tracks
    def split_segments(lons, lats, max_jump=180.0):
        segs = []
        start = 0
        for i in range(1, len(lons)):
            if abs(lons[i] - lons[i - 1]) > max_jump:
                segs.append((lons[start:i], lats[start:i]))
                start = i
        segs.append((lons[start:], lats[start:]))
        return segs

    track_objs = []
    track_lbls = []

    # Footprint plotter on near-sided
    def plot_footprint(ax, center_lon, center_lat, radius_deg):
        npts = 100
        angles = np.linspace(0, 2 * np.pi, npts)
        lons = center_lon + radius_deg * np.cos(angles)
        lats = center_lat + radius_deg * np.sin(angles)
        x, y = map2(lons, lats)
        ax.scatter(x, y, color='yellow', alpha=0.3, zorder=10)

    # ────────────────────────────────────────────────────────────────────────
    # Animate callback (called once per second)
    def animate(frame_idx, sel_dict):
        nonlocal alt_hist, frame_hist, track_objs, track_lbls

        # Remove old plot objects
        for obj in track_objs:
            obj.remove()
        track_objs.clear()
        for lbl in track_lbls:
            lbl.remove()
        track_lbls.clear()

        # Clear and reset ax3 + ax4
        ax3.clear()
        ax3.set_facecolor('darkslategray')
        ax3.axis('off')
        ax3.set_title("Satellite Status", color='white')

        ax4.clear()
        ax4.set_facecolor('darkslategray')
        ax4.set_title("Altitude vs. Time (rolling)", color='white')
        ax4.set_xlabel("Frame #", color='white')
        ax4.set_ylabel("Altitude (km)", color='white')
        ax4.tick_params(colors='white')

        now = datetime.utcnow()
        state_dict = ConvertKepToStateVectors(sel_dict, use_skyfield=False)

        # Pick first satellite for text + altitude-time
        first_name = next(iter(sel_dict))
        data = state_dict[first_name]

        # ─────────── FIX #1 ───────────
        # 'alt_km' is a scalar, not an array.  Use it directly:
        alt0 = data['alt_km']
        # 'speed_km_s' is an array.  Grab its first element for display:
        speed0 = data['speed_km_s'][0]
        lon0 = data['lons'][0]
        lat0 = data['lats'][0]
        # ──────────────────────────────

        text_lines = [
            f"Satellite:   {first_name}",
            f"UTC Time:    {now:%Y-%m-%d %H:%M:%S}",
            f"LATITUDE:    {lat0:7.3f}°",
            f"LONGITUDE:   {lon0:7.3f}°",
            f"ALTITUDE:    {alt0:7.3f} km",
            f"SPEED:       {speed0:7.3f} km/s",
        ]
        ax3.text(
            0.02, 0.5,
            "\n".join(text_lines),
            color='white',
            fontsize=12,
            family='monospace',
            va='center',
            ha='left'
        )

        # Update altitude history
        alt_hist.append(alt0)
        frame_hist.append(frame_idx)
        ax4.plot(frame_hist, alt_hist, 'y-', linewidth=2)
        ax4.set_xlim(max(0, frame_idx - max_history + 1), frame_idx + 1)
        amin = min(alt_hist) - 10
        amax = max(alt_hist) + 10
        ax4.set_ylim(amin, amax)
        ax4.tick_params(colors='white')

        # For each selected satellite → plot on both maps
        for sat_name in sel_dict:
            sat_data = state_dict[sat_name]
            lons = sat_data['lons']
            lats = sat_data['lats']
            # alt_km is a scalar
            footprint_deg = (sat_data['alt_km'] / (6371.0 + sat_data['alt_km'])) * (180.0 / np.pi)

            # ─────────── FIX #2 ───────────
            # Instead of clearing the entire ax2, just redraw coastlines + footprint
            ax2.clear()
            map2.lon_0 = lon0
            map2.lat_0 = lat0
            map2.satellite_height = sat_data['alt_km'] * 1000.0
            map2.drawmapboundary(fill_color='aqua')
            map2.fillcontinents(color='coral', lake_color='aqua')
            map2.drawcoastlines()
            map2.drawparallels(np.arange(-90, 120, 30))
            map2.drawmeridians(np.arange(0, 420, 60))
            map2.drawstates(linewidth=1.5, color='black', zorder=10)
            map2.drawcountries(linewidth=1.5, color='black', zorder=10)

            plot_footprint(ax2, lon0, lat0, footprint_deg)

            # Ground station on near-sided
            xg, yg = map2(my_lon, my_lat)
            ax2.plot(xg, yg, 'go', markersize=8)
            ax2.annotate('Me', xy=(xg, yg), xytext=(xg + 5, yg + 5), color='white')

            # Satellite pos on near-sided
            xsn, ysn = map2(lon0, lat0)
            p2, = ax2.plot(xsn, ysn, 'r*', markersize=10, zorder=10)
            track_objs.append(p2)

            segments = split_segments(lons, lats)
            for seg_lons, seg_lats in segments:
                if len(seg_lons) < 2:
                    continue
                xx2, yy2 = map2(seg_lons, seg_lats)
                l2, = ax2.plot(xx2, yy2, color='lime', linewidth=2, zorder=5)
                d2, = ax2.plot(xx2, yy2, 'wo', markersize=2, zorder=6)
                track_objs.extend([l2, d2])

            ax2.set_xlim(map2.xmin, map2.xmax)
            ax2.set_ylim(map2.ymin, map2.ymax)
            ax2.set_title(f"Near-Sided @ {int(sat_data['alt_km'])} km", color='white')
            # ─────────────────────────────────

            # GLOBAL (ax1)
            xg1, yg1 = map1(lon0, lat0)
            p1, = ax1.plot(xg1, yg1, 'r*', markersize=8, zorder=10)
            track_objs.append(p1)

            for seg_lons, seg_lats in segments:
                if len(seg_lons) < 2:
                    continue
                xx1, yy1 = map1(seg_lons, seg_lats)
                l1, = ax1.plot(xx1, yy1, color='lime', linewidth=2, zorder=5)
                d1, = ax1.plot(xx1, yy1, 'wo', markersize=2, zorder=6)
                track_objs.extend([l1, d1])

            lbl = ax1.annotate(
                sat_name,
                xy=(xg1, yg1),
                xytext=(xg1 + 6, yg1 + 6),
                color='yellow',
                fontsize=9,
                zorder=11
            )
            track_lbls.append(lbl)

        ax1.set_xlim(map1.xmin, map1.xmax)
        ax1.set_ylim(map1.ymin, map1.ymax)

        # Re-draw ground station globally
        map1.plot(x_qth, y_qth, 'go', markersize=8)
        ax1.annotate('Me', xy=(x_qth, y_qth), xytext=(x_qth + 5, y_qth + 5), color='white')

        plt.suptitle(f"Amateur Satellite Tracking — UTC: {now:%Y-%m-%d %H:%M:%S}", color='white')
        fig.canvas.draw()
        fig.canvas.flush_events()

        return track_objs  # blit=False, but we return this list of artists anyway

    # Build FuncAnimation
    ani = animation.FuncAnimation(
        fig,
        animate,
        fargs=(selected,),
        interval=1000,
        blit=False,
        repeat=False
    )

    # ── FIX #3: remove empty legend() call ──
    # ax1.legend(loc='lower left', facecolor='gray', edgecolor='white')
    plt.tight_layout()
    plt.show()


def SetupWindow(root, tle_dict, my_lat, my_lon):
    """
    Create a plain-white Tk window with checkboxes and two buttons.
    """
    root.title("Satellite Selector")
    root.configure(bg="white")

    frame1 = tk.Frame(root, bg="white")
    frame1.grid(row=0, column=0, padx=10, pady=10)

    checkbox_dict = {}
    row_ctr = 0
    col_ctr = 0

    for sat_name in sorted(tle_dict.keys()):
        var = tk.IntVar(value=0)
        cb = tk.Checkbutton(
            frame1,
            text=sat_name,
            variable=var,
            fg="black",
            bg="white",
            anchor="w"
        )
        cb.grid(row=row_ctr, column=col_ctr, sticky=tk.W, pady=2)
        checkbox_dict[sat_name] = var

        row_ctr += 1
        if row_ctr >= 20:
            row_ctr = 0
            col_ctr += 1

    frame2 = tk.Frame(root, bg="white")
    frame2.grid(row=1, column=0, padx=10, pady=10)

    run_btn = tk.Button(
        frame2,
        text="Run Prediction",
        command=lambda: runPredictionTool(checkbox_dict, tle_dict, my_lat, my_lon)
    )
    run_btn.grid(row=0, column=0, padx=5, pady=5)

    quit_btn = tk.Button(
        frame2,
        text="Quit Program",
        command=root.quit
    )
    quit_btn.grid(row=0, column=1, padx=5, pady=5)

    return checkbox_dict


if __name__ == "__main__":
    from keplerian_parser import ParseTwoLineElementFile
    tle_dict = ParseTwoLineElementFile("amateur.tle")

    # Ground station (example):
    my_lat = 41.19494
    my_lon = -111.94153

    # Compute QTH on global map (one-time import):
    import matplotlib.pyplot as plt
    from mpl_toolkits.basemap import Basemap

    map1 = Basemap(
        projection='mill',
        llcrnrlat=-90, urcrnrlat=90,
        llcrnrlon=-180, urcrnrlon=180,
        resolution='c',
    )
    x_qth, y_qth = map1(my_lon, my_lat)

    # Build and show the Tk window on a white background:
    root = tk.Tk()
    checkbox_dict = SetupWindow(root, tle_dict, my_lat, my_lon)
    root.mainloop()
