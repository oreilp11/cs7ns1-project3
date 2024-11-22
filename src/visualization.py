# Written by Emile Delmas & Arnav Tripathy
from flask import Flask, render_template, jsonify
import update_satellite_positions
from find_shortest_way import find_shortest_path
import csv
import os


base_path = os.path.dirname(os.path.dirname(__file__))
static_path = os.path.join(base_path, 'static')
template_path = os.path.join(base_path, 'templates')
devices_path = os.path.join(base_path, 'assets', 'devices_ip.csv')

app = Flask(__name__, template_folder=template_path, static_folder=static_path)

# Remove initialization of WindTurbineNode
# turbine_node = WindTurbineNode()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_positions')
def get_positions():
    positions = update_satellite_positions.calculate_satellite_positions(range(1,11))
    for pos in positions:
        if pos['id'] == 0:
            pos['name'] = "Windfarm"
        elif pos['id'] == -1:
            pos['name'] = "Ground Station"
        else:
            pos['name'] = f"Satellite {pos['id']}"

    return jsonify(positions)

@app.route('/get_shortest_path')
def get_shortest_path():
    positions = update_satellite_positions.calculate_satellite_positions(range(1,11))
    path_nodes = find_shortest_path(positions, 0, -1)[0]
    if not path_nodes:
        return jsonify([])

    path_coordinates = []
    for node in path_nodes:
        node_pos = next(pos for pos in positions if pos['id'] == node)
        path_coordinates.append({
            'lat': float(node_pos['lat']),
            'long': float(node_pos['long'])
        })

    return jsonify(path_coordinates)

@app.route('/dashboard/<int:turbine_id>')
def dashboard(turbine_id):
    return render_template('dashboard.html', turbine_id=turbine_id)

@app.route('/get_turbine_data/<int:turbine_id>')
def get_turbine_data(turbine_id):
    csv_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'turbine_data.csv')
    if not os.path.exists(csv_file_path):
        return jsonify({'error': 'No data available'}), 404

    # Read the latest data for the specified turbine
    latest_data = None
    with open(csv_file_path, mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if int(row['turbine'].split(' ')[1]) == turbine_id:
                latest_data = row

    if latest_data:
        return jsonify({
            'timestamp': float(latest_data['timestamp']),
            'temperature': float(latest_data['temperature']),
            'pressure': float(latest_data['pressure']),
            'wind_speed': float(latest_data['wind_speed']),
            'power_output': float(latest_data['power_output'])
        })
    else:
        return jsonify({'error': 'Turbine ID not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
