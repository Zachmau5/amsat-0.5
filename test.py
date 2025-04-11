from tle_sgp4_predictor import propagate_satellite
from datetime import datetime

line1 = "1 25544U 98067A   24100.81234567  .00005147  00000-0  95543-4 0  9990"
line2 = "2 25544  51.6406 108.3352 0004879  72.6901  48.5581 15.50083386438410"

positions = propagate_satellite(line1, line2, datetime.utcnow(), 60000000, 90)
for t, pos in positions:
    print(f"{t.isoformat()} ECEF: {pos}")
