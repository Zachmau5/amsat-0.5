import numpy as np

def ParseTwoLineElementFile(filename="amateur.tle"):
    """
    Parses a local Two-Line Element (TLE) text file and returns a dictionary
    mapping each satellite's name to a NumPy array containing its orbital elements.

    The TLE file is assumed to be organized in sets of three lines per satellite:
        Line 0: Satellite name (if blank, it defaults to "UNKNOWN")
        Line 1: First data line containing:
                    - Satellite catalog number and classification
                    - Launch information
                    - Epoch (year and fractional day) in the 4th field (split_line[3])
                    - Drag term (B* term) in the 5th field (split_line[4])
        Line 2: Second data line containing:
                    - Orbit inclination (in degrees, field 3)
                    - Right Ascension of the Ascending Node (RAAN, field 4)
                    - Eccentricity (field 5, with an assumed missing decimal point)
                    - Argument of perigee (field 6)
                    - Mean anomaly (field 7)
                    - Mean motion (field 8)

    The parsed data array (results) is organized as follows:
        Index 0: Epoch year (from the first two digits of the epoch field)
        Index 1: Epoch remainder (fractional day from the epoch field)
        Index 2: Inclination (in degrees)
        Index 3: RAAN (in degrees)
        Index 4: Eccentricity (as a decimal, e.g., 0.0008070)
        Index 5: Argument of perigee (in degrees)
        Index 6: Mean anomaly (in degrees)
        Index 7: Mean motion (in revolutions per day)
        Index 8: Drag term (B*, in scientific notation)

    Parameters:
        filename (str): The path to the TLE file to be parsed.
                        Default is "amateur.tle".

    Returns:
        results_dict (dict): A dictionary where the keys are satellite names
                             and the values are NumPy arrays of shape (9,)
                             containing the orbital elements in the order described above.

    Processing Details:
        - The file is read line-by-line.
        - A counter is used to group three lines together:
              0: Satellite name (trimmed)
              1: First data line (extract epoch information and drag term)
              2: Second data line (extract inclination, RAAN, eccentricity, argument of perigee,
                 mean anomaly, and mean motion)
        - For the epoch from line 1:
              * Field at index 3 provides epoch information as a string in the format "YYDDD.DDDDDDDD":
                    - The first two characters (epoch_year) represent the last two digits of the year.
                    - The remaining characters (epoch_remainder) represent the day of year with fractional
                      portion.
              * The drag term (B*) is extracted from field index 4.
        - For the second data line:
              * Field 2 gives the inclination.
              * Field 3 gives the RAAN.
              * Field 4 provides the eccentricity without an explicit decimal point.
                If the eccentricity string does not start with a period, a period is prepended.
              * Fields 5, 6, and 7 give the argument of perigee, mean anomaly, and mean motion,
                respectively.
        - These values are stored sequentially in a NumPy array named "results".
        - After processing a group of three lines, the array is added to a dictionary keyed by
          the satellite name.
        - The array "results" is then reset to zeros, and the process repeats.

    Example Usage:
        >>> tle_data = ParseTwoLineElementFile("amateur.tle")
        >>> print(tle_data["ISS (ZARYA)"])

    Note:
        This function expects that the TLE file is properly formatted according to the standard TLE format.
    """

    # Open and read the file, splitting into separate lines
    with open(filename, 'r') as f:
        lines = f.read().splitlines()

    # Initialize the line counter and temporary array for storing 9 elements
    counter = 0
    results = np.zeros(9, dtype=float)
    results_dict = {}

    # Process the file line-by-line, grouping every 3 lines
    for line in lines:
        split_line = line.split()

        if counter == 0:
            # First line: Satellite name (or "UNKNOWN" if blank)
            sat_name = line.strip() if line.strip() else "UNKNOWN"

        elif counter == 1:
            # Second line: Contains the epoch and drag term.
            # The epoch info is in the fourth field (index 3).
            split_line = list(filter(None, split_line))
            epoch_info = split_line[3]  # Expected format: "YYDDD.DDDDDDDD"
            epoch_year = epoch_info[0:2]      # Extract "YY"
            epoch_remainder = epoch_info[2:]    # Extract "DDD.DDDDDDDD"
            ftdmm = split_line[4]               # Drag term

            results[0] = float(epoch_year)      # Store epoch year (last two digits)
            results[1] = float(epoch_remainder) # Store the fractional day of year
            results[8] = float(ftdmm)           # Store drag term

        elif counter == 2:
            # Third line: Contains the orbital elements:
            # Inclination, RAAN, Eccentricity, Argument of perigee,
            # Mean anomaly, and Mean motion.
            split_line = list(filter(None, split_line))
            inclination = split_line[2]  # Inclination field (degrees)
            raan = split_line[3]         # RAAN (degrees)

            # Eccentricity may be provided without a leading decimal point.
            ecc_str = split_line[4]
            if not ecc_str.startswith('.'):
                ecc_str = '.' + ecc_str

            arg_perigee = split_line[5]  # Argument of perigee (degrees)
            mean_anomaly = split_line[6] # Mean anomaly (degrees)
            mean_motion = split_line[7]  # Mean motion (rev/day)

            results[2] = float(inclination)
            results[3] = float(raan)
            results[4] = float(ecc_str)
            results[5] = float(arg_perigee)
            results[6] = float(mean_anomaly)
            results[7] = float(mean_motion)

            # Add the processed data to the dictionary, using satellite name as key.
            results_dict[sat_name] = results
            # Reset the temporary results array for the next satellite.
            results = np.zeros(9, dtype=float)

        # Increment the counter and wrap it every 3 lines
        counter += 1
        counter = counter % 3

    return results_dict
