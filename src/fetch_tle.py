# # # """
# # # fetch_tle.py
# # #
# # # This module fetches Two-Line Element (TLE) data from a specified URL and saves the data to a local file.
# # # TLE data (orbital element sets for satellites) are retrieved from services like CelesTrak.
# # #
# # # Key Functionality:
# # #     - Uses urllib.request to send an HTTP GET request with a User-Agent header (to avoid being blocked).
# # #     - Reads the TLE data from the remote server, decodes it (assuming UTF-8), and writes it to a file.
# # #     - Prints a success or error message based on the result.
# # #
# # # Usage:
# # #     Run this module as a standalone script; it will fetch the TLE data from the provided URL and
# # #     save it under the filename provided.
# # #
# # # Example:
# # #     > python fetch_tle.py
# # #
# # # Dependencies:
# # #     - urllib.request: For making HTTP requests
# # # """
# #
# # from urllib.request import Request, urlopen
# #
# # GROUP_URLS = {
# #     "Amateur": "https://celestrak.org/NORAD/elements/gp.php?GROUP=AMATEUR&FORMAT=TLE",
# #     "NOAA":    "https://celestrak.org/NORAD/elements/gp.php?GROUP=NOAA&FORMAT=TLE",
# #     "GOES":    "https://celestrak.org/NORAD/elements/gp.php?GROUP=GOES&FORMAT=TLE",
# #     "Weather": "https://celestrak.org/NORAD/elements/gp.php?GROUP=WEATHER&FORMAT=TLE",
# #     "CUBESAT": "https://celestrak.org/NORAD/elements/gp.php?GROUP=CUBESAT&FORMAT=TLE",
# #     "SATNOGS": "https://celestrak.org/NORAD/elements/gp.php?GROUP=satnogs&FORMAT=TLE",
# # }
# #
# #
# # def fetch_and_save_tle(url, filename):
# #     """Fetch TLE data from a URL and save it to a local file."""
# #     req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
# #     try:
# #         with urlopen(req) as response:
# #             data = response.read().decode('utf-8')
# #         with open(filename, 'w') as f:
# #             f.write(data)
# #         # print(f"[you're a wizard harry] TLE data saved to {filename}")
# #     except Exception as e:
# #         print(f"[oof] Failed to fetch TLE data: {e}")
# #
# # def fetch_group(group_name: str) -> str:
# #     """
# #     Fetch a group (Amateur, NOAA, GOES, Weather, AMSAT).
# #     Saves as <group>.tle and returns filename.
# #     """
# #     if group_name not in GROUP_URLS:
# #         raise ValueError(f"Unknown group: {group_name}")
# #     url = GROUP_URLS[group_name]
# #     filename = f"{group_name.lower()}.tle"
# #     fetch_and_save_tle(url, filename)
# #     return filename
# #
# # if __name__ == "__main__":
# #     # Example: fetch AMSAT TLEs
# #     fname = fetch_group("Amateur")
# #     print(f"Saved to {fname}")
# #
# # from urllib.request import Request, urlopen
# # from pathlib import Path
# #
# # GROUP_URLS = {
# #     "Amateur": "https://celestrak.org/NORAD/elements/gp.php?GROUP=AMATEUR&FORMAT=TLE",
# #     "NOAA":    "https://celestrak.org/NORAD/elements/gp.php?GROUP=NOAA&FORMAT=TLE",
# #     "GOES":    "https://celestrak.org/NORAD/elements/gp.php?GROUP=GOES&FORMAT=TLE",
# #     "Weather": "https://celestrak.org/NORAD/elements/gp.php?GROUP=WEATHER&FORMAT=TLE",
# #     "CUBESAT": "https://celestrak.org/NORAD/elements/gp.php?GROUP=CUBESAT&FORMAT=TLE",
# #     "SATNOGS": "https://celestrak.org/NORAD/elements/gp.php?GROUP=satnogs&FORMAT=TLE",
# # }
# #
# # # Base directory for TLE files: <repo_root>/tle
# # TLE_DIR = Path(__file__).parent / "tle"
# #
# #
# # def fetch_and_save_tle(url, filename: Path):
# #     """Fetch TLE data from a URL and save it to a local file."""
# #     TLE_DIR.mkdir(exist_ok=True)
# #     req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
# #     try:
# #         with urlopen(req) as response:
# #             data = response.read().decode('utf-8')
# #         with open(filename, 'w') as f:
# #             f.write(data)
# #         # print(f"[you're a wizard harry] TLE data saved to {filename}")
# #     except Exception as e:
# #         print(f"[oof] Failed to fetch TLE data: {e}")
# #
# #
#
# import os
# from urllib.request import Request, urlopen
# from urllib.error import URLError, HTTPError
#
# def fetch_and_save_tle(url, filename, timeout=8):
#     """
#     Fetch a TLE file from a URL with a timeout.
#     If the download fails but a cached file exists, use it.
#     If the download fails and no cached file exists, raise.
#     """
#     try:
#         req = Request(url, headers={"User-Agent": "amsat-1.0"})
#         with urlopen(req, timeout=timeout) as response:
#             text = response.read().decode("utf-8")
#
#         with open(filename, "w", encoding="utf-8") as f:
#             f.write(text)
#
#         print(f"[TLE] Downloaded fresh TLE → {filename}")
#
#     except Exception as e:
#         print(f"[TLE] WARNING: Failed to download {url}: {e}")
#
#         if os.path.exists(filename):
#             print(f"[TLE] Using cached file instead → {filename}")
#         else:
#             print(f"[TLE] ERROR: No cached TLE file exists at {filename}")
#             raise
# def fetch_group(group_name: str) -> str:
#     """
#     Fetch a group (Amateur, NOAA, GOES, Weather, CUBESAT, SATNOGS).
#     Saves as tle/<group>.tle and returns the filename (string).
#     """
#     if group_name not in GROUP_URLS:
#         raise ValueError(f"Unknown group: {group_name}")
#     url = GROUP_URLS[group_name]
#     filename = TLE_DIR / f"{group_name.lower()}.tle"
#     fetch_and_save_tle(url, filename)
#     return str(filename)   # keep returning a plain string for existing callers
#
# if __name__ == "__main__":
#     fname = fetch_group("Amateur")
#     print(f"Saved to {fname}")
#
"""
fetch_tle.py

Fetches Two-Line Element (TLE) data from CelesTrak and saves to local files.

Behavior:
- Fetches by group name (Amateur, NOAA, GOES, Weather, CUBESAT, SATNOGS).
- Saves files under <repo_root>/src/tle/<group>.tle (relative to this file).
- Uses a timeout on network requests.
- If a download fails but a cached file exists, it falls back to the cached file.
"""

import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


GROUP_URLS = {
    "Amateur": "https://celestrak.org/NORAD/elements/gp.php?GROUP=AMATEUR&FORMAT=TLE",
    "NOAA":    "https://celestrak.org/NORAD/elements/gp.php?GROUP=NOAA&FORMAT=TLE",
    "GOES":    "https://celestrak.org/NORAD/elements/gp.php?GROUP=GOES&FORMAT=TLE",
    "Weather": "https://celestrak.org/NORAD/elements/gp.php?GROUP=WEATHER&FORMAT=TLE",
    "CUBESAT": "https://celestrak.org/NORAD/elements/gp.php?GROUP=CUBESAT&FORMAT=TLE",
    "SATNOGS": "https://celestrak.org/NORAD/elements/gp.php?GROUP=satnogs&FORMAT=TLE",
}
# Base directory for TLE files: <repo_root>/src/tle
TLE_DIR = Path(__file__).parent / "tle"


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


import time

def fetch_and_save_tle(url: str, filename: Path, timeout: int = 30) -> None:
    TLE_DIR.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    try:
        req = Request(url, headers={"User-Agent": "amsat-1.0"})
        with urlopen(req, timeout=timeout) as response:
            text = response.read().decode("utf-8")

        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)

        elapsed = time.perf_counter() - start
        print(f"{GREEN}[TLE] Downloaded fresh TLE → {filename} ({elapsed:.1f}s){RESET}")

    except (URLError, HTTPError, OSError, TimeoutError) as e:
        elapsed = time.perf_counter() - start
        print(f"{RED}[TLE] WARNING: Failed to download {url} after {elapsed:.1f}s: {e}{RESET}")

        if filename.exists():
            print(f"{YELLOW}[TLE] Using cached TLE file instead → {filename}{RESET}")
        else:
            print(f"{RED}[TLE] ERROR: No cached TLE file exists at {filename}{RESET}")
            raise

# def fetch_and_save_tle(url: str, filename: Path, timeout: int = 30) -> None:
#     """
#     Fetch a TLE file from a URL with a timeout and save it to 'filename'.
#
#     If the download fails but a cached file exists, it prints a warning and
#     keeps the cached file. If the download fails and no cached file exists,
#     it raises the exception.
#     """
#     # Make sure the directory exists
#     TLE_DIR.mkdir(parents=True, exist_ok=True)
#
#     try:
#         req = Request(url, headers={"User-Agent": "amsat-1.0"})
#         with urlopen(req, timeout=timeout) as response:
#             text = response.read().decode("utf-8")
#
#         with open(filename, "w", encoding="utf-8") as f:
#             f.write(text)
#
#         # print(f"[TLE] Downloaded fresh TLE → {filename}")
#         print(f"{GREEN}[TLE] Downloaded fresh TLE → {filename}{RESET}")
#
#     except (URLError, HTTPError, OSError, TimeoutError) as e:
#         # print(f"[TLE] WARNING: Failed to download {url}: {e}")
#         print(f"{RED}[TLE] WARNING: Failed to download {url}: {e}{RESET}")
#
#         if filename.exists():
#             print(f"[TLE] Using cached TLE file instead → {filename}")
#         else:
#             print(f"[TLE] ERROR: No cached TLE file exists at {filename}")
#             raise


def fetch_group(group_name: str, timeout: int = 30) -> str:
    """
    Fetch a TLE group (Amateur, NOAA, GOES, Weather, CUBESAT, SATNOGS).

    Returns the path to the TLE file as a string.
    """
    if group_name not in GROUP_URLS:
        raise ValueError(f"Unknown group: {group_name}")

    url = GROUP_URLS[group_name]
    filename = TLE_DIR / f"{group_name.lower()}.tle"
    fetch_and_save_tle(url, filename, timeout=timeout)
    return str(filename)

    """
    Fetch a TLE group (Amateur, NOAA, GOES, Weather, CUBESAT, SATNOGS).

    Returns the path to the TLE file as a string.
    """
    if group_name not in GROUP_URLS:
        raise ValueError(f"Unknown group: {group_name}")

    url = GROUP_URLS[group_name]
    filename = TLE_DIR / f"{group_name.lower()}.tle"
    fetch_and_save_tle(url, filename, timeout=timeout)
    return str(filename)


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    fname = fetch_group("Amateur")
    print(f"Saved to {fname}")
