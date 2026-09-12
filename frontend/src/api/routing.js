const OSRM_BASE = 'https://router.project-osrm.org';

function coordinateString(points) {
  return points.map((p) => `${Number(p.lng)},${Number(p.lat)}`).join(';');
}

async function osrm(path) {
  const response = await fetch(`${OSRM_BASE}${path}`);
  const data = await response.json().catch(() => null);
  if (!response.ok || data?.code !== 'Ok') throw new Error(data?.message || 'مسیریابی در دسترس نیست');
  return data;
}

function greedyOrder(matrix, start = 0) {
  const order = [start];
  const remaining = new Set(matrix.map((_, index) => index).filter((index) => index !== start));
  while (remaining.size) {
    const current = order[order.length - 1];
    const next = [...remaining].sort((a, b) => (matrix[current]?.[a] ?? Infinity) - (matrix[current]?.[b] ?? Infinity))[0];
    order.push(next); remaining.delete(next);
  }
  return order;
}

export async function planRoute(points, { optimize = true } = {}) {
  const valid = points.filter((p) => Number.isFinite(Number(p.lat)) && Number.isFinite(Number(p.lng))).map((p) => ({ ...p, lat: Number(p.lat), lng: Number(p.lng) }));
  if (valid.length < 2) return { points: valid, track: valid.map((p) => [p.lat, p.lng]), distance: 0, duration: 0, optimized: false, steps: [] };
  let ordered = valid;
  if (optimize && valid.length > 2) {
    const table = await osrm(`/table/v1/driving/${coordinateString(valid)}?annotations=duration`);
    const order = greedyOrder(table.durations || [], 0);
    ordered = order.map((index) => valid[index]);
  }
  const route = await osrm(`/route/v1/driving/${coordinateString(ordered)}?overview=full&geometries=geojson&steps=true`);
  const result = route.routes?.[0];
  const track = result?.geometry?.coordinates?.map(([lng, lat]) => [lat, lng]) || ordered.map((p) => [p.lat, p.lng]);
  const steps = (result?.legs || []).flatMap((leg) => leg.steps || []).map((step, index) => ({
    index: index + 1,
    instruction: [step.maneuver?.type, step.maneuver?.modifier, step.name].filter(Boolean).join(' — '),
    type: step.maneuver?.type || 'continue',
    modifier: step.maneuver?.modifier || '',
    road: step.name || 'مسیر بدون نام',
    distance: step.distance || 0,
    duration: step.duration || 0,
    location: step.maneuver?.location || null,
  }));
  return { points: ordered, track, distance: result?.distance || 0, duration: result?.duration || 0, optimized: optimize && valid.length > 2, steps };
}

export function formatDistance(meters) {
  return meters >= 1000 ? `${(meters / 1000).toFixed(1)} کیلومتر` : `${Math.round(meters)} متر`;
}

export function formatDuration(seconds) {
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} دقیقه`;
  return `${Math.floor(minutes / 60)} ساعت و ${minutes % 60} دقیقه`;
}
