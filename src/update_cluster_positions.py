import math
from datetime import datetime
import numpy as np
import pandas as pd

def read_static_positions():
    df = pd.read_csv('../assets/device_positions.csv')
    static_positions = df[df['id'].isin([-1, 0])].to_dict('records')
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

def calculate_cluster_positions():
    n_clusters = 10
    ground_station, windfarm = read_static_positions()

    # Calculate middle point
    mid_lat = (ground_station['lat'] + windfarm['lat']) / 2
    mid_long = (ground_station['long'] + windfarm['long']) / 2

    # Get current time
    now = datetime.now()
    time_factor = (now.minute % 3) * 60 + now.second

    # Parameters for cluster positioning
    altitude = 500  # km
    clusters = []

    for i in range(n_clusters):
        cluster_id = i + 1
        np.random.seed(cluster_id)
        start_radius = 750 / 111  # Start from ~750 km from the center

        # Find two random points on the circle
        angle1 = np.random.uniform(0, 2 * math.pi)
        angle2 = np.random.uniform(0, 2 * math.pi)
        point1_lat = mid_lat + start_radius * math.sin(angle1)
        point1_long = mid_long + (start_radius / math.cos(math.radians(mid_lat))) * math.cos(angle1)
        point2_lat = mid_lat + start_radius * math.sin(angle2)
        point2_long = mid_long + (start_radius / math.cos(math.radians(mid_lat))) * math.cos(angle2)

        # Calculate position on the line between the two points
        t = (time_factor + i*15) % 180 / 180
        new_lat = point1_lat + t * (point2_lat - point1_lat)
        new_long = point1_long + t * (point2_long - point1_long)

        clusters.append({
            'id': cluster_id,
            'long': new_long,
            'lat': new_lat,
            'alt': altitude
        })

    # Return all positions including ground station and windfarm
    return [ground_station, windfarm] + clusters
