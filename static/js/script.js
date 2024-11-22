// Written by Emile Delmas
// Initialize map
const map = L.map('map').setView([53, -17], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Device markers storage - modified to store both circle and label
const markers = {};
let rangeCircle = null;
let pathLines = [];

// Update marker positions
function updateMarkers() {
    fetch('/get_positions')
        .then(response => response.json())
        .then(devices => {
            // Find ground station and windfarm
            const groundStation = devices.find(d => d.id === -1);
            const windfarm = devices.find(d => d.id === 0);

            // Calculate middle point
            const midLat = (groundStation.lat + windfarm.lat) / 2;
            const midLong = (groundStation.long + windfarm.long) / 2;

            // Update or create range circle (750km ≈ 6.75 degrees)
            if (rangeCircle) {
                rangeCircle.setLatLng([midLat, midLong]);
            } else {
                rangeCircle = L.circle([midLat, midLong], {
                    color: 'grey',
                    fillColor: 'none',
                    fillOpacity: 0,
                    radius: 750000  // 750km in meters
                }).addTo(map);
            }

            devices.forEach(device => {
                if (markers[device.id]) {
                    // Update existing markers
                    markers[device.id].circle.setLatLng([device.lat, device.long]);
                    markers[device.id].label.setLatLng([device.lat, device.long]);
                } else {
                    // Create circle marker
                    const circleMarker = L.circleMarker([device.lat, device.long], {
                        radius: 10,
                        color: 'blue',
                        fillColor: '#f03',
                        fillOpacity: 0.5
                    }).addTo(map);

                    // Create label
                    const label = L.divIcon({
                        className: 'device-label',
                        html: `<div style="text-align: center; font-size: 12px;">${device.name || 'Device ' + device.id}</div>`,
                        iconSize: [50, 100]
                    });

                    const labelMarker = L.marker([device.lat, device.long], { icon: label }).addTo(map);

                    // Store both markers
                    markers[device.id] = {
                        circle: circleMarker,
                        label: labelMarker
                    };
                }
            });
        });
}

function updateShortestPath() {
    // Remove existing path lines
    pathLines.forEach(line => map.removeLayer(line));
    pathLines = [];

    fetch('/get_shortest_path')
        .then(response => response.json())
        .then(coordinates => {
            // Draw lines between consecutive points
            for (let i = 0; i < coordinates.length - 1; i++) {
                const line = L.polyline(
                    [
                        [coordinates[i].lat, coordinates[i].long],
                        [coordinates[i + 1].lat, coordinates[i + 1].long]
                    ],
                    {
                        color: 'red',
                        weight: 3,
                        dashArray: '5, 10'
                    }
                ).addTo(map);
                pathLines.push(line);
            }
        });
}

// Update positions every 500ms
setInterval(() => {
    updateMarkers();
    updateShortestPath();
}, 500);
updateMarkers();
updateShortestPath();
