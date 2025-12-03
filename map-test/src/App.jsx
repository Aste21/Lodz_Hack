import { useState, useEffect } from "react";
import "./App.css";
import OpenStreetMap from "./my-components/OpenStreetMap";
import Chat from "./my-components/Chat";
import Papa from "papaparse";
import { SlidersHorizontal } from "lucide-react";

const tramLines = [
  "1","2","3","4","5","6","7","8","9",
  "10A","10B","11","12","14","15","16",
  "17","18","19","41","43","45","P1","P2","R8"
];

const busLines = [
  "6.","50A","50B","51A","51B","52","53A","53B","54A","54B",
  "55A","55B","56","57","58A","58B","59","60A","60B","60C",
  "61","62","63","64A","64B","65A","65B","66","68","69A","69B",
  "70","71A","71B","72A","72B","73","75A","75B","76","77","78",
  "80A","80B","81A","81B","82A","82B","83","84A","84B","85A",
  "85B","86","87A","87B","88A","88B","88C","88D","89","90",
  "91A","91B","91C","92A","92B","93","94","96","97A","97B",
  "99","201","202","F1","G1","G2","H","N1A","N1B","N2","N3A",
  "N3B","N4A","N4B","N5A","N5B","N6","N7A","N7B","N8","N9","OP6",
  "P4","P7","R9","R11","R16","R22","R24","R26","W","Z","Z3","Z13"
];

function App() {
  const [userLocation, setUserLocation] = useState([51.758821, 19.456283]);
  const [loading, setLoading] = useState(true);
  const [stops, setStops] = useState([]);
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [selectedLines, setSelectedLines] = useState([]);
  const [search, setSearch] = useState("");
  const [fromAddress, setFromAddress] = useState("");
  const [toAddress, setToAddress] = useState("");
  const [vehicles, setVehicles] = useState([]);
  const [showMap, setShowMap] = useState(false);
  const [showChat, setShowChat] = useState(false);

  const logAddresses = () => {
    console.log(`Skąd: ${fromAddress}, Dokąd: ${toAddress}`);
  };


  useEffect(() => {
    fetch("/stops.txt")
      .then((response) => response.text())
      .then((text) => {
        const parsed = Papa.parse(text, { header: true, skipEmptyLines: true });
        const stopsData = parsed.data.map((s) => ({
          id: s.stop_id,
          name: s.stop_name,
          lat: parseFloat(s.stop_lat),
          lng: parseFloat(s.stop_lon)
        }));
        setStops(stopsData);
      })
      .catch((err) => console.error("Error loading stops:", err));
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
          console.error("Error getting location:", error);
          setLoading(false);
        }
      );
    } else {
      console.error("Geolocation is not supported by this browser.");
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const fetchVehicles = () => {
      fetch("http://localhost:8001/data")
        .then((response) => response.json())
        .then((data) => {
          // setVehicles(data);
          // console.log(data)
        })
        .catch((err) => console.error("Error fetching vehicles:", err));
    };

    // Fetch immediately on mount
    fetchVehicles();

    // Then fetch every 10 seconds
    const interval = setInterval(fetchVehicles, 10000);

    // Cleanup interval on unmount
    return () => clearInterval(interval);
  }, []);

  const toggleLine = (line) => {
    setSelectedLines((prev) =>
      prev.includes(line)
        ? prev.filter((l) => l !== line)
        : [...prev, line]
    );
  };

  const handleStartScreenClick = (e) => {
    const clickX = e.clientX || (e.touches && e.touches[0]?.clientX) || (e.changedTouches && e.changedTouches[0]?.clientX);
    if (!clickX) return;
    
    const screenWidth = window.innerWidth;
    const centerX = screenWidth / 2;
    
    // Oblicz rzeczywisty rozmiar kółka (15vw, max 60px, min 50px)
    const circleSize = Math.min(Math.max(window.innerWidth * 0.15, 50), 60);
    const circleRadius = circleSize / 2;
    const safeRadius = circleRadius + 10; // margines bezpieczeństwa 10px
    
    const distanceFromCenter = Math.abs(clickX - centerX);
    
    // Jeśli kliknięto w kółko (z marginesem bezpieczeństwa), nie rób nic (lub można dodać akcję)
    if (distanceFromCenter <= safeRadius) {
      // Kliknięcie w kółko - można dodać akcję lub pozostawić puste
      return;
    }
    
    // Jeśli kliknięto po prawej stronie od kółka, przejdź do mapy
    if (clickX > centerX) {
      setShowMap(true);
    } else {
      // Po lewej stronie - chat
      setShowChat(true);
    }
  };

  const handleMapBottomClick = (e) => {
    const clickX = e.clientX || (e.touches && e.touches[0]?.clientX) || (e.changedTouches && e.changedTouches[0]?.clientX);
    if (!clickX) return;
    
    const screenWidth = window.innerWidth;
    const centerX = screenWidth / 2;
    
    // Oblicz rzeczywisty rozmiar kółka (15vw, max 60px, min 50px)
    const circleSize = Math.min(Math.max(window.innerWidth * 0.15, 50), 60);
    const circleRadius = circleSize / 2;
    const safeRadius = circleRadius + 15; // większy margines bezpieczeństwa 15px
    
    const distanceFromCenter = Math.abs(clickX - centerX);
    
    // Jeśli kliknięto w kółko (z marginesem bezpieczeństwa), wróć do ekranu głównego
    if (distanceFromCenter <= safeRadius) {
      setShowMap(false);
      setShowChat(false);
      return;
    }
    
    // Jeśli kliknięto po lewej stronie od kółka - chat
    if (clickX < centerX) {
      setShowChat(true);
      setShowMap(false);
    }
    // Po prawej stronie - pozostajemy na mapie (nic nie robimy)
  };

  // Ekran chatu
  if (showChat) {
    return <Chat onClose={() => setShowChat(false)} />;
  }

  // Ekran startowy
  if (!showMap) {
    return (
      <div 
        className="start-screen" 
        onClick={handleStartScreenClick}
        onTouchEnd={handleStartScreenClick}
      >
        <div className="start-bottom-line">
          <img src="/bottom_line.png" alt="Bottom Line" className="bottom-line-image" />
          <div className="start-circle"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <img src="/goratlo.png" alt="Header Image" className="header-image" />
      <div className="map-wrapper">
        {!loading && (
          <OpenStreetMap
            center={userLocation}
            vehicles={vehicles}
            stops={stops}
            selectedLines={selectedLines}
          />
        )}
        <button className="filter-btn" onClick={() => setIsFilterOpen(true)}>
          <SlidersHorizontal size={22} strokeWidth={2.5} color="black" />
        </button>
      </div>
      <div 
        className="map-bottom-line"
        onClick={handleMapBottomClick}
        onTouchEnd={handleMapBottomClick}
      >
        <img src="/bottom_line.png" alt="Bottom Line" className="bottom-line-image" />
        <div className="map-circle"></div>
      </div>

      <div className="address-fields">
<div className="address-row">
  <div className="addr-dot from-dot"></div>
  <input
    className="addr-box"
    value={fromAddress}
    onChange={(e) => setFromAddress(e.target.value)}
    placeholder="Skąd?"
  />
</div>

<div className="address-row">
  <div className="addr-dot to-dot"></div>
  <input
    className="addr-box"
    value={toAddress}
    onChange={(e) => setToAddress(e.target.value)}
    placeholder="Dokąd?"
  />
</div>

{(fromAddress && toAddress) && (
  <div className="address-row">
    <button className="log-btn" onClick={logAddresses}>
      Szukaj trasy
    </button>
  </div>
)}
      </div>

      <div className={`filter-panel ${isFilterOpen ? "open" : ""}`}>
        <div className="fp-header">
          <span className="fp-title">Filtruj mapę</span>
          <div className="fp-x" onClick={() => setIsFilterOpen(false)}>X</div>
        </div>

        <div className="fp-subtitle">Szukaj linii:</div>
        <input
          className="fp-search"
          placeholder="Wpisz numer linii"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <div className="fp-subtitle">Wybrane linie:</div>
        <div className="fp-selected">
          {selectedLines.length === 0 ? (
            <span className="fp-empty">Brak</span>
          ) : (
            selectedLines.map((num) => (
              <div key={num} className="fp-pill">{num}</div>
            ))
          )}
        </div>

        {}

        <div className="fp-subtitle">Wszystkie linie:</div>

        <div className="fp-grid">
          {[...tramLines, ...busLines]
            .filter(l => l.toLowerCase().includes(search.toLowerCase()))
            .map((line) => {
              const isTram = tramLines.includes(line);
              return (
                <div
                  key={line}
                  className={`fp-item ${isTram ? "tram" : "bus"} ${
                    selectedLines.includes(line) ? "selected" : ""
                  }`}
                  onClick={() => toggleLine(line)}
                >
                  {line}
                </div>
              );
            })}
        </div>

        {}

        <div className="fp-footer">
          <button className="fp-reset" onClick={() => setSelectedLines([])}>
            ZRESETUJ
          </button>
          <button className="fp-save" onClick={() => setIsFilterOpen(false)}>
            ZAPISZ
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
