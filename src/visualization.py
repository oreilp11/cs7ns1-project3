from flask import Flask, render_template, jsonify
import update_satellite_positions
from find_shortest_way import find_shortest_path
import csv
import os
from wind_farm import WindTurbineNode

base_path = os.path.dirname(os.path.dirname(__file__))
static_path = os.path.join(base_path, 'static')
template_path = os.path.join(base_path, 'templates')
devices_path = os.path.join(base_path, 'assets', 'devices_ip.csv')

app = Flask(__name__, template_folder=template_path, static_folder=static_path)

# Initialize WindTurbineNode to access generate_turbine_data
turbine_node = WindTurbineNode()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_positions')
def get_positions():
    positions = update_satellite_positions.calculate_satellite_positions(range(1,11))
    for pos in positions:
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
    data = turbine_node.generate_turbine_data()
    turbine_key = f'turbine {turbine_id}'
    if turbine_key in data['turbines']:
        single_turbine_data = data['turbines'][turbine_key]
        single_turbine_data['timestamp'] = data['timestamp']
        return jsonify(single_turbine_data)
    else:
        return jsonify({'error': 'Turbine ID not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
