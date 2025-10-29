#!/usr/bin/env python3
"""
GS-232B Calibration Wizard (UI helper for main_gs232b.py)
------------------------------------------------------------------
Author: Zach (comments written in my own voice)

Purpose
-------
A lightweight Tk/Tkinter wizard I can run before the main tracking GUI to:
  1) Drive the array to known reference headings (North/South) to verify
     physical vs. “software” north alignment.
  2) Execute a 360° CW sweep at a chosen GS-232B speed (X1..X4),
     using C2 polling to integrate travel (or a SIM mode when hardware
     isn’t present).
  3) Optionally park (stage) the array at a preset azimuth before exiting.
  4) Return control to the main app (satellite selection / tracking).

Design notes
------------
- Decoupled from main so I can run it standalone or embedded in the main Tk root.
- Serial is minimal and intended to be compatible with my existing SerialManager.
- UI never blocks: sweeps run on a worker thread; UI updates via `after()`.
- Includes a no-hardware “Simulate” mode for bench testing or demos.

Commands used (quick ref)
-------------------------
Wxxx yyy  -> absolute move (az=xxx, el=yyy)
R / L     -> CW / CCW rotation
U / D     -> Up / Down rotation
X1..X4    -> horizontal rotation speed select
A         -> azimuth-only stop
S         -> all stop (both axes)
C2        -> position echo

This is NOT a hard calibration tool (no F/O/offset commands). It’s a bring-up
sequence to verify headings and ensure the system behaves as expected.
"""
import time
import threading
import tkinter as tk
import re
from tkinter import ttk
import tkinter.font as tkfont

# PySerial is optional so the UI can be tested without hardware.
try:
    import serial
    from serial import Serial, SerialException
except Exception:  # allow import in environments without pyserial for quick UI tests
    serial = None
    Serial = None
    class SerialException(Exception): ...


# =========================
# Modern-ish font selection
# =========================
def _pick_ui_font():
    """Try to use a clean UI font; fall back to TkDefaultFont if unavailable."""
    try:
        fams = set(tkfont.families())
        for f in ("Segoe UI", "Noto Sans", "DejaVu Sans", "Cantarell", "Roboto", "Arial"):
            if f in fams:
                return f
    except Exception:
        pass
    return "TkDefaultFont"


# =========================
# C2 parser (shared helper)
# =========================
# Accept typical C2 variants like '+0180+0090', ' 180 090', '0180,090', etc.
_C2_RE = re.compile(r'([+\-]?\d{3,4})[ ,]?([+\-]?\d{3})')

def parse_c2_az_el(reply: str):
    """
    Parse GS-232B C2 reply into (az, el) integer degrees.
    Returns (None, None) on failure.

    I clamp az ∈ [0, 450] and el ∈ [0, 180] to keep values sane and avoid
    weirdness when a controller supports >360° wrap.
    """
    if not reply:
        return (None, None)
    m = _C2_RE.search(reply)
    if not m:
        return (None, None)
    try:
        az = int(m.group(1))
        el = int(m.group(2))
        az = max(0, min(450, az))
        el = max(0, min(180, el))
        return (az, el)
    except Exception:
        return (None, None)


# ==========================================
# Minimal Serial Manager (portable + simple)
# ==========================================
class SerialManager:
    """
    Barebones serial manager for GS-232B:
      - Attempts to open one of several candidate ports.
      - write_cmd("R") -> sends "R\\r\\n".
      - send_move(az, el) -> sends Wxxx yyy.
      - c2() -> sends C2 and returns one line.

    If my main has a richer serial stack, I can pass that in to run_wizard()
    and skip using this class entirely.
    """
    def __init__(self, candidates=("/dev/ttyUSB0", "/dev/ttyUSB1", "COM3", "COM4"),
                 baud=9600, timeout=1.0):
        self.candidates = list(candidates)
        self.baud = baud
        self.timeout = timeout
        self.ser = None
        self.last_open_port = None
        self._open_any()

    def _open_any(self):
        """Try last good port first, then iterate over the rest."""
        if Serial is None:
            return False
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
                except Exception:
                    pass
                print(f"[SER] Opened {p} @ {self.baud} 8N1")
                return True
            except Exception as e:
                print(f"[SER] Open {p} failed: {e}")
                self.ser = None
        return False

    def ensure_open(self):
        """If the port dropped, try to reopen. Used to keep the status banner honest."""
        if self.ser and self.ser.is_open:
            return True
        return self._open_any()

    def close(self):
        """Best-effort close on shutdown."""
        try:
            if self.ser:
                self.ser.close()
                print("[SER] Closed")
        except Exception:
            pass
        self.ser = None

    # ---- raw helpers ----
    def _write_raw(self, bcmd: bytes):
        if not self.ensure_open():
            raise SerialException("Port not open")
        self.ser.write(bcmd)
        self.ser.flush()

    def _readline(self) -> str:
        if not self.ensure_open():
            return ""
        try:
            return self.ser.readline().decode(errors="ignore").strip()
        except Exception:
            return ""

    # ---- high-level helpers ----
    def write_cmd(self, cmd_str: str, expect_reply=False, retries=1) -> str:
        """
        Send "cmd\\r\\n" to the controller. Optionally read a one-line reply.
        Includes a small retry loop to recover from transient USB hiccups.
        """
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
                time.sleep(0.25)
                self.ensure_open()
                attempt += 1
        return ""

    def send_move(self, az_deg: int, el_deg: int, echo_c2=False):
        """
        Convenience wrapper for W commands with clamping and fixed formatting.
        echo_c2=True triggers a C2 readback so I can show the result in the UI.
        """
        az = max(0, min(450, int(round(az_deg))))
        el = max(0, min(180, int(round(el_deg))))
        cmd = f"W{az:03d} {el:03d}"
        reply = self.write_cmd(cmd, expect_reply=False)
        if echo_c2:
            reply = self.write_cmd("C2", expect_reply=True)
        return cmd, reply

    def stop(self):
        """S = All stop (both axes)."""
        return self.write_cmd("S", expect_reply=False)

    def c2(self):
        """C2 = Position echo (az, el)."""
        return self.write_cmd("C2", expect_reply=True)


# ==========================
# Wizard UI + sweep thread
# ==========================
class WizardFrame(tk.Frame):
    """
    Pages:
      - Splash
      - North (W000 000)
      - South (W180 000)
      - Sweep  (X1..X4 -> R, pause with A, Complete after 360° travel)
      - Stage  (preset az every 15°)
      - Complete

    `on_complete(True)` returns control to the caller with a success flag.
    """
    def __init__(self, master, ser_mgr: SerialManager, on_complete, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.configure(bg="white")
        self.ser_mgr = ser_mgr
        self.on_complete = on_complete  # callback(bool)

        self.page = None
        self.status_var = tk.StringVar(value="")

        # Sweep thread state (so UI never blocks)
        self._sweep_thread = None
        self._sweep_stop = threading.Event()
        self._sweep_running = False
        self._sweep_paused = threading.Event()  # set() means paused

        # Container for the current page + a bottom status line
        self.container = tk.Frame(self, bg="white")
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        # Fonts + ttk styles (after a Tk root exists)
        try:
            _UI_FONT = _pick_ui_font()
            self.TITLE_FONT = (_UI_FONT, 14, "bold")
            self.BODY_FONT  = (_UI_FONT, 11)
            self.style = ttk.Style(self)
            self.style.configure("Heading.TLabel", font=self.TITLE_FONT, background="white", foreground="black")
            self.style.configure("Body.TLabel",    font=self.BODY_FONT,  background="white", foreground="black")
        except Exception:
            # If fonts/styles fail, fallback to Tk defaults.
            pass

        status_bar = tk.Frame(self, bg="white")
        status_bar.pack(fill="x", side="bottom")
        tk.Label(status_bar, textvariable=self.status_var, bg="white", fg="black").pack(anchor="w", padx=8, pady=6)

        # Start at the splash screen
        self.goto_splash()

    # ---------- Navigation helpers ----------
    def _clear_page(self):
        """Wipe the current page and reset status text."""
        for w in self.container.winfo_children():
            w.destroy()
        self.page = None
        self.status_var.set("")

    def _serial_status(self, extra=""):
        """
        Update the status banner with port state and last action.
        I call ensure_open() so I can reflect whether I’m currently connected.
        """
        ok = self.ser_mgr.ensure_open()
        port = getattr(self.ser_mgr, "last_open_port", None)
        s = f"Serial: {'OK' if ok else 'NOT CONNECTED'}"
        if port:
            s += f" | Port: {port}"
        if extra:
            s += f" | {extra}"
        self.status_var.set(s)

    def _c2_echo_label(self, parent):
        """
        Small, consistent row to display the latest C2 echo after a move.
        """
        row = tk.Frame(parent, bg="white")
        row.pack(fill="x", pady=(12, 0))
        ttk.Label(row, text="C2 Echo:", style="Body.TLabel").pack(side="left")
        echo_var = tk.StringVar(value="(none)")
        ttk.Label(row, textvariable=echo_var, style="Body.TLabel").pack(side="left", padx=8)
        return echo_var

    # ---------- Pages ----------
    def goto_splash(self):
        """Intro with safety blurb + Start/Cancel."""
        self._clear_page()
        self.page = "splash"
        f = tk.Frame(self.container, bg="white")
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Calibration Wizard", style="Heading.TLabel").pack(pady=(0, 10))
        ttk.Label(f, text="This sequence will move the array.\nMake sure the area is clear before starting.",
                  style="Body.TLabel", justify="left").pack(pady=(0, 20))

        tk.Button(f, text="Start",  width=16, command=self.goto_north).pack(pady=6)
        tk.Button(f, text="Cancel", width=16, command=lambda: self._finish(False)).pack(pady=(6, 0))

        self._serial_status()

    def goto_north(self):
        """
        Step 1: Command W000 000 (AZ=0°, EL=0°).
        Visual check: array should physically face True North.
        """
        self._clear_page()
        self.page = "north"
        f = tk.Frame(self.container, bg="white")
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Step 1: Point to TRUE NORTH", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(f, text="Sends W000 000 (Az=0°, El=0°). Verify the array faces True North.",
                  style="Body.TLabel", justify="left").pack(anchor="w", pady=(4, 10))

        buttons = tk.Frame(f, bg="white"); buttons.pack(anchor="w", pady=8)
        echo_var = self._c2_echo_label(f)

        tk.Button(buttons, text="Move (W000 000)", width=18,
                  command=lambda: self._do_move(0, 0, echo_var)).grid(row=0, column=0, padx=4, pady=4)
        tk.Button(buttons, text="Next ▶", width=12, command=self.goto_south).grid(row=0, column=1, padx=4, pady=4)
        tk.Button(buttons, text="Stop + Restart", width=16,
                  command=self._stop_and_restart).grid(row=0, column=2, padx=4, pady=4)

        self._serial_status()

    def goto_south(self):
        """
        Step 2: Command W180 000 (AZ=180°, EL=0°).
        Visual check: array should point Due South.
        """
        self._clear_page()
        self.page = "south"
        f = tk.Frame(self.container, bg="white")
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Step 2: Point to DUE SOUTH", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(f, text="Sends W180 000 (Az=180°, El=0°). Verify the array faces Due South.",
                  style="Body.TLabel", justify="left").pack(anchor="w", pady=(4, 10))

        buttons = tk.Frame(f, bg="white"); buttons.pack(anchor="w", pady=8)
        echo_var = self._c2_echo_label(f)

        tk.Button(buttons, text="Move (W180 000)", width=18,
                  command=lambda: self._do_move(180, 0, echo_var)).grid(row=0, column=0, padx=4, pady=4)
        tk.Button(buttons, text="Next ▶", width=12, command=self.goto_sweep).grid(row=0, column=1, padx=4, pady=4)
        tk.Button(buttons, text="Stop + Restart", width=16,
                  command=self._stop_and_restart).grid(row=0, column=2, padx=4, pady=4)

        self._serial_status()

    def goto_sweep(self):
        """
        Step 3: Continuous CW rotation at selected speed (X1..X4 -> R).
        - EL is forced to 0°.
        - If SIM is disabled, I poll C2 at the chosen interval and integrate
          the forward CW delta to detect when we’ve hit ~360° total.
        - If SIM is enabled, I emulate travel based on a simple deg/sec map.

        The "Complete ▶" button becomes enabled once 360° of travel is reached.
        """
        self._clear_page()
        self.page = "sweep"
        f = tk.Frame(self.container, bg="white")
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Step 3: Full 360° Sweep (Speed-Based)", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            f,
            text=("Sets elevation to 0°, selects a horizontal rotation speed (X1..X4), "
                  "then starts continuous CW rotation (R).\n"
                  "Use Stop (Pause) to pause with azimuth-only stop (A), Resume to continue, "
                  "or Stop + Restart to send S and return to Splash.\n\n"
                  "If you don't have the GS-232B connected, enable 'Simulate (no hardware)'."),
            style="Body.TLabel", justify="left"
        ).pack(anchor="w", pady=(4, 10))

        # Controls row
        controls = tk.Frame(f, bg="white"); controls.pack(anchor="w", pady=8)

        ttk.Label(controls, text="Speed:", style="Body.TLabel").grid(row=0, column=0, padx=4, sticky="w")
        speed_var = tk.StringVar(value="X2")
        tk.OptionMenu(controls, speed_var, "X1", "X2", "X3", "X4").grid(row=0, column=1, padx=4, sticky="w")

        ttk.Label(controls, text="C2 Poll (ms):", style="Body.TLabel").grid(row=0, column=2, padx=8, sticky="w")
        poll_var = tk.IntVar(value=200)
        tk.Spinbox(controls, from_=100, to=1000, increment=50, textvariable=poll_var, width=6)\
            .grid(row=0, column=3, padx=4, sticky="w")

        # Simulation checkbox (bypass C2, emulate az)
        self._simulate_var = tk.BooleanVar(value=False)
        tk.Checkbutton(controls, text="Simulate (no hardware)", variable=self._simulate_var,
                       bg="white").grid(row=0, column=4, padx=12, sticky="w")

        # Buttons row
        btns = tk.Frame(f, bg="white"); btns.pack(anchor="w", pady=10)

        self.start_btn = tk.Button(
            btns, text="Start Sweep", width=16,
            command=lambda: self._start_sweep_speed(speed_var.get(), poll_var.get())
        )
        self.start_btn.grid(row=0, column=0, padx=4, pady=4)

        self.pause_btn = tk.Button(btns, text="Stop (Pause)", width=16,
                                   state="disabled", command=self._pause_sweep_speed)
        self.pause_btn.grid(row=0, column=1, padx=4, pady=4)

        self.resume_btn = tk.Button(btns, text="Resume", width=12,
                                    state="disabled",
                                    command=lambda: self._resume_sweep_speed(speed_var.get()))
        self.resume_btn.grid(row=0, column=2, padx=4, pady=4)

        self.stop_restart_btn = tk.Button(btns, text="Stop + Restart", width=16,
                                          command=self._stop_and_restart)
        self.stop_restart_btn.grid(row=0, column=3, padx=4, pady=4)

        self.complete_btn = tk.Button(btns, text="Complete ▶", width=14,
                                      state="disabled", command=self.goto_stage)
        self.complete_btn.grid(row=0, column=4, padx=4, pady=4)

        self._serial_status()

    def goto_complete(self):
        """End page. Continue returns True to the caller to proceed to selection."""
        self._clear_page()
        self.page = "complete"
        f = tk.Frame(self.container, bg="white")
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Calibration Complete", style="Heading.TLabel").pack(pady=(0, 6), anchor="w")
        ttk.Label(f, text="Proceed to Satellite Selection.", style="Body.TLabel",
                  justify="left").pack(anchor="w", pady=(0, 12))

        btns = tk.Frame(f, bg="white"); btns.pack(anchor="w", pady=10)
        tk.Button(btns, text="Continue", width=16, command=lambda: self._finish(True)).grid(row=0, column=0, padx=4, pady=4)
        tk.Button(btns, text="Restart Wizard", width=16, command=self.goto_splash).grid(row=0, column=1, padx=4, pady=4)
        tk.Button(btns, text="Cancel", width=12, command=lambda: self._finish(False)).grid(row=0, column=2, padx=4, pady=4)

        self._serial_status()

    def goto_stage(self):
        """
        Optional staging step: park the array at a preset azimuth (every 15°).
        EL stays at 0°. Nice to leave it somewhere expected before handing
        control back to the main app.
        """
        self._clear_page()
        self.page = "stage"

        f = tk.Frame(self.container, bg="white")
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Final Staging: Choose an azimuth to park the array",
                  style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            f,
            text=("Select a preset angle (every 15°). Click Move to command Wxxx 000.\n"
                  "Finish will exit the wizard and continue to Satellite Selection."),
            style="Body.TLabel", justify="left"
        ).pack(anchor="w", pady=(4, 10))

        # 0..345 by 15°, laid out 6 columns wide
        grid = tk.Frame(f, bg="white"); grid.pack(anchor="w", pady=(0, 10))
        self._stage_az_var = tk.IntVar(value=0)

        angles = list(range(0, 360, 15))
        cols = 6
        for idx, az in enumerate(angles):
            r = idx // cols
            c = idx % cols
            tk.Radiobutton(
                grid, text=f"{az:03d}°", value=az, variable=self._stage_az_var,
                bg="white", fg="black", anchor="w", padx=6
            ).grid(row=r, column=c, sticky="w", padx=4, pady=4)

        btns = tk.Frame(f, bg="white"); btns.pack(anchor="w", pady=8)

        echo_var = self._c2_echo_label(f)

        def _do_stage_move():
            az = int(self._stage_az_var.get())
            try:
                cmd, reply = self.ser_mgr.send_move(az, 0, echo_c2=True)
                echo_var.set(reply if reply else "(no reply)")
                self._serial_status(extra=f"Staged: {cmd}")
            except Exception as e:
                echo_var.set("(error)")
                self._serial_status(extra=f"Stage move failed: {e}")

        tk.Button(btns, text="Move", width=12, command=_do_stage_move).grid(row=0, column=0, padx=4, pady=4)
        tk.Button(btns, text="Back", width=10, command=self.goto_sweep).grid(row=0, column=1, padx=4, pady=4)
        tk.Button(btns, text="Stop + Restart", width=16, command=self._stop_and_restart).grid(row=0, column=2, padx=4, pady=4)
        tk.Button(btns, text="Finish ▶", width=12, command=lambda: self._finish(True)).grid(row=0, column=3, padx=4, pady=4)

        self._serial_status()

    # ---------- Actions ----------
    def _do_move(self, az_deg, el_deg, echo_var):
        """
        One-shot W move with C2 echo pushed to the UI.
        Kept centralized so button handlers stay tiny.
        """
        try:
            cmd, reply = self.ser_mgr.send_move(az_deg, el_deg, echo_c2=True)
            echo_var.set(reply if reply else "(no reply)")
            self._serial_status(extra=f"Last: {cmd}")
        except Exception as e:
            echo_var.set("(error)")
            self._serial_status(extra=f"Move failed: {e}")

    # (old garbage) step/dwell sweep: retained for troubleshooting, not used by default.
    def _start_sweep(self, step_deg: int, dwell_ms: int):
        """Simple step-and-dwell sweep; replaced by speed-based sweep but left here for reference."""
        if self._sweep_running:
            return
        self._sweep_stop.clear()
        self._sweep_paused.clear()
        self._sweep_running = True
        try:
            self.complete_btn.configure(state="disabled")
        except Exception:
            pass

        if self.page == "sweep":
            self.start_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal")
            self.resume_btn.configure(state="disabled")

        def worker():
            last_cmd = ""
            try:
                for az in range(0, 361, max(1, int(step_deg))):
                    if self._sweep_stop.is_set():
                        break
                    # Pause gate
                    while self._sweep_paused.is_set() and not self._sweep_stop.is_set():
                        time.sleep(0.05)
                    if self._sweep_stop.is_set():
                        break

                    cmd, _ = self.ser_mgr.send_move(az, 0, echo_c2=False)
                    last_cmd = cmd

                    # Dwell with responsiveness to pause/stop
                    total_sleep = max(0, dwell_ms) / 1000.0
                    slept = 0.0
                    while slept < total_sleep:
                        if self._sweep_stop.is_set():
                            break
                        if self._sweep_paused.is_set():
                            time.sleep(0.05)
                            continue
                        time.sleep(0.05)
                        slept += 0.05

                if not self._sweep_stop.is_set():
                    self._on_sweep_done()
            except Exception as e:
                self._on_sweep_error(e)
            finally:
                self._sweep_running = False
                def _idle_ui():
                    if self.page == "sweep":
                        self.start_btn.configure(state="normal")
                        self.pause_btn.configure(state="disabled")
                        self.resume_btn.configure(state="disabled")
                self.after(0, _idle_ui)
                self._serial_status(extra=f"Last: {last_cmd}")

        self._sweep_thread = threading.Thread(target=worker, daemon=True)
        self._sweep_thread.start()
        self._serial_status(extra="Sweeping...")

    def _start_sweep_speed(self, speed_cmd: str, poll_ms: int):
        """
        Preferred sweep:
          - Apply chosen speed (X1..X4)
          - Start CW (R)
          - Integrate CW travel to 360° (C2 polling) OR emulate if SIM is on.
        Once 360° total is reached, enable the Complete button.
        """
        if self._sweep_running:
            return

        # sanitize inputs
        speed_cmd = (speed_cmd or "X2").upper()
        if speed_cmd not in ("X1", "X2", "X3", "X4"):
            speed_cmd = "X2"
        poll_ms = max(50, int(poll_ms))

        # basic, tweakable mapping of controller "speed" to deg/sec
        SPEED_DEG_PER_SEC = {"X1": 2.0, "X2": 6.0, "X3": 12.0, "X4": 24.0}

        simulate = bool(getattr(self, "_simulate_var", tk.BooleanVar(value=False)).get())

        self._sweep_stop.clear()
        self._sweep_paused.clear()
        self._sweep_running = True
        try:
            self.complete_btn.configure(state="disabled")
        except Exception:
            pass

        if self.page == "sweep":
            self.start_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal")
            self.resume_btn.configure(state="disabled")

        def worker():
            last_cmd = ""
            try:
                # 0) Initialize starting az
                start_reply = None
                az0 = None
                if not simulate:
                    start_reply = self.ser_mgr.c2()
                    az0, _ = parse_c2_az_el(start_reply)
                if az0 is None:
                    az0 = 0.0  # safe fallback

                # 1) Force elevation to 0° at current az
                try:
                    if not simulate:
                        self.ser_mgr.send_move(int(az0) % 360, 0, echo_c2=False)
                        last_cmd = f"W{int(az0)%360:03d} 000"
                    else:
                        last_cmd = f"(sim) W{int(az0)%360:03d} 000"
                except Exception:
                    pass

                # 2) Apply horizontal speed (Xn)
                if not simulate:
                    try:
                        self.ser_mgr.write_cmd(speed_cmd, expect_reply=False)
                        last_cmd = speed_cmd
                    except Exception:
                        pass
                else:
                    last_cmd = f"(sim){speed_cmd}"

                # 3) Start CW rotation (R)
                if not simulate:
                    try:
                        self.ser_mgr.write_cmd("R", expect_reply=False)
                        last_cmd = "R"
                    except Exception:
                        pass
                    self._serial_status(extra=f"Rotating CW at {speed_cmd}...")
                else:
                    self._serial_status(extra=f"(sim) Rotating CW at {speed_cmd}...")

                # 4) Poll/Emulate movement and integrate CW travel
                total_travel = 0.0
                prev_az = float(az0 % 360)

                deg_per_sec = SPEED_DEG_PER_SEC.get(speed_cmd, 6.0)
                poll_interval_s = poll_ms / 1000.0

                def cw_delta(curr, prev):
                    # Smallest forward CW delta in [0, 360)
                    return (curr - prev) % 360.0

                while not self._sweep_stop.is_set():
                    # Pause handling (send az-stop 'A' once when paused; hold until resumed)
                    if self._sweep_paused.is_set():
                        if not simulate:
                            try:
                                self.ser_mgr.write_cmd("A", expect_reply=False)
                                last_cmd = "A"
                            except Exception:
                                pass
                        time.sleep(0.05)
                        continue

                    if simulate:
                        # Emulated travel using deg/sec * poll interval
                        increment = deg_per_sec * poll_interval_s
                        curr_az = (prev_az + increment) % 360.0
                        traveled = cw_delta(curr_az, prev_az)
                        total_travel += traveled
                        prev_az = curr_az

                        if total_travel >= 360.0:
                            last_cmd = "(sim) A"
                            self._on_sweep_done()
                            break
                    else:
                        # Real hardware: poll C2 and integrate CW deltas
                        try:
                            reply = self.ser_mgr.c2()
                            az, _ = parse_c2_az_el(reply)
                            if az is not None:
                                az_f = float(az % 360)
                                dt = cw_delta(az_f, prev_az)
                                total_travel += dt
                                prev_az = az_f
                                if total_travel >= 360.0:
                                    try:
                                        self.ser_mgr.write_cmd("A", expect_reply=False)  # az stop
                                        last_cmd = "A"
                                    except Exception:
                                        pass
                                    self._on_sweep_done()
                                    break
                        except Exception:
                            # Serial hiccup; keep trying
                            pass

                    # Sleep in small steps so stop/pause stays reactive
                    slept = 0.0
                    step = 0.05
                    target = poll_interval_s
                    while slept < target and not self._sweep_stop.is_set() and not self._sweep_paused.is_set():
                        time.sleep(step)
                        slept += step

            except Exception as e:
                self._on_sweep_error(e)
            finally:
                self._sweep_running = False
                def _idle_ui():
                    if self.page == "sweep":
                        self.start_btn.configure(state="normal")
                        self.pause_btn.configure(state="disabled")
                        self.resume_btn.configure(state="disabled")
                self.after(0, _idle_ui)
                self._serial_status(extra=f"Last: {last_cmd}")

        self._sweep_thread = threading.Thread(target=worker, daemon=True)
        self._sweep_thread.start()
        self._serial_status(extra=f"{'(sim) ' if simulate else ''}Sweep running at {speed_cmd}...")

    def _pause_sweep_speed(self):
        """User pressed Stop (Pause): raise pause flag, update UI, and show status."""
        if not self._sweep_running:
            return
        self._sweep_paused.set()
        self.pause_btn.configure(state="disabled")
        self.resume_btn.configure(state="normal")
        self.start_btn.configure(state="disabled")
        self.status_var.set("Sweep paused (A sent). Press Resume to continue.")

    def _resume_sweep_speed(self, speed_cmd: str):
        """
        User pressed Resume:
        - Re-apply speed Xn
        - Re-issue R
        - Clear pause and restore UI
        """
        if not self._sweep_running:
            return
        speed_cmd = (speed_cmd or "X2").upper()
        if speed_cmd not in ("X1", "X2", "X3", "X4"):
            speed_cmd = "X2"
        try:
            self.ser_mgr.write_cmd(speed_cmd, expect_reply=False)
            self.ser_mgr.write_cmd("R", expect_reply=False)
        except Exception as e:
            self.status_var.set(f"Resume error: {e}")
            return
        self._sweep_paused.clear()
        self.pause_btn.configure(state="normal")
        self.resume_btn.configure(state="disabled")
        self.start_btn.configure(state="disabled")
        self.status_var.set(f"Resumed at {speed_cmd}...")

    def _on_sweep_done(self):
        """Enable the Complete button once 360° travel is achieved."""
        def enable_complete():
            if self.page == "sweep":
                try:
                    self.complete_btn.configure(state="normal")
                except Exception:
                    pass
                self.status_var.set("Sweep complete. You may press Complete ▶.")
        self.after(0, enable_complete)

    def _on_sweep_error(self, e):
        """Surface sweep thread exceptions to the status bar."""
        def show_err():
            self.status_var.set(f"Sweep error: {e}")
        self.after(0, show_err)

    def _stop_and_restart(self):
        """
        Emergency stop path:
        - Raise stop, clear pause, send 'S', jump back to Splash.
        """
        if self._sweep_running:
            self._sweep_stop.set()
        self._sweep_paused.clear()
        try:
            self.ser_mgr.stop()  # 'S' All Stop
        except Exception as e:
            self._serial_status(extra=f"Stop error: {e}")
        self.goto_splash()

    def _finish(self, ok: bool):
        """
        Exit the wizard:
        - Assert stop if a sweep is running.
        - Destroy my frame and call on_complete(ok) for the caller to decide next steps.
        """
        if self._sweep_running:
            self._sweep_stop.set()
        self.destroy()
        try:
            self.on_complete(bool(ok))
        except Exception:
            pass


# ==========================
# Public entry point
# ==========================
def run_wizard(root: tk.Tk, ser_mgr: SerialManager) -> bool:
    """
    Run the wizard inside an existing Tk root and SerialManager.
    Blocks until the user completes or cancels, then returns True/False.
    """
    result_holder = {"ok": False}
    done = threading.Event()

    def on_complete(ok: bool):
        result_holder["ok"] = ok
        done.set()

    # Replace whatever is in the root with this wizard
    for w in root.winfo_children():
        w.destroy()
    root.title("GS-232B Calibration Wizard")
    root.configure(bg="white")

    wf = WizardFrame(root, ser_mgr, on_complete)
    wf.pack(fill="both", expand=True)

    # Mini “modal” loop – periodically check for completion
    def check_done():
        if done.is_set():
            root.quit()  # exit the nested loop
        else:
            root.after(100, check_done)

    check_done()
    root.mainloop()
    return result_holder["ok"]


# ==========================
# Standalone for testing
# ==========================
if __name__ == "__main__":
    # Launch the wizard by itself so I can test UI + SIM mode without main.
    root = tk.Tk()
    sm = SerialManager()

    ok = run_wizard(root, sm)
    print(f"[Wizard] Completed = {ok}")

    # Close serial on exit (best effort)
    try:
        sm.close()
    except Exception:
        pass
