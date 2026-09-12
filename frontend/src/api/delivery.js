import { authApi } from './auth.js';

const BASE = '/api/delivery';

function accessToken() {
  const session = authApi.getSession?.();
  return session?.tokens?.access || session?.access || null;
}

async function request(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken() ? { Authorization: `Bearer ${accessToken()}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(data?.detail || 'خطا در دریافت اطلاعات پخش');
  return data;
}

const list = (data) => Array.isArray(data) ? data : (data?.results || []);

export const deliveryApi = {
  routes: async () => list(await request('/routes/')),
  visits: async () => list(await request('/visits/')),
  trips: async () => list(await request('/trips/')),
  deliveryStops: async () => list(await request('/delivery-stops/')),
  gpsTracks: async () => list(await request('/gps-tracks/')),
  checkIn: (id, latitude, longitude) => request(`/visits/${id}/check-in/`, { method: 'POST', body: { latitude, longitude } }),
  checkOut: (id, latitude, longitude, note = '') => request(`/visits/${id}/check-out/`, { method: 'POST', body: { latitude, longitude, note } }),
  startTrip: (id) => request(`/trips/${id}/start/`, { method: 'POST' }),
  recordGps: (route, latitude, longitude, accuracy_meters) => request('/gps-tracks/', { method: 'POST', body: { route, latitude, longitude, accuracy_meters } }),
  saveRoutePlan: (id, plan) => request(`/routes/${id}/save-plan/`, { method: 'POST', body: plan }),
  deliver: (id, payload) => request(`/delivery-stops/${id}/deliver/`, { method: 'POST', body: payload }),
};

export function currentPosition() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve({ latitude: null, longitude: null });
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ latitude: coords.latitude.toFixed(6), longitude: coords.longitude.toFixed(6), accuracy_meters: coords.accuracy }),
      () => resolve({ latitude: null, longitude: null }),
      { enableHighAccuracy: true, timeout: 5000, maximumAge: 30000 },
    );
  });
}

export const deliveryFallback = {
  routes: [{ id: 'preview-route', code: 'R-12', name: 'مسیر ۱۲ — منطقه غرب', stops: [] }],
  visits: [],
  trips: [],
  deliveryStops: [],
};
