import { MapContainer, TileLayer, Marker, Popup, Polyline, useMapEvents, useMap } from "react-leaflet";
import { useState, useEffect } from "react";
import { decode } from "@googlemaps/polyline-codec";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Default marker icon fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

// Custom icons
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

const startIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

const endIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

// Component to track zoom level
function ZoomHandler({ setCurrentZoom }) {
  useMapEvents({
    zoomend: (e) => {
      setCurrentZoom(e.target.getZoom());
    },
  });
  return null;
}

// Component to fit bounds when route changes
function RouteFitter({ routeData }) {
  const map = useMap();

  useEffect(() => {
    if (routeData?.route?.overview_polyline) {
      const coords = decode(routeData.route.overview_polyline);
      if (coords.length > 0) {
        const bounds = L.latLngBounds(coords);
        map.fitBounds(bounds, { padding: [50, 50] });
      }
    }
  }, [routeData, map]);

  return null;
}

export default function OpenStreetMap({
  center = [51.758821, 19.456283],
  zoom = 13,
  vehicles = [],
  stops = [],
  minZoomForStops = 14,
  selectedLines = [],
  routeData = null
}) {
  const [currentZoom, setCurrentZoom] = useState(zoom);

  // Filter vehicles by selected lines
  const filteredVehicles = selectedLines.length > 0
    ? vehicles.filter(v => selectedLines.includes(v.route_id))
    : vehicles;

  // Decode route polyline if available
  const routeCoords = routeData?.route?.overview_polyline 
    ? decode(routeData.route.overview_polyline)
    : null;

  // Get step polylines for different colors
  const stepPolylines = routeData?.route?.steps?.map(step => {
    if (step.polyline) {
      return {
        coords: decode(step.polyline),
        mode: step.mode,
        line: step.line
      };
    }
    return null;
  }).filter(Boolean) || [];

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

      <ZoomHandler setCurrentZoom={setCurrentZoom} />
      {routeData && <RouteFitter routeData={routeData} />}

      {/* Route polylines - draw step by step for different colors */}
      {stepPolylines.map((step, idx) => (
        <Polyline
          key={idx}
          positions={step.coords}
          color={step.mode === 'WALKING' ? '#4A90E2' : step.mode === 'TRANSIT' ? '#E74C3C' : '#95a5a6'}
          weight={5}
          opacity={0.7}
        />
      ))}

      {/* Route start/end markers */}
      {routeData?.route && (
        <>
          <Marker
            position={[
              routeData.route.start_location.lat,
              routeData.route.start_location.lng
            ]}
            icon={startIcon}
          >
            <Popup>Start</Popup>
          </Marker>
          <Marker
            position={[
              routeData.route.end_location.lat,
              routeData.route.end_location.lng
            ]}
            icon={endIcon}
          >
            <Popup>
              Destination<br/>
              Distance: {routeData.route.distance}<br/>
              Duration: {routeData.route.duration}
            </Popup>
          </Marker>
        </>
      )}

      {/* Transit stop markers from route */}
      {routeData?.route?.steps?.map((step, idx) => {
        if (step.mode === 'TRANSIT' && step.departure_stop_location) {
          return (
            <Marker
              key={`dep-${idx}`}
              position={[
                step.departure_stop_location.lat,
                step.departure_stop_location.lng
              ]}
              icon={stopIcon}
            >
              <Popup>
                <strong>{step.departure_stop}</strong><br/>
                Line: {step.line}<br/>
                {step.num_stops} stops
              </Popup>
            </Marker>
          );
        }
        return null;
      })}

      {/* Vehicle markers */}
      {filteredVehicles.map((v) => (
        <Marker
          key={v.entity_id}
          position={[v.latitude, v.longitude]}
          icon={v.route_type.includes("autobus") ? busIcon : tramIcon}
        >
          <Popup>
            {v.route_type.toUpperCase()} {v.route_id} <br/>
            Arrival delay: {v.arrival_delay_minutes} min  
          </Popup>
        </Marker>
      ))}

      {/* Stop markers - only show when zoomed in and no route active */}
      {!routeData && currentZoom >= minZoomForStops && stops.map((s) => (
        <Marker 
          key={s.id} 
          position={[s.lat, s.lng]}
          icon={stopIcon}
        >
          <Popup>{s.name}</Popup>
        </Marker>
      ))}

      {/* Center marker - only show when no route */}
      {!routeData && (
        <Marker position={center}>
          <Popup>You are here {center}</Popup>
        </Marker>
      )}
    </MapContainer>
  );
}