#!/usr/bin/env python3
"""
GS-232B Serial Manager (unchanged behavior, just relocated)

This wraps pyserial and provides:
- auto-open across candidate ports
- basic retries on write failures
- GS-232B command helpers: send_move(), query_c2()
"""

from __future__ import annotations

import time
import serial
from serial import Serial, SerialException
from gs232.commands import format_move


class SerialManager:
    """
    Behavior preserved from your inline class:
      - constructor tries candidates (preferring last_open_port if any)
      - _open_any() rotates through candidates until one opens
      - write_cmd() sends with CRLF, optional reply, simple retry on failure
      - send_move() formats 'Waaa eee' and (optionally) issues C2 echo
      - query_c2() sends 'C2' and returns a single reply line
    """

    def __init__(self, candidates, baud: int = 9600, timeout: float = 1.0):
        self.candidates = candidates[:]  # list of port names to try
        self.baud = baud
        self.timeout = timeout
        self.ser: Serial | None = None
        self.last_open_port: str | None = None
        self._open_any()

    def _open_any(self) -> bool:
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
                    # self._write_raw(b"P45\r\n")  # prefer 450° mode (optional)
                    # _ = self._readline()
                except Exception:
                    pass
                print(f"[SER] Opened {p} @ {self.baud} 8N1")
                return True
            except Exception as e:
                print(f"[SER] Open {p} failed: {e}")
                self.ser = None
        return False

    def ensure_open(self) -> bool:
        if self.ser and self.ser.is_open:
            return True
        return self._open_any()

    def close(self) -> None:
        try:
            if self.ser:
                self.ser.close()
                print("[SER] Closed port")
        except Exception:
            pass
        self.ser = None

    def _write_raw(self, bcmd: bytes) -> None:
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

    def write_cmd(self, cmd_str: str, expect_reply: bool = False, retries: int = 1) -> str:
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

    def send_move(self, az: float, el: float, echo_c2: bool = True) -> tuple[str, str]:
        # cmd = f"W{int(round(az)):03d} {int(round(el)):03d}"
        cmd = format_move(az, el)
        reply = ""
        try:
            _ = self.write_cmd(cmd, expect_reply=False, retries=1)
            if echo_c2:
                reply = self.write_cmd("C2", expect_reply=True, retries=1)
        except Exception:
            self.close()
            self.ensure_open()
        return cmd, reply

    def query_c2(self) -> str:
        return self.write_cmd("C2", expect_reply=True, retries=1)

    def stop(self):
        """Send 'S' (all stop) to the GS-232B."""
        return self.write_cmd("S", expect_reply=False)
