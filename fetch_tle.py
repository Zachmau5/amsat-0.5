# """
# fetch_tle.py
#
# This module fetches Two-Line Element (TLE) data from a specified URL and saves the data to a local file.
# TLE data (orbital element sets for satellites) are retrieved from services like CelesTrak.
#
# Key Functionality:
#     - Uses urllib.request to send an HTTP GET request with a User-Agent header (to avoid being blocked).
#     - Reads the TLE data from the remote server, decodes it (assuming UTF-8), and writes it to a file.
#     - Prints a success or error message based on the result.
#
# Usage:
#     Run this module as a standalone script; it will fetch the TLE data from the provided URL and
#     save it under the filename provided.
#
# Example:
#     > python fetch_tle.py
#
# Dependencies:
#     - urllib.request: For making HTTP requests
# """
#
# from urllib.request import Request, urlopen
#
# def fetch_and_save_tle(url, filename):
#     """
#     Fetch TLE data from a URL and save it to a local file.
#
#     Parameters:
#         url (str): The URL of the TLE data source (e.g., a CelesTrak URL).
#         filename (str): The local filename to save the TLE data.
#
#     Process:
#         1. Create an HTTP Request with a custom 'User-Agent' header.
#         2. Attempt to open the URL and read the response.
#         3. Decode the byte stream to a string using UTF-8.
#         4. Write the TLE data string to a local file specified by 'filename'.
#         5. Print a success message indicating where the data was saved.
#         6. If any exception occurs during the fetch or file operation,
#            catch it and print an error message.
#
#     Returns:
#         None
#     """
#     req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
#     try:
#         with urlopen(req) as response:
#             data = response.read().decode('utf-8')
#         with open(filename, 'w') as f:
#             f.write(data)
#         print(f"[you're a wizard harry] TLE data saved to {filename}")
#     except Exception as e:
#         print(f"[oof] Failed to fetch TLE data: {e}")
#
# if __name__ == "__main__":
#     # URL for TLE data from CelesTrak (Amateur satellites)
#     tle_url = "https://www.celestrak.com/NORAD/elements/amateur.txt"
#     output_filename = "amateur.tle"
#
#     fetch_and_save_tle(tle_url, output_filename)
#
# from urllib.request import Request, urlopen
#
# GROUP_URLS = {
#     "Amateur": "https://celestrak.org/NORAD/elements/gp.php?GROUP=amateur&FORMAT=tle",
#     "NOAA":    "https://celestrak.org/NORAD/elements/gp.php?GROUP=noaa&FORMAT=tle",
#     "GOES":    "https://celestrak.org/NORAD/elements/gp.php?GROUP=goes&FORMAT=tle",
#     "Weather": "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle",
# }
#
# def fetch_and_save_tle(url, filename):
#     """Fetch TLE data from a URL and save it to a local file."""
#     req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
#     try:
#         with urlopen(req) as response:
#             data = response.read().decode('utf-8')
#         with open(filename, 'w') as f:
#             f.write(data)
#         print(f"[you're a wizard harry] TLE data saved to {filename}")
#     except Exception as e:
#         print(f"[oof] Failed to fetch TLE data: {e}")
#
# def fetch_group(group_name: str) -> str:
#     """
#     Fetch a group (Amateur, NOAA, GOES, Weather).
#     Saves as <group>.tle and returns filename.
#     """
#     if group_name not in GROUP_URLS:
#         raise ValueError(f"Unknown group: {group_name}")
#     url = GROUP_URLS[group_name]
#     filename = f"{group_name.lower()}.tle"
#     fetch_and_save_tle(url, filename)
#     return filename
#
# if __name__ == "__main__":
#     # Example: fetch Amateur TLEs
#     fname = fetch_group("Amateur")
#     print(f"Saved to {fname}")
from urllib.request import Request, urlopen

GROUP_URLS = {
    "Amateur": "https://celestrak.org/NORAD/elements/gp.php?GROUP=AMATEUR&FORMAT=TLE",
    "NOAA":    "https://celestrak.org/NORAD/elements/gp.php?GROUP=NOAA&FORMAT=TLE",
    "GOES":    "https://celestrak.org/NORAD/elements/gp.php?GROUP=GOES&FORMAT=TLE",
    "Weather": "https://celestrak.org/NORAD/elements/gp.php?GROUP=WEATHER&FORMAT=TLE",
    "CUBESAT": "https://celestrak.org/NORAD/elements/gp.php?GROUP=CUBESAT&FORMAT=TLE",
    "SATNOGS": "https://celestrak.org/NORAD/elements/gp.php?GROUP=satnogs&FORMAT=TLE",
}


def fetch_and_save_tle(url, filename):
    """Fetch TLE data from a URL and save it to a local file."""
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urlopen(req) as response:
            data = response.read().decode('utf-8')
        with open(filename, 'w') as f:
            f.write(data)
        # print(f"[you're a wizard harry] TLE data saved to {filename}")
    except Exception as e:
        print(f"[oof] Failed to fetch TLE data: {e}")

def fetch_group(group_name: str) -> str:
    """
    Fetch a group (Amateur, NOAA, GOES, Weather, AMSAT).
    Saves as <group>.tle and returns filename.
    """
    if group_name not in GROUP_URLS:
        raise ValueError(f"Unknown group: {group_name}")
    url = GROUP_URLS[group_name]
    filename = f"{group_name.lower()}.tle"
    fetch_and_save_tle(url, filename)
    return filename

if __name__ == "__main__":
    # Example: fetch AMSAT TLEs
    fname = fetch_group("Amateur")
    print(f"Saved to {fname}")


