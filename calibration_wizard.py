#!/usr/bin/env python3
"""
GS-232B Calibration Wizard for Antenna Pointing Bringup(UI helper for main_gs232b.py)
------------------------------------------------------------------
Author: Zach Hallett

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
# _C2_RE = _C2_RE = re.compile(r'AZ\s*[:=]\s*([+\-]?\d{1,4})\D+EL\s*[:=]\s*([+\-]?\d{1,3})', re.IGNORECASE)
_C2_RE = re.compile(r'AZ\s*[:=]\s*([+\-]?\d{1,4})\D+EL\s*[:=]\s*([+\-]?\d{1,3})', re.IGNORECASE)



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

    # def _readline(self) -> str:
    #     if not self.ensure_open():
    #         return ""
    #     try:
    #         return self.ser.readline().decode(errors="ignore").strip()
    #     except Exception:
    #         return ""
    def _readline(self) -> str:
        if not self.ensure_open():
            return ""
        try:
            # Read until CR (0x0D); GS-232B commonly uses CR-only line endings
            b = self.ser.read_until(b"\r")
            if not b:
                return ""
            # Strip the trailing CR and any spurious whitespace
            return b.rstrip(b"\r").decode("ascii", errors="ignore").strip()
        except Exception:
            return ""

    # ---- high-level helpers ----
    def write_cmd(self, cmd_str: str, expect_reply=False, retries=1) -> str:
        """
        Send "cmd\\r\\n" to the controller. Optionally read a one-line reply.
        Includes a small retry loop to recover from transient USB hiccups.
        """
        # payload = (cmd_str.rstrip() + "\r\n").encode("ascii", errors="ignore")
        payload = (cmd_str.rstrip() + "\r").encode("ascii", errors="ignore")

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

        self._c2_poll_id = None
        self._c2_target_var = None  # StringVar to update with latest C2 line

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
        self._c2_target_var = None
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
        row = tk.Frame(parent, bg="white")
        row.pack(fill="x", pady=(12, 0))
        ttk.Label(row, text="C2 Echo:", style="Body.TLabel").pack(side="left")
        echo_var = tk.StringVar(value="(none)")
        ttk.Label(row, textvariable=echo_var, style="Body.TLabel").pack(side="left", padx=8)
        # Remember this var so the poller can update it globally
        self._c2_target_var = echo_var
        # Ensure the poller is running (1 Hz)
        self._start_c2_poll(1000)
        return echo_var


    def _pause_sweep(self):
        if not self._sweep_running:
            return
        self._sweep_paused.set()  # tell move_and_wait() to stop and hold
        try:
            self.pause_btn.configure(state="disabled")
            self.resume_btn.configure(state="normal")
            self.status_var.set("Paused. Rotator stopped (S). Press Resume to continue.")
        except Exception:
            pass

    def _resume_sweep(self):
        if not self._sweep_running:
            return
        self._sweep_paused.clear()  # move_and_wait() will re-issue the pending W target
        try:
            self.pause_btn.configure(state="normal")
            self.resume_btn.configure(state="disabled")
            self.status_var.set("Resuming…")
        except Exception:
            pass

    # def _start_c2_poll(self, period_ms: int = 1000):
    #     """Start/continue a 1 Hz C2 poll that updates self._c2_target_var if set."""
    #     # Avoid double-scheduling
    #     if self._c2_poll_id is not None:
    #         return
    #
    #     def _tick():
    #         # Reschedule first so exceptions don’t kill the loop
    #         self._c2_poll_id = self.after(period_ms, _tick)
    #
    #         # Only poll when we have a label to show it on and we're not in a fast sweep
    #         if self._c2_target_var is None:
    #             return
    #         if self._sweep_running:
    #             return
    #         try:
    #             reply = self.ser_mgr.c2()
    #             if reply:
    #                 self._c2_target_var.set(reply)
    #         except Exception:
    #             # keep polling; no UI spam
    #             pass
    #
    #     # Kick it off
    #     self._c2_poll_id = self.after(period_ms, _tick)


    def _start_c2_poll(self, period_ms: int = 1000):
        """Start/continue a 1 Hz C2 poll that updates self._c2_target_var if set."""
        if self._c2_poll_id is not None:
            return

        def _tick():
            self._c2_poll_id = self.after(period_ms, _tick)
            if self._c2_target_var is None:
                return
            try:
                reply = self.ser_mgr.c2()
                if reply:
                    self._c2_target_var.set(reply)
            except Exception:
                pass

        self._c2_poll_id = self.after(period_ms, _tick)

    def _stop_c2_poll(self):
        """Stop the periodic C2 poll (called on teardown or if you ever need to)."""
        if self._c2_poll_id is not None:
            try:
                self.after_cancel(self._c2_poll_id)
            except Exception:
                pass
            self._c2_poll_id = None


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
        Step 3: Full Az/El sweep with live C2 echo (1 Hz from your poller).
        - Azimuth: 0 → 360 → 0
        - Elevation: 0 → 90 → 0
        """
        self._clear_page()
        self.page = "sweep"

        f = tk.Frame(self.container, bg="white")
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Step 3: Full Az/El Sweep", style="Heading.TLabel").pack(anchor="w")

        ttk.Label(
            f,
            text=("This will:\n"
                "  1) Move to 0°,0°\n"
                "  2) Sweep AZ: 0 → 360 → 0\n"
                "  3) Sweep EL: 0 → 90 → 0\n\n"
                "C2 Echo updates once per second."),
            style="Body.TLabel",
            justify="left"
        ).pack(anchor="w", pady=(4, 10))

        # Live C2 echo (uses your 1 Hz poller via _c2_echo_label)
        echo_var = self._c2_echo_label(f)
        # Buttons row
        btns = tk.Frame(f, bg="white"); btns.pack(anchor="w", pady=10)

        self.start_btn = tk.Button(
            btns, text="Start Full Sweep", width=16,
            command=self._start_full_sweep
        )
        self.start_btn.grid(row=0, column=0, padx=4, pady=4)

        self.pause_btn = tk.Button(
            btns, text="Pause", width=12, state="disabled",
            command=self._pause_sweep
        )
        self.pause_btn.grid(row=0, column=1, padx=4, pady=4)

        self.resume_btn = tk.Button(
            btns, text="Resume", width=12, state="disabled",
            command=self._resume_sweep
        )
        self.resume_btn.grid(row=0, column=2, padx=4, pady=4)

        self.stop_restart_btn = tk.Button(
            btns, text="Stop + Restart", width=16,
            command=self._stop_and_restart
        )
        self.stop_restart_btn.grid(row=0, column=3, padx=4, pady=4)

        self.complete_btn = tk.Button(
            btns, text="Complete ▶", width=14,
            state="disabled", command=self.goto_stage
        )
        self.complete_btn.grid(row=0, column=4, padx=4, pady=4)


    def move_and_wait(self, target_az: int, target_el: int, tol_deg: int = 2, poll_s: float = 0.25, timeout_s: float = 120.0):
        """
        Send Wxxx yyy and wait until C2 reports within `tol_deg` of both targets,
        or until timeout/stop is requested.
        """
        # Command move
        self.ser_mgr.send_move(int(target_az) % 360, int(target_el), echo_c2=False)

        # Wait loop
        t0 = time.time()
        while not self._sweep_stop.is_set():
            # Timeout guard
            if time.time() - t0 > timeout_s:
                raise TimeoutError(f"Timeout waiting for W{target_az:03d} {target_el:03d}")

            # Query C2 and check tolerance
            reply = self.ser_mgr.c2()
            az, el = parse_c2_az_el(reply)
            if az is not None and el is not None:
                if abs((az % 360) - (target_az % 360)) <= tol_deg and abs(el - target_el) <= tol_deg:
                    return  # reached
            time.sleep(poll_s)


    def _start_full_sweep(self):
        """
        Run az sweep (0→360→0) then el sweep (0→90→0).
        Uses C2 polling to confirm arrival within tolerance.
        """
        if self._sweep_running:
            return

        self._sweep_stop.clear()
        self._sweep_paused.clear()
        self._sweep_running = True
        try:
            self.complete_btn.configure(state="disabled")
            self.start_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal")
            self.resume_btn.configure(state="disabled")
        except Exception:
            pass


        def worker():
            last_phase = ""
            try:
                # --- Home first ---
                last_phase = "Hom­ing to 0°,0°"
                self._serial_status(last_phase)
                self.move_and_wait(0, 0)

                # --- AZ: 0 -> 360 ---
                if self._sweep_stop.is_set(): return
                last_phase = "AZ 0° → 360°"
                self._serial_status(last_phase)
                self.move_and_wait(360, 0)

                # --- AZ: 360 -> 0 ---
                if self._sweep_stop.is_set(): return
                last_phase = "AZ 360° → 0°"
                self._serial_status(last_phase)
                self.move_and_wait(0, 0)

                # --- EL: 0 -> 90 ---
                if self._sweep_stop.is_set(): return
                last_phase = "EL 0° → 90°"
                self._serial_status(last_phase)
                self.move_and_wait(0, 90)

                # --- EL: 90 -> 0 ---
                if self._sweep_stop.is_set(): return
                last_phase = "EL 90° → 0°"
                self._serial_status(last_phase)
                self.move_and_wait(0, 0)

                # Done
                if not self._sweep_stop.is_set():
                    self._on_sweep_done()

            except Exception as e:
                self._on_sweep_error(e)
            finally:
                self._sweep_running = False
                def _restore_buttons():
                    self.start_btn.configure(state="normal")
                    self.pause_btn.configure(state="disabled")
                    self.resume_btn.configure(state="disabled")
                self.after(0, _restore_buttons)

                self.after(0, lambda: self.start_btn.configure(state="normal"))
                self._serial_status(extra=f"Last phase: {last_phase}")

        threading.Thread(target=worker, daemon=True).start()
        self._serial_status(extra="Full sweep running…")


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
