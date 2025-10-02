#!/usr/bin/env python3
import sys
import math
import time
import queue
import threading

import tkinter as tk
from fetch_tle import fetch_group
from visibility import has_visible_pass_next_hour  # from the separate module

# from pointing import az_el_from_geodetic  # (kept for compatibility, not used for Skyfield path)
import serial
from serial import SerialException, Serial



# 1. Kill anything else holding the port
# lsof /dev/ttyUSB0
# fuser -v /dev/ttyUSB0
#
#
# If you see a process (Python, miniterm, etc.), stop it:
#
# kill <PID>
#
# 2. Open screen on the rotator’s port
# screen /dev/ttyUSB0 9600
#
#
# The GS-232 expects 9600 baud, 8N1, no handshake by default.
#
# 3. Basic “flush” commands
#
# Inside screen:
#
# Type S then press Enter → this sends the Stop command, halting any rotation and clearing the input buffer.
#
# Type C2 then Enter → controller replies with the current AZ/EL (e.g., +0180+0090).
#
# Type H or H2 then Enter → lists the command help screens, confirming it’s alive.
#
# 4. Exit screen cleanly
#
# Press:
#
# Ctrl-A, then K, then Y
#
#
# That kills the screen session and frees the port.
# def runPredictionTool(checkbox_dict, tle_dict, my_lat, my_lon):
def runPredictionTool(checkbox_dict, tle_dict, my_lat, my_lon, tle_path):

    """
    2×2 figure:
      TL: Global map, TR: Near-sided (QTH-centered),
      BL: Az/Elev gauges, BR: GS-232B console (Waaa eee + C2 echo).
    """
    # 1) Gather satellites
    selected = {name: tle_dict[name] for name, var in checkbox_dict.items() if var.get() == 1}
    if not selected:
        from tkinter import messagebox
        messagebox.showwarning("No Satellites Selected", "Please check at least one satellite before running.")
        return

    # ────────────────────────────────────────────────────────────────────
    # TLE lookup (fixes the earlier ndarray .get error by reading raw TLE lines)
    def _norm_name(s: str) -> str:
        return "".join((s or "").upper().split())

    def load_tle_lookup(tle_path="amateur.tle"):
        lk = {}
        try:
            with open(tle_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
            i = 0
            while i <= len(lines) - 3:
                name = lines[i]
                l1   = lines[i+1]
                l2   = lines[i+2]
                if l1.startswith("1 ") and l2.startswith("2 "):
                    lk[_norm_name(name)] = (l1, l2)
                    # Also index by NORAD if you ever need it
                    norad = l1[2:7].strip()
                    lk[norad] = (l1, l2)
                    i += 3
                else:
                    i += 1
        except Exception as e:
            print(f"[WARN] Could not load TLE file: {e}")
        return lk

    # tle_lookup = load_tle_lookup("amateur.tle")
    tle_lookup = load_tle_lookup(tle_path)

    # ────────────────────────────────────────────────────────────────────
    # Serial continuity manager
    class SerialManager:
        def __init__(self, candidates, baud=9600, timeout=1.0):
            self.candidates = candidates[:]  # list of port names to try
            self.baud = baud
            self.timeout = timeout
            self.ser = None
            self.last_open_port = None
            self._open_any()

        def _open_any(self):
            ports_to_try = []
            if self.last_open_port:
                ports_to_try.append(self.last_open_port)
            ports_to_try.extend([p for p in self.candidates if p != self.last_open_port])

            for p in ports_to_try:
                try:
                    self.ser = Serial(
                        port=p,
                        baudrate=self.baud,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=self.timeout,
                        xonxoff=False,
                        rtscts=False,
                        dsrdtr=False,
                        write_timeout=1.0,
                    )
                    self.last_open_port = p
                    try:
                        self.ser.reset_input_buffer()
                        self.ser.reset_output_buffer()
                        # self._write_raw(b"P45\r\n")  # prefer 450° mode
                        # _ = self._readline()
                    except Exception:
                        pass
                    print(f"[SER] Opened {p} @ {self.baud} 8N1")
                    return True
                except Exception as e:
                    print(f"[SER] Open {p} failed: {e}")
                    self.ser = None
            return False

        def ensure_open(self):
            if self.ser and self.ser.is_open:
                return True
            return self._open_any()

        def close(self):
            try:
                if self.ser:
                    self.ser.close()
                    print("[SER] Closed port")
            except Exception:
                pass
            self.ser = None

        def _write_raw(self, bcmd):
            if not self.ensure_open():
                raise SerialException("Port not open")
            self.ser.write(bcmd)
            self.ser.flush()

        def _readline(self):
            if not self.ensure_open():
                return ""
            try:
                return self.ser.readline().decode(errors="ignore").strip()
            except Exception:
                return ""

        def write_cmd(self, cmd_str, expect_reply=False, retries=1):
            payload = (cmd_str.rstrip() + "\r\n").encode("ascii", errors="ignore")
            attempt = 0
            while attempt <= retries:
                try:
                    self._write_raw(payload)
                    if expect_reply:
                        return self._readline()
                    return ""
                except SerialException:
                    self.close()
                    time.sleep(0.2)
                    self.ensure_open()
                    attempt += 1
            return ""

        def send_move(self, az, el, echo_c2=True):
            cmd = f"W{int(round(az)):03d} {int(round(el)):03d}"
            reply = ""
            try:
                _ = self.write_cmd(cmd, expect_reply=False, retries=1)
                if echo_c2:
                    reply = self.write_cmd("C2", expect_reply=True, retries=1)
            except Exception:
                self.close()
                self.ensure_open()
            return cmd, reply

        def query_c2(self):
            return self.write_cmd("C2", expect_reply=True, retries=1)

    # Always try these; USB0 preferred per your setup
    ser_mgr = SerialManager(
        candidates=["/dev/ttyUSB0", "/dev/ttyUSB1", "COM3", "COM4"],
        baud=9600,
        timeout=1.0
    )

    # ────────────────────────────────────────────────────────────────────
    # Heavy imports now
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from mpl_toolkits.basemap import Basemap
    from matplotlib import animation
    from datetime import datetime
    from collections import deque
    from skyfield.api import load, wgs84, EarthSatellite

    ts = load.timescale()
    _sat_cache = {}

    # N2YO-style debug print
    def n2yo_style_debug(name, sat, t, note=""):
        try:
            geoc = sat.at(t)
            sp = geoc.subpoint()
            lat = sp.latitude.degrees
            lon = sp.longitude.degrees
            alt_km = sp.elevation.km
            vx, vy, vz = geoc.velocity.km_per_s
            speed = (vx*vx + vy*vy + vz*vz) ** 0.5
            utc_now = datetime.utcnow()
            print("\n--- N2YO Comparison Style ---")
            print(f"Satellite:     {name}")
            print(f"UTC Time:      {utc_now.strftime('%H:%M:%S')}")
            print(f"LATITUDE:      {lat:.2f}°")
            print(f"LONGITUDE:     {lon:.2f}°")
            print(f"ALTITUDE [km]: {alt_km:.2f}")
            print(f"SPEED [km/s]:  {speed:.2f}")
            if note:
                print(f"NOTE:          {note}")
            print("-----------------------------\n")
        except Exception as e:
            print(f"[DEBUG] N2YO-style debug failed: {e}")

    # ────────────────────────────────────────────────────────────────────
    # Figure layout
    fig = plt.figure(figsize=(14, 7))
    gs = fig.add_gridspec(2, 2, hspace=0.25, wspace=0.25)
    ax1 = fig.add_subplot(gs[0, 0])   # Global
    ax2 = fig.add_subplot(gs[0, 1])   # Near-sided
    subgs = gs[1, 0].subgridspec(2, 1, hspace=0.35)
    ax_az = fig.add_subplot(subgs[0, 0], projection='polar')
    ax_el = fig.add_subplot(subgs[1, 0], projection='polar')

    # Serial console (bottom-right)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor('black'); ax4.axis('off')
    ax4.set_title("Yaesu GS-232B Serial Console", color='white')
    serial_lines = deque(maxlen=14)
    serial_text = ax4.text(
        0.02, 0.98, "", transform=ax4.transAxes,
        color='black', fontsize=11, family='monospace',
        ha='left', va='top'
    )

    # ────────────────────────────────────────────────────────────────────
    # Anti-jitter knobs
    AZ_DEADBAND_DEG   = 0.4
    EL_DEADBAND_DEG   = 0.3
    MIN_INTERVAL_S    = 1.0
    AZ_SLEW_DEG_PER_S = 8.0
    EL_SLEW_DEG_PER_S = 6.0
    QUANT_STEP_DEG    = 0.2
    last_sent_time = [0.0]
    last_cmd = {"az": None, "el": None}
    smoothed = {"az": None, "el": None}
    ZENITH_FREEZE_DEG = 87.0   # hold az near zenith to avoid flips
    USE_AZ_UNWRAP      = True  # keep az continuous so we can send >360 if needed

    def unwrap_az(prev, new_0to360):
        """Return new az near 'prev' by allowing ±360 jumps."""
        if prev is None:
            return new_0to360
        cands = (new_0to360, new_0to360 + 360.0, new_0to360 - 360.0)
        return min(cands, key=lambda x: abs(x - prev))

    def _quantize(v, step=QUANT_STEP_DEG):
        return round(v / step) * step

    def _slew_toward(current, target, max_rate_deg_s, dt):
        if current is None:
            return target
        max_delta = max_rate_deg_s * max(dt, 1e-3)
        dv = target - current
        if dv >  max_delta: dv =  max_delta
        if dv < -max_delta: dv = -max_delta
        return current + dv

    # Gauges styling
    def az_to_compass(az):
        dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE',
                'S','SSW','SW','WSW','W','WNW','NW','NNW']
        return dirs[int((az/22.5)+0.5) % 16]

    def init_az_compass(ax):
        ax.set_facecolor('black')
        ax.set_theta_zero_location('N'); ax.set_theta_direction(-1)
        ax.set_rlim(0, 1.0); ax.set_rticks([]); ax.set_xticklabels([])
        ax.text(0.5, 1.08, "Azimuth", transform=ax.transAxes, ha='center', va='bottom',
                color='white', fontsize=12,
                path_effects=[pe.withStroke(linewidth=3, foreground='black')])
        for r in (0.33, 0.66, 1.0):
            ax.plot([0, 2*math.pi], [r, r], color='white', alpha=0.15, linewidth=1)
        for ang in range(0, 360, 30):
            t = math.radians(ang)
            ax.plot([t, t], [0.0, 1.0], color='white', alpha=0.15, linewidth=1)
        for ang, lab in [(0, 'N'), (90, 'E'), (180, 'S'), (270, 'W')]:
            ax.text(math.radians(ang), 0.7, lab, color='white', ha='center', va='bottom', fontsize=10)

    def init_el_gauge(ax):
        ax.set_facecolor('black')
        ax.set_theta_zero_location('W'); ax.set_theta_direction(-1)
        ax.set_thetamin(0); ax.set_thetamax(90)
        ax.set_rlim(0, 1.0); ax.set_rticks([]); ax.set_xticklabels([])
        ax_el.text(0.5, -0.18, "Elevation", transform=ax_el.transAxes, ha='center', va='top',
                   color='white', fontsize=12,
                   path_effects=[pe.withStroke(linewidth=3, foreground='black')])
        ax.bar(math.radians(5), 1.0, width=math.radians(10), bottom=0.0, alpha=0.14, color='red', edgecolor=None)

    # Maps
    map1 = Basemap(projection='mill', llcrnrlat=-90, urcrnrlat=90,
                   llcrnrlon=-180, urcrnrlon=180, resolution='c', ax=ax1)
    map1.drawmapboundary(fill_color='white')
    map1.fillcontinents(color='gray', lake_color='blue')
    map1.drawcoastlines()
    ax1.set_facecolor('white')
    ax1.set_title("Global View", color='black')
    x_q_g, y_q_g = map1(my_lon, my_lat)
    map1.plot(x_q_g, y_q_g, 'go', markersize=8)
    ax1.annotate('Me', xy=(x_q_g, y_q_g), xytext=(x_q_g + 5, y_q_g + 5), color='black')

    map2 = Basemap(projection='nsper', lon_0=my_lon, lat_0=my_lat,
                   satellite_height=2000 * 1000.0, resolution='l', ax=ax2)

    def draw_nearsided_background():
        ax2.set_facecolor('black')
        map2.ax = ax2
        map2.drawmapboundary(fill_color='aqua')
        map2.fillcontinents(color='coral', lake_color='aqua', zorder=1)
        map2.drawcoastlines(color='white', linewidth=0.6)
        xq, yq = map2(my_lon, my_lat)
        ax2.plot(xq, yq, 'go', markersize=8, zorder=5)
        ax2.annotate('Me', xy=(xq, yq), xytext=(xq + 5, yq + 5), color='white', zorder=6)
        ax2.set_title("Near-Sided (QTH-centered)", color='white')

    draw_nearsided_background()

    track_objs, track_lbls = [], []

    # ────────────────────────────────────────────────────────────────────
    def animate(frame_idx, sel_dict):
        nonlocal track_objs, track_lbls, serial_lines, serial_text

        # Clear dynamic artists
        for o in track_objs:
            try: o.remove()
            except: pass
        track_objs.clear()
        for l in track_lbls:
            try: l.remove()
            except: pass
        track_lbls.clear()

        # Gauges fresh
        ax_az.cla(); init_az_compass(ax_az)
        ax_el.cla(); init_el_gauge(ax_el)

        now = datetime.utcnow()

        # Which sat are we driving with?
        first_name = next(iter(sel_dict))
        # Get TLE lines by *name* from our file-based lookup
        lkp = tle_lookup.get(_norm_name(first_name))
        if not lkp:
            serial_lines.append(f"{now:%H:%M:%S}  {first_name:<18} → [WARN] No TLE for name in file")
            serial_text.set_text("\n".join(serial_lines))
            return track_objs
        l1, l2 = lkp

        # Build or reuse the Skyfield satellite object
        key = (first_name, l1, l2)
        sat = _sat_cache.get(key)
        if sat is None:
            sat = EarthSatellite(l1, l2, first_name, ts)
            _sat_cache[key] = sat

        # Propagate and compute topocentric az/el
        t = ts.utc(now.year, now.month, now.day, now.hour, now.minute,
                   now.second + now.microsecond * 1e-6)
        gs = wgs84.latlon(my_lat, my_lon, elevation_m=0.0)
        alt_ref, az_ref, distance = (sat - gs).at(t).altaz()
        el_deg = alt_ref.degrees
        az_deg = az_ref.degrees % 360.0
        el_deg = alt_ref.degrees
        az_0to360 = az_ref.degrees % 360.0

# ---- Anti-jitter + send ----
        if el_deg < 0:
            cmd_echo = "HOLD (below horizon)"
        else:
            # initialize smoothed state
            if smoothed["az"] is None: smoothed["az"] = az_0to360
            if smoothed["el"] is None: smoothed["el"] = el_deg

            # keep azimuth continuous (so we can go past 360 up to 450 on capable rotators)
            if USE_AZ_UNWRAP:
                target_azc = unwrap_az(smoothed["az"], az_0to360)
            else:
                target_azc = az_0to360

            # optional: freeze az near zenith to avoid the classic keyhole flip
            if el_deg >= ZENITH_FREEZE_DEG:
                target_azc = smoothed["az"]

            # slew toward targets at physical rate limits
            dt = min(2.0, max(0.05, (now.timestamp() - last_sent_time[0]) if last_sent_time[0] > 0 else 0.6))
            smoothed["az"] = _slew_toward(smoothed["az"], target_azc, AZ_SLEW_DEG_PER_S, dt)
            smoothed["el"] = _slew_toward(smoothed["el"], el_deg,      EL_SLEW_DEG_PER_S, dt)

            # clamp to mount limits; *allow up to 450°* for az if supported
            az_cmd = max(0,   min(450, _quantize(smoothed["az"])))
            el_cmd = max(0,   min(180, _quantize(smoothed["el"])))
            # Deadband & rate
            if (last_cmd["az"] is not None and last_cmd["el"] is not None and
                abs(az_cmd - last_cmd["az"]) < AZ_DEADBAND_DEG and
                abs(el_cmd - last_cmd["el"]) < EL_DEADBAND_DEG):
                cmd_echo = f"SKIP (deadband) → {az_cmd:6.2f} {el_cmd:6.2f}"
            elif last_sent_time[0] > 0 and (now.timestamp() - last_sent_time[0]) < MIN_INTERVAL_S:
                cmd_echo = f"SKIP (rate-limit) → {az_cmd:6.2f} {el_cmd:6.2f}"
            else:
                sent_cmd, reply = ser_mgr.send_move(az_cmd, el_cmd, echo_c2=True)
                last_cmd["az"], last_cmd["el"] = az_cmd, el_cmd
                last_sent_time[0] = now.timestamp()
                # Print N2YO-style block only when we actually send to motors
                n2yo_style_debug(first_name, sat, t, note=f"Sent: {sent_cmd}")
                if reply:
                    cmd_echo = f"{sent_cmd} | {reply}"
                else:
                    cmd_echo = f"{sent_cmd} | (no echo)"

        serial_lines.append(f"{now:%H:%M:%S}  {first_name:<18} → {cmd_echo}")
        serial_text.set_text("\n".join(serial_lines))

        # ---- Gauges ----
        theta = math.radians(az_deg % 360.0)
        ax_az.plot([0, theta], [0, 1.0], color='yellow', linewidth=3, zorder=5)
        ax_az.plot([theta], [1.0], marker='o', markersize=8,
                   markeredgecolor='black', markerfacecolor='yellow', zorder=6)
        el_disp = max(0.0, min(90.0, el_deg))
        theta_el = math.radians(el_disp)
        ax_el.plot([math.radians(0), theta_el], [0, 1.0], color='yellow', linewidth=3, zorder=5)
        ax_el.plot([theta_el], [1.0], marker='o', markersize=8,
                   markeredgecolor='black', markerfacecolor='yellow', zorder=6)
        # ---- Maps ----
        ax2.cla(); draw_nearsided_background()
        subpoint = (sat.at(t)).subpoint()
        sat_lat = subpoint.latitude.degrees
        sat_lon = subpoint.longitude.degrees
        alt_km = subpoint.elevation.km

        xs, ys = map2(sat_lon, sat_lat)
        p2, = ax2.plot(xs, ys, 'r*', markersize=10, zorder=10)
        track_objs.append(p2)

        xg1, yg1 = map1(sat_lon, sat_lat)
        p1, = ax1.plot(xg1, yg1, 'r*', markersize=8, zorder=10); track_objs.append(p1)
        lbl = ax1.annotate(first_name, xy=(xg1, yg1), xytext=(xg1 + 6, yg1 + 6),
                           color='black', fontsize=9, zorder=11)
        track_lbls.append(lbl)

        # Title/status
        geoc = sat.at(t)
        vx, vy, vz = geoc.velocity.km_per_s
        speed = (vx*vx + vy*vy + vz*vz) ** 0.5
        plt.suptitle(
            f"UTC {now:%Y-%m-%d %H:%M:%S} | {first_name}  Lat {sat_lat:+7.2f}°  Lon {sat_lon:+8.2f}°  Alt {alt_km:.0f} km  |  {speed:.2f} km/s",
            color='black'
        )
        return track_objs

    ani = animation.FuncAnimation(fig, animate, fargs=(selected,),
                                  interval=600, blit=False, repeat=False)


    import matplotlib.pyplot as plt
    plt.show()


import tkinter as tk
from fetch_tle import fetch_group
from keplerian_parser import ParseTwoLineElementFile
def SetupWindow(root, my_lat, my_lon):
    root.title("Satellite Selector")
    root.configure(bg="white")

    # ── Group selector ──────────────────────────────────────────────────
    frame0 = tk.Frame(root, bg="white")
    frame0.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    group_var = tk.StringVar(value="Amateur")
    tk.Label(frame0, text="Select Group:", bg="white").pack(side="left")
    group_menu = tk.OptionMenu(frame0, group_var,
                               "Amateur", "NOAA", "GOES", "Weather", "CUBESAT", "SATNOGS")
    group_menu.pack(side="left")

    # ── Scrollable checkbox area: V + H scrollbars ─────────────────────
    frame1_container = tk.Frame(root, bg="white")
    frame1_container.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    # Let row 1 / col 0 expand
    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(0, weight=1)

    canvas = tk.Canvas(frame1_container, bg="white", highlightthickness=0)
    vsb = tk.Scrollbar(frame1_container, orient="vertical",   command=canvas.yview)
    hsb = tk.Scrollbar(frame1_container, orient="horizontal", command=canvas.xview)
    canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    canvas.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    frame1_container.grid_rowconfigure(0, weight=1)
    frame1_container.grid_columnconfigure(0, weight=1)

    # Inner frame that will hold all the checkboxes
    list_frame = tk.Frame(canvas, bg="white")
    list_window = canvas.create_window((0, 0), window=list_frame, anchor="nw")

    # Keep scrollregion updated whenever content changes
    def _on_list_config(_evt=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
    list_frame.bind("<Configure>", _on_list_config)

    # Mouse/touchpad scrolling:
    #  - vertical with wheel
    #  - horizontal with Shift+wheel
    #  - Linux button events supported too
    def _bind_mousewheel(canvas):
        # Cross-platform mousewheel:
        #  - Windows/macOS: <MouseWheel>, <Shift-MouseWheel>
        #  - X11/Linux: <Button-4>/<Button-5>, <Shift-Button-4>/<Shift-Button-5>
        system = canvas.tk.call('tk', 'windowingsystem')  # 'x11', 'win32', 'aqua'

        def on_wheel(e):
            # e.delta: +120/-120 on Win, small values on macOS; not used on X11
            step = -1 if getattr(e, "delta", 0) > 0 else 1
            canvas.yview_scroll(step, "units")

        def on_wheel_h(e):
            step = -1 if getattr(e, "delta", 0) > 0 else 1
            canvas.xview_scroll(step, "units")

        # X11 button emulation
        def on_linux_up(e):    canvas.yview_scroll(-1, "units")
        def on_linux_down(e):  canvas.yview_scroll( 1, "units")
        def on_linux_left(e):  canvas.xview_scroll(-1, "units")
        def on_linux_right(e): canvas.xview_scroll( 1, "units")

        # Bind only while cursor is over the canvas
        def enable(_):
            if system in ("win32", "aqua"):
                canvas.bind_all("<MouseWheel>", on_wheel)
                canvas.bind_all("<Shift-MouseWheel>", on_wheel_h)
            else:  # x11
                canvas.bind_all("<Button-4>", on_linux_up)
                canvas.bind_all("<Button-5>", on_linux_down)
                canvas.bind_all("<Shift-Button-4>", on_linux_left)
                canvas.bind_all("<Shift-Button-5>", on_linux_right)

        def disable(_):
            if system in ("win32", "aqua"):
                canvas.unbind_all("<MouseWheel>")
                canvas.unbind_all("<Shift-MouseWheel>")
            else:
                canvas.unbind_all("<Button-4>")
                canvas.unbind_all("<Button-5>")
                canvas.unbind_all("<Shift-Button-4>")
                canvas.unbind_all("<Shift-Button-5>")

        canvas.bind("<Enter>", enable)
        canvas.bind("<Leave>", disable)


    # ── Populate and wire buttons ───────────────────────────────────────
    checkbox_dict = {}

    def load_satellites():
        nonlocal checkbox_dict
        for w in list_frame.winfo_children():
            w.destroy()
        checkbox_dict.clear()

        LABEL_TO_KEY = {
            "Amateur": "Amateur",
            "NOAA": "NOAA",
            "GOES": "GOES",
            "Weather": "Weather",
            "CUBESAT": "CUBESAT",
            "SATNOGS": "SATNOGS",
        }
        key = LABEL_TO_KEY.get(group_var.get())
        if key is None:
            # If you see AttributeError here, import at top: from tkinter import messagebox
            tk.messagebox.showerror("Unknown group", f"{group_var.get()} is not configured.")
            return

        tle_filename = fetch_group(key)
        tle_dict = ParseTwoLineElementFile(tle_filename)

        # Grid checkboxes into columns of 20 rows (grows wide -> horizontal scroll)
        row_ctr, col_ctr = 0, 0
        for sat_name in sorted(tle_dict.keys()):
            var = tk.IntVar(value=0)
            cb = tk.Checkbutton(list_frame, text=sat_name, variable=var,
                                fg="black", bg="white", anchor="w")
            cb.grid(row=row_ctr, column=col_ctr, sticky=tk.W, pady=2, padx=4)
            checkbox_dict[sat_name] = var
            row_ctr += 1
            if row_ctr >= 20:
                row_ctr = 0
                col_ctr += 1

        # Update scroll area after populating
        list_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

        # Wire Run button for this dataset
        run_button.config(command=lambda: runPredictionTool(
            checkbox_dict, tle_dict, my_lat, my_lon, tle_path=tle_filename))

    # Buttons row
    frame2 = tk.Frame(root, bg="white")
    frame2.grid(row=2, column=0, padx=10, pady=10)
    run_button = tk.Button(frame2, text="Run Prediction")
    run_button.grid(row=0, column=0, padx=5, pady=5)
    tk.Button(frame2, text="Quit Program", command=root.quit).grid(row=0, column=1, padx=5, pady=5)

    # Initial load + reload on selection change
    load_satellites()
    group_var.trace_add("write", lambda *_: load_satellites())

    return checkbox_dict



# def SetupWindow(root, my_lat, my_lon):
#     root.title("Satellite Selector")
#     root.configure(bg="white")
#
#     # Frame for group selection
#     frame0 = tk.Frame(root, bg="white")
#     frame0.grid(row=0, column=0, padx=10, pady=10, sticky="w")
#
#     group_var = tk.StringVar(value="Amateur")
#     tk.Label(frame0, text="Select Group:", bg="white").pack(side="left")
#     group_menu = tk.OptionMenu(frame0, group_var, "Amateur", "NOAA", "GOES", "Weather", "CUBESAT", "SATNOGS")
#     group_menu.pack(side="left")
#
#     # Frame for satellite checkboxes
#     frame1 = tk.Frame(root, bg="white")
#     frame1.grid(row=1, column=0, padx=10, pady=10)
#     checkbox_dict = {}
#
#     def load_satellites():
#         nonlocal checkbox_dict
#         for widget in frame1.winfo_children():
#             widget.destroy()
#         checkbox_dict.clear()
#
#         group = group_var.get()
#         LABEL_TO_KEY = {
#             "Amateur": "Amateur",
#             "NOAA": "NOAA",
#             "GOES": "GOES",
#             "Weather": "Weather",
#             "CUBESAT": "CUBESAT",
#             "SATNOGS" : "SATNOGS",
#         }
#         key = LABEL_TO_KEY.get(group_var.get())
#         if key is None:
#             tk.messagebox.showerror("Unknown group", f"{group_var.get()} is not configured.")
#             return
#         tle_filename = fetch_group(key)
#
#
#         # tle_filename = fetch_group(group)  # fetch and save file
#         tle_dict = ParseTwoLineElementFile(tle_filename)
#
#         row_ctr, col_ctr = 0, 0
#         for sat_name in sorted(tle_dict.keys()):
#             var = tk.IntVar(value=0)
#             cb = tk.Checkbutton(frame1, text=sat_name, variable=var,
#                                 fg="black", bg="white", anchor="w")
#             cb.grid(row=row_ctr, column=col_ctr, sticky=tk.W, pady=2)
#             checkbox_dict[sat_name] = var
#             row_ctr += 1
#             if row_ctr >= 20:
#                 row_ctr = 0
#                 col_ctr += 1
#
#         # Update Run button
#         run_button.config(command=lambda: runPredictionTool(
#             # checkbox_dict, tle_dict, my_lat, my_lon))
#             checkbox_dict, tle_dict, my_lat, my_lon, tle_path=tle_filename))
#
#
#     # Frame for buttons
#     frame2 = tk.Frame(root, bg="white")
#     frame2.grid(row=2, column=0, padx=10, pady=10)
#     run_button = tk.Button(frame2, text="Run Prediction")
#     run_button.grid(row=0, column=0, padx=5, pady=5)
#     tk.Button(frame2, text="Quit Program", command=root.quit).grid(row=0, column=1, padx=5, pady=5)
#
#     # Initial load
#     load_satellites()
#     # Reload when group changes
#     group_var.trace_add("write", lambda *_: load_satellites())
#
#     return checkbox_dict


if __name__ == "__main__":
    # We still use your keplerian_parser only to list satellite NAMES for the GUI.
    # (Raw TLE L1/L2 are loaded separately from the file for Skyfield.)
    from keplerian_parser import ParseTwoLineElementFile
    tle_dict = ParseTwoLineElementFile("amateur.tle")

    # Ground station
    my_lat = 41.19502233287143
    my_lon = -111.94128097234622

    root = tk.Tk()
    checkbox_dict = SetupWindow(root, my_lat, my_lon)
    root.mainloop()
