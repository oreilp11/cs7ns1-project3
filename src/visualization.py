from flask import Flask, render_template, jsonify
import update_cluster_positions
from find_shortest_way import find_shortest_path

app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_positions')
def get_positions():
    positions = update_cluster_positions.update_positions()
    return jsonify(positions)

@app.route('/get_shortest_path')
def get_shortest_path():
    positions = update_cluster_positions.get_current_positions()
    path_nodes = find_shortest_path(positions, 0, -1)
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
