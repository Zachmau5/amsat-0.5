import numpy as np
from urllib.request import urlopen
from bs4 import BeautifulSoup

'''
Decode 2-line elsets with the following key:
1 AAAAAU 00  0  0 BBBBB.BBBBBBBB  .CCCCCCCC  00000-0  00000-0 0  DDDZ
2 AAAAA EEE.EEEE FFF.FFFF GGGGGGG HHH.HHHH III.IIII JJ.JJJJJJJJKKKKKZ
KEY: A-CATALOGNUM B-EPOCHTIME C-DECAY D-ELSETNUM E-INCLINATION F-RAAN
G-ECCENTRICITY H-ARGPERIGEE I-MNANOM J-MNMOTION K-ORBITNUM Z-CHECKSUM
'''

def ParseTwoLineElementFile():
    """
    Reads amateur satellite TLEs from celestrak.org and returns a dictionary:

    results_dict[sat_name] = np.array([ epoch_year, epoch_days, inclination, RAAN,
                                        eccentricity, arg_perigee, mean_anomaly,
                                        mean_motion, ftdmm ])

    Each entry is a float. The user can then convert these to radians as needed.
    """

    # Website to scrape for TLE data
    sat_page = 'https://www.celestrak.com/NORAD/elements/amateur.txt'

    # Open the website (directly, or via proxy if needed).
    # Proxy logic is commented out since it's optional.
    '''
    proxy = urllib.request.ProxyHandler({'https': 'https://llproxy:8080'})
    opener = urllib.request.build_opener(proxy)
    urllib.request.install_opener(opener)
    page = urllib.request.urlopen(sat_page)
    '''

    page = urlopen(sat_page)

    # Use BeautifulSoup to parse the data
    soup = BeautifulSoup(page, 'html.parser')
    lines = soup.get_text().splitlines()

    counter = 0
    # We'll store ephemeral results in this array of 9 floats
    results = np.zeros(9, dtype=float)
    results_dict = {}

    for line in lines:
        # Split by whitespace
        split_line = line.split()

        if counter == 0:
            # This is the satellite name line
            # The first token is the sat name
            if len(split_line) > 0:
                sat_name = split_line[0].strip('\n')
            else:
                sat_name = "UNKNOWN"

        elif counter == 1:
            # TLE line 1
            # remove empty strings if any (in Python 3, filter returns an iterator)
            split_line = list(filter(None, split_line))

            # Example line:
            # 1 25544U 98067A   23140.61002778  .00000266  00000-0  14404-4 0  9995
            # split_line might be:
            # ['1', '25544U', '98067A', '23140.61002778', '.00000266', '00000-0', '14404-4', '0', '9995']

            # epoch_info is like "23140.61002778"
            epoch_info = split_line[3]
            epoch_year = epoch_info[0:2]      # e.g. "23"
            epoch_remainder = epoch_info[2:]  # e.g. "140.61002778"

            # ftdmm (first time derivative of mean motion / 2)
            # Typically in TLE line 1 around index 4
            ftdmm = split_line[4]

            # (We do not parse stdmm or bstar here, but you could if needed)

            # Store in results array
            results[0] = float(epoch_year)
            results[1] = float(epoch_remainder)
            # We'll store ftdmm in results[8]
            results[8] = float(ftdmm)

        elif counter == 2:
            # TLE line 2
            # remove empty strings
            split_line = list(filter(None, split_line))

            # Example line:
            # 2 25544  51.6431 294.3246 0005576  54.8435  59.0689 15.50052960398583
            # Indexing might be:
            # [0] = '2'
            # [1] = '25544'
            # [2] = '51.6431'   (inclination)
            # [3] = '294.3246'  (RAAN)
            # [4] = '0005576'   (ecc without decimal)
            # [5] = '54.8435'   (arg of perigee)
            # [6] = '59.0689'   (mean anomaly)
            # [7] = '15.50052960398583' (mean motion)

            inclination = split_line[2]
            raan = split_line[3]

            # Eccentricity might be missing the decimal point
            ecc_str = split_line[4]
            if not ecc_str.startswith('.'):
                ecc_str = '.' + ecc_str

            arg_perigee = split_line[5]
            mean_anomaly = split_line[6]
            mean_motion = split_line[7]

            results[2] = float(inclination)
            results[3] = float(raan)
            results[4] = float(ecc_str)
            results[5] = float(arg_perigee)
            results[6] = float(mean_anomaly)
            results[7] = float(mean_motion)

            # Now store in the dictionary
            results_dict[sat_name] = results

            # Reset array for the next satellite
            results = np.zeros(9, dtype=float)

        # Increment counter & wrap
        counter += 1
        counter = np.mod(counter, 3)

    return results_dict

# If you want to test locally:
# if __name__ == "__main__":
#     d = ParseTwoLineElementFile()
#     for sat in d:
#         print(sat, d[sat])
