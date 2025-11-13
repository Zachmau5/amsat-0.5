#!/usr/bin/env python3
"""
GS-232B command formatting and parsing helpers.
Pure functions only — no serial I/O here.
"""

def format_move(az_deg: float, el_deg: float) -> str:
    """
    Format an absolute move command.

    Example:
        >>> format_move(180.2, 45.7)
        'W180 046'
    """
    az = int(round(az_deg))
    el = int(round(el_deg))
    return f"W{az:03d} {el:03d}"


def parse_c2(reply: str) -> tuple[float, float] | None:
    """
    Parse a C2 status reply of the form '+0aaa+0eee' -> (az, el).

    Example:
        >>> parse_c2('+0180+0090')
        (180.0, 90.0)
    """
    if not reply or len(reply) < 8:
        return None
    try:
        # remove CR/LF and spaces
        reply = reply.strip()
        # typical form: '+0aaa+0eee' or '+180+090'
        parts = reply.replace('+0', '+').split('+')
        nums = [float(p) for p in parts if p]
        if len(nums) == 2:
            return nums[0], nums[1]
    except Exception:
        pass
    return None


# Common static commands
STOP_CMD = "S"       # Stop motion
STATUS_CMD = "C2"    # Query az/el
HELP_CMD = "H"       # Help page 1
HELP2_CMD = "H2"     # Help page 2
MODE_450_CMD = "P45" # Enable 450° mode (optional)
