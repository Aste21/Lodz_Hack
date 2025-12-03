import { useState, useEffect } from 'react';
import './App.css'
import OpenStreetMap from './my-components/OpenStreetMap'
import Papa from 'papaparse';

function App() {
  const [userLocation, setUserLocation] = useState([51.758821, 19.456283]); // default location
  const [loading, setLoading] = useState(true);
  const [stops, setStops] = useState([]);

  const vehicles = [
    { id: 'B12', type: 'bus', lat: 51.7511, lng: 19.452 },
    { id: 'T5', type: 'tram', lat: 51.7515, lng: 19.458 }
  ];

  useEffect(() => {
    fetch('/stops.txt')
      .then((response) => response.text())
      .then((text) => {
        const parsed = Papa.parse(text, { header: true, skipEmptyLines: true });
        const stopsData = parsed.data.map((s) => ({
          id: s.stop_id,
          name: s.stop_name,
          lat: parseFloat(s.stop_lat),
          lng: parseFloat(s.stop_lon),
        }));
        setStops(stopsData);
      })
      .catch((err) => console.error('Error loading stops:', err));
  }, []);

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setUserLocation([latitude, longitude]);
          setLoading(false);
        },
        (error) => {
          console.error('Error getting location:', error);
          setLoading(false);
        }
      );
    } else {
      console.error('Geolocation is not supported by this browser.');
      setLoading(false);
    }
  }, []);

  return (
    <>
      <div style={{ width: "350px", height: "700px" }}>
        {!loading && 
          <OpenStreetMap
            center={userLocation}
            vehicles={vehicles}
            stops={stops}
          />}
      </div>
    </>
  )
}

export default App
