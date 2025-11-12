 
#!/usr/bin/env python3
"""
test_pass_visibility.py

Standalone tester for pass_visibility.compute_pass_visibility_for_file.

Uses your existing fetch_tle.fetch_group to get a TLE file,
then prints any satellites with passes in the next 30 minutes.
"""

from datetime import datetime

from fetch_tle import fetch_group
from pass_visibility import compute_pass_visibility_for_file

# Same QTH you use in main
MY_LAT = 41.19502233287143
MY_LON = -111.94128097234622


def main():
    print("=== Fetching TLE group: Amateur ===")
    tle_path = fetch_group("Amateur")
    print(f"Using TLE file: {tle_path}")

    print("\n=== Computing passes for next 30 minutes ===")
    visibility = compute_pass_visibility_for_file(
        tle_path=tle_path,
        my_lat=MY_LAT,
        my_lon=MY_LON,
        window_minutes=30.0,
        min_el_deg=10.0,   # threshold for "in pass"
        dt_sec=20.0,       # coarse step is fine for planning
    )

    now = datetime.utcnow()
    print(f"UTC now: {now:%Y-%m-%d %H:%M:%S}\n")

    print("Satellites with at least one pass in next 30 minutes:")
    print("----------------------------------------------------")

    any_found = False
    for sat_name, summary in sorted(visibility.items()):
        if not summary.passes:
            continue
        any_found = True
        p = summary.passes[0]
        print(
            f"{sat_name:30s}  "
            f"start {p.start:%H:%M:%S}Z  "
            f"peak {p.peak:%H:%M:%S}Z  "
            f"end {p.end:%H:%M:%S}Z  "
            f"max_el {p.max_el_deg:5.1f} deg"
        )

    if not any_found:
        print("No passes found. Try lowering min_el_deg or extending window.")


if __name__ == "__main__":
    main()
