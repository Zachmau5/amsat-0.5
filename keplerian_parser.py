import numpy as np

def ParseTwoLineElementFile(filename="amateur.tle"):
    """
    Parses a local TLE text file and returns a dictionary:
    results_dict[sat_name] = np.array([...])
    """

    with open(filename, 'r') as f:
        lines = f.read().splitlines()

    counter = 0
    results = np.zeros(9, dtype=float)
    results_dict = {}

    for line in lines:
        split_line = line.split()

        if counter == 0:
            sat_name = line.strip() if line.strip() else "UNKNOWN"

        elif counter == 1:
            split_line = list(filter(None, split_line))

            epoch_info = split_line[3]
            epoch_year = epoch_info[0:2]
            epoch_remainder = epoch_info[2:]
            ftdmm = split_line[4]

            results[0] = float(epoch_year)
            results[1] = float(epoch_remainder)
            results[8] = float(ftdmm)

        elif counter == 2:
            split_line = list(filter(None, split_line))

            inclination = split_line[2]
            raan = split_line[3]

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

            results_dict[sat_name] = results
            results = np.zeros(9, dtype=float)

        counter += 1
        counter = counter % 3

    return results_dict
