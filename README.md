# amsatHow It Works
TLE Parsing and Keplerian Elements
TLE Data:
The TLE provides the seven key orbital elements plus epoch information:

Epoch

Inclination

RAAN (Right Ascension of the Ascending Node)

Eccentricity

Argument of Perigee

Mean Anomaly

Mean Motion
(A drag term is also provided for models such as SGP4.)

Parsing:
The keplerian_parser.py module reads the TLE file and extracts these elements into a dictionary.
