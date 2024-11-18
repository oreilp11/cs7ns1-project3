import math
from datetime import datetime
import numpy as np
import os
import csv  # Added import for csv

def read_static_positions():
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "device_positions.csv")

    static_positions = []
    with open(csv_path, mode='r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row['id'] = int(row['id'])
            row['lat'] = float(row['lat'])
            row['long'] = float(row['long'])
            row['alt'] = float(row.get('alt', 0))  # Ensure 'alt' is a float
            static_positions.append(row)

    ground_station = next(pos for pos in static_positions if pos['id'] == -1)
    windfarm = next(pos for pos in static_positions if pos['id'] == 0)
    return ground_station, windfarm

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon2

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c

def calculate_satellite_positions(device_ids):
    ground_station, windfarm = read_static_positions()

    # Calculate middle point
    mid_lat = (ground_station['lat'] + windfarm['lat']) / 2
    mid_long = (ground_station['long'] + windfarm['long']) / 2

    # Get current time
    now = datetime.now()
    time_factor = (now.minute % 6) * 60 + now.second

    # Parameters for satellite positioning
    altitude = 500  # km
    satellites = []

    # remove 0 and -1 from device_ids
    device_ids = [i for i in device_ids if i not in [0, -1]]

    for i in device_ids:
        satellite_id = i
        np.random.seed(satellite_id)
        start_radius = 750 / 111  # Start from ~750 km from the center

        # Find two random points on the circle ensuring the distance between them is at least the radius
        angle1 = np.random.uniform(-math.pi/4, 3*math.pi/4)
        angle2 = (angle1 + math.pi) % (2 * math.pi)  # Ensure angle2 is at least 180 degrees apart from angle1

        point1_lat = mid_lat + start_radius * math.sin(angle1)
        point1_long = mid_long + (start_radius / math.cos(math.radians(mid_lat))) * math.cos(angle1)
        point2_lat = mid_lat + start_radius * math.sin(angle2)
        point2_long = mid_long + (start_radius / math.cos(math.radians(mid_lat))) * math.cos(angle2)

        # Calculate position on the line between the two points
        t = (time_factor + i*30) % 360 / 360
        new_lat = point1_lat + t * (point2_lat - point1_lat)
        new_long = point1_long + t * (point2_long - point1_long)

        satellites.append({
            'id': satellite_id,
            'long': new_long,
            'lat': new_lat,
            'alt': altitude
        })

    # Return all positions including ground station and windfarm
    return [ground_station, windfarm] + satellites

