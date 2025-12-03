import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Default marker icon fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

// Custom icons for bus and tram
const busIcon = new L.Icon({
  iconUrl: '/bus-front.svg',
  iconSize: [25, 25],
  iconAnchor: [12, 25],
  popupAnchor: [0, -20],
});

const tramIcon = new L.Icon({
  iconUrl: '/tram-front.svg',
  iconSize: [25, 25],
  iconAnchor: [12, 25],
  popupAnchor: [0, -20],
});

const stopIcon = new L.Icon({
  iconUrl: '/milestone.svg',
  iconSize: [25, 25],
  iconAnchor: [12, 25],
  popupAnchor: [0, -20],
});

export default function OpenStreetMap({
  center = [51.758821, 19.456283],
  zoom = 13,
  vehicles = [],
  stops = []
}) {
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      scrollWheelZoom={true}
      style={{ height: "100%", width: "100%" }}
      className="rounded-2xl shadow"
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Vehicle markers */}
      {vehicles.map((v) => (
        <Marker
          key={v.entity_id}
          position={[v.lat, v.lng]}
          icon={v.route_type.includes("autobus") ? busIcon : tramIcon}
        >
          <Popup>{v.route_type.toUpperCase()} {v.entity_id}</Popup>
        </Marker>
      ))}

      {/* Stop markers */}
      {stops.map((s) => (
        <Marker 
          key={s.id} 
          position={[s.lat, s.lng]}
          icon={stopIcon}
        >
          <Popup>{s.name}</Popup>
        </Marker>
      ))}

      {/* Center marker */}
      <Marker position={center}>
        <Popup>You are here {center}</Popup>
      </Marker>
    </MapContainer>
  );
}
