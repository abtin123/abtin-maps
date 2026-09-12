import React, { useEffect, useMemo, useState } from 'react';
import { CircleMarker, MapContainer, Marker, Popup, Polyline, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const TEHRAN = [35.7219, 51.3347];

function FitBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 1) map.fitBounds(L.latLngBounds(points.map((p) => [p.lat, p.lng])), { padding: [32, 32], maxZoom: 14 });
    else if (points.length === 1) map.setView([points[0].lat, points[0].lng], 14);
  }, [map, points]);
  return null;
}

function LocateUser() {
  const map = useMap();
  const [position, setPosition] = useState(null);
  const [error, setError] = useState('');
  const locate = () => {
    if (!navigator.geolocation) return setError('GPS در این مرورگر پشتیبانی نمی‌شود.');
    navigator.geolocation.getCurrentPosition((value) => {
      const next = [value.coords.latitude, value.coords.longitude];
      setPosition(next); setError(''); map.setView(next, 16);
    }, () => setError('دسترسی GPS رد شد یا موقعیت فعلی قابل دریافت نیست.'), { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 });
  };
  return <><button type="button" className="map-locate-btn" onClick={locate}>موقعیت فعلی</button>{error && <span className="map-locate-error">{error}</span>}{position && <CircleMarker center={position} radius={8} pathOptions={{ color: '#2563eb', fillColor: '#60a5fa', fillOpacity: 0.9 }}><Popup>موقعیت فعلی دستگاه</Popup></CircleMarker>}</>;
}

function markerIcon(color = '#2f7bff', active = false) {
  return L.divIcon({
    className: 'abtin-marker-wrap',
    html: `<span class="abtin-marker ${active ? 'active' : ''}" style="--marker-color:${color}"></span>`,
    iconSize: [24, 24], iconAnchor: [12, 12], popupAnchor: [0, -14],
  });
}

export default function RealMap({ points = [], track = [], height = 380, title = 'نقشه عملیاتی' }) {
  const validPoints = useMemo(() => points.filter((p) => Number.isFinite(Number(p.lat)) && Number.isFinite(Number(p.lng))).map((p) => ({ ...p, lat: Number(p.lat), lng: Number(p.lng) })), [points]);
  const validTrack = useMemo(() => track.filter((p) => Number.isFinite(Number(p.lat)) && Number.isFinite(Number(p.lng))).map((p) => [Number(p.lat), Number(p.lng)]), [track]);
  const route = validTrack.length > 1 ? validTrack : validPoints.map((p) => [p.lat, p.lng]);
  const center = validPoints[0] ? [validPoints[0].lat, validPoints[0].lng] : TEHRAN;
  return <div className="real-map" style={{ height }} aria-label={title}>
    <MapContainer center={center} zoom={12} scrollWheelZoom className="real-map-container">
      <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <FitBounds points={validPoints} />
      <LocateUser />
      {route.length > 1 && <Polyline positions={route} pathOptions={{ color: '#2f7bff', weight: 5, opacity: 0.8, dashArray: validTrack.length ? undefined : '10 8' }} />}
      {validPoints.map((p, i) => <Marker key={`${p.id || p.label}-${i}`} position={[p.lat, p.lng]} icon={markerIcon(p.color, p.active)}><Popup><strong>{p.label || 'مقصد'}</strong>{p.address && <><br />{p.address}</>}{p.status && <><br /><small>{p.status}</small></>}</Popup></Marker>)}
    </MapContainer>
    <div className="real-map-legend"><span><i style={{ background: '#4ade80' }} /> انجام‌شده</span><span><i style={{ background: '#fbbf24' }} /> مقصد بعدی</span><span><i style={{ background: '#f87171' }} /> باقی‌مانده</span></div>
  </div>;
}
