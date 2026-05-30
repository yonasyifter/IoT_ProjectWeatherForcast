<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { fetchEmergencyRequests, resolveEmergencyRequest } from '@/services/emergencyApi.js'
import trailsRaw from '@/map/trails.json?raw'

const requests = ref([])
const selectedRequest = ref(null)
const loading = ref(false)
const error = ref('')
const solvingIds = ref(new Set())
const map = ref(null)
const markers = ref({})
const trailLayers = ref([])
let refreshTimer = null
const trails = loadTrails()
const parkLocation = trails[0]?.coords?.[0]
  ? [trails[0].coords[0].lat, trails[0].coords[0].lng]
  : [39.3239, 16.4675]

const activeRequests = computed(() =>
  requests.value.filter(request =>
    request.latitude != null &&
    request.longitude != null &&
    String(request.status || '').toUpperCase() === 'ACTIVE'
  )
)

const mappedActiveRequests = computed(() =>
  activeRequests.value.map(request => ({
    ...request,
    mapLocation: nearestTrailLocation(request),
  }))
)

async function fetchRequests() {
  loading.value = true
  error.value = ''

  try {
    requests.value = await fetchEmergencyRequests()
    const locatableRequests = activeRequests.value

    if (!selectedRequest.value && locatableRequests.length > 0) {
      selectedRequest.value = locatableRequests[0]
    } else if (selectedRequest.value) {
      selectedRequest.value = locatableRequests.find(
        request => request.request_id === selectedRequest.value.request_id
      ) || locatableRequests[0] || null
    }

    await nextTick()
    updateMapMarkers()
    window.dispatchEvent(new CustomEvent('emergency-requests-updated'))
  } catch (err) {
    error.value = err.message || 'Failed to load emergency requests'
  } finally {
    loading.value = false
  }
}

async function solveRequest(request) {
  if (!request?.request_id) return
  const confirmed = window.confirm('Mark this emergency request as solved?')
  if (!confirmed) return

  solvingIds.value = new Set([...solvingIds.value, request.request_id])
  error.value = ''

  try {
    await resolveEmergencyRequest(request)
    requests.value = requests.value.filter(item => item.request_id !== request.request_id)
    selectedRequest.value = activeRequests.value[0] || null
    updateMapMarkers()
    window.dispatchEvent(new CustomEvent('emergency-requests-updated'))
  } catch (err) {
    error.value = err.message || 'Failed to solve emergency request'
  } finally {
    const nextSolvingIds = new Set(solvingIds.value)
    nextSolvingIds.delete(request.request_id)
    solvingIds.value = nextSolvingIds
  }
}

function initMap() {
  if (map.value) return

  map.value = L.map('emergency-map', {
    zoomControl: false,
  }).setView(parkLocation, 15)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19,
    minZoom: 14,
  }).addTo(map.value)

  L.control.zoom({ position: 'topright' }).addTo(map.value)
  drawTrailLayers()
  fitMapToTrailsAndRequests()
}

function drawTrailLayers() {
  if (!map.value) return

  trailLayers.value.forEach(layer => map.value.removeLayer(layer))
  trailLayers.value = trails.map((trail, index) => {
    const layer = L.polyline(trail.coords.map(point => [point.lat, point.lng]), {
      color: trailColor(index),
      opacity: 0.72,
      weight: 4,
      lineCap: 'round',
      lineJoin: 'round',
    })
      .addTo(map.value)
      .bindTooltip(`Trail ${trail.id}: ${escapeHtml(trail.name)}<br>${escapeHtml(trail.length)}`, {
        sticky: true,
        direction: 'top',
      })

    return layer
  })
}

function updateMapMarkers() {
  if (!map.value) return

  Object.values(markers.value).forEach(marker => map.value.removeLayer(marker))
  markers.value = {}

  mappedActiveRequests.value.forEach((request) => {
    const marker = L.marker([request.mapLocation.lat, request.mapLocation.lng], { icon: emergencyMarkerIcon() })
      .addTo(map.value)
      .bindPopup(`
        <strong>${escapeHtml(request.visitor_name || 'Visitor')}</strong><br>
        Request: ${escapeHtml(request.request_id || '-') }<br>
        Trail context: ${escapeHtml(request.mapLocation.trailName || 'Nearest trail')}<br>
        ${request.message ? escapeHtml(request.message) : 'Emergency request'}
      `)

    marker.on('click', () => trackRequest(request))

    markers.value[request.request_id] = marker
  })

  if (selectedRequest.value?.latitude != null && selectedRequest.value?.longitude != null) {
    trackRequest(selectedRequest.value, false)
  } else if (activeRequests.value.length > 0) {
    fitMapToTrailsAndRequests()
  } else {
    fitMapToTrailsAndRequests()
  }
}

function fitMapToTrailsAndRequests() {
  if (!map.value) return

  const trailPoints = trails.flatMap(trail => trail.coords.map(point => [point.lat, point.lng]))
  const requestPoints = mappedActiveRequests.value.map(request => [request.mapLocation.lat, request.mapLocation.lng])
  const points = [...trailPoints, ...requestPoints]

  if (points.length > 0) {
    map.value.fitBounds(L.latLngBounds(points), { padding: [42, 42] })
  } else {
    map.value.setView(parkLocation, 16)
  }
}

function emergencyMarkerIcon() {
  return L.divIcon({
    className: 'emergency-marker',
    html: `
      <svg class="emergency-person-pin" viewBox="0 0 36 44" aria-hidden="true">
        <path d="M18 43C18 43 4 27.7 4 16.8C4 8.6 10.3 2 18 2C25.7 2 32 8.6 32 16.8C32 27.7 18 43 18 43Z" />
        <circle cx="18" cy="16.8" r="9.5" />
        <path class="person" d="M18 16.5C20.1 16.5 21.7 14.9 21.7 12.9C21.7 10.9 20.1 9.3 18 9.3C15.9 9.3 14.3 10.9 14.3 12.9C14.3 14.9 15.9 16.5 18 16.5ZM11.8 24.4C12.3 20.9 14.8 18.6 18 18.6C21.2 18.6 23.7 20.9 24.2 24.4C24.3 25.1 23.8 25.7 23.1 25.7H12.9C12.2 25.7 11.7 25.1 11.8 24.4Z" />
      </svg>
    `,
    iconSize: [36, 44],
    iconAnchor: [18, 42],
    popupAnchor: [0, -40],
    tooltipAnchor: [0, -40],
  })
}

function trackRequest(request, openPopup = true) {
  selectedRequest.value = request
  if (!map.value || request.latitude == null || request.longitude == null) return

  const location = nearestTrailLocation(request)
  map.value.setView([location.lat, location.lng], 18)
  const marker = markers.value[request.request_id]
  if (marker && openPopup) marker.openPopup()
}

function formatDate(value) {
  if (!value) return '-'
  const date = typeof value === 'number' ? new Date(value) : new Date(String(value))
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
}

function locationLabel(request) {
  if (request.latitude == null || request.longitude == null) return 'Location unavailable'
  return `${Number(request.latitude).toFixed(6)}, ${Number(request.longitude).toFixed(6)}`
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function nearestTrailLocation(request) {
  const source = {
    lat: Number(request.latitude),
    lng: Number(request.longitude),
  }

  if (!Number.isFinite(source.lat) || !Number.isFinite(source.lng) || trails.length === 0) {
    return { ...source, trailName: '' }
  }

  let nearest = null

  trails.forEach((trail) => {
    trail.coords.slice(0, -1).forEach((start, index) => {
      const end = trail.coords[index + 1]
      const candidate = closestPointOnSegment(source, start, end)
      const distance = distanceBetween(source, candidate)

      if (!nearest || distance < nearest.distance) {
        nearest = {
          ...candidate,
          distance,
          trailId: trail.id,
          trailName: trail.name,
        }
      }
    })
  })

  return nearest || { ...source, trailName: '' }
}

function closestPointOnSegment(point, start, end) {
  const originLat = point.lat * Math.PI / 180
  const metersPerLat = 111_320
  const metersPerLng = 111_320 * Math.cos(originLat)

  const px = point.lng * metersPerLng
  const py = point.lat * metersPerLat
  const ax = start.lng * metersPerLng
  const ay = start.lat * metersPerLat
  const bx = end.lng * metersPerLng
  const by = end.lat * metersPerLat
  const dx = bx - ax
  const dy = by - ay
  const lengthSquared = dx * dx + dy * dy
  const ratio = lengthSquared === 0
    ? 0
    : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / lengthSquared))

  return {
    lat: (ay + dy * ratio) / metersPerLat,
    lng: (ax + dx * ratio) / metersPerLng,
  }
}

function distanceBetween(a, b) {
  const latFactor = 111_320
  const lngFactor = 111_320 * Math.cos(((a.lat + b.lat) / 2) * Math.PI / 180)
  const dx = (b.lng - a.lng) * lngFactor
  const dy = (b.lat - a.lat) * latFactor
  return Math.hypot(dx, dy)
}

function loadTrails() {
  try {
    const parsed = JSON.parse(`{${trailsRaw}}`)
    return Object.entries(parsed.trails || {})
      .map(([key, trail]) => {
        const id = String(key.match(/\d+/)?.[0] || '').replace(/^0+/, '') || String(trail.trail_id?.[0] || '')
        return {
          id,
          name: trail.name || `Trail ${id}`,
          length: trail.length || '-',
          coords: (trail.coords || [])
            .map(point => ({ lat: Number(point.lat), lng: Number(point.lng) }))
            .filter(point => Number.isFinite(point.lat) && Number.isFinite(point.lng)),
        }
      })
      .filter(trail => trail.id && trail.coords.length > 1)
  } catch {
    return []
  }
}

function trailColor(index) {
  return ['#38bdf8', '#22c55e', '#f59e0b', '#a855f7', '#f43f5e'][index % 5]
}

watch(activeRequests, () => {
  nextTick(updateMapMarkers)
})

onMounted(async () => {
  await nextTick()
  initMap()
  await fetchRequests()
  refreshTimer = setInterval(fetchRequests, 15000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  if (map.value) {
    map.value.remove()
    map.value = null
  }
})
</script>

<template>
  <main class="emergency-page">
    <div class="container-fluid py-4">
      <div class="d-flex justify-content-between align-items-center gap-3 flex-wrap mb-4">
        <div>
          <h1 class="h4 mb-1">Emergency Requests</h1>
          <p class="text-secondary mb-0">Active visitor emergency requests and live location tracking.</p>
        </div>

        <button class="btn btn-sm btn-outline-light" :disabled="loading" @click="fetchRequests">
          <i class="bi bi-arrow-clockwise me-1"></i>
          Refresh
        </button>
      </div>

      <div v-if="error" class="alert alert-danger">
        <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
      </div>

      <section class="emergency-panel mb-3">
        <div class="d-flex justify-content-between align-items-center gap-2 flex-wrap mb-3">
          <div>
            <h2 class="h5 mb-1">Visitor Emergency Request List</h2>
            <p class="text-secondary small mb-0">Requests disappear when solved or when the visitor disables emergency/location.</p>
          </div>
          <span class="badge text-bg-danger">{{ activeRequests.length }} active</span>
        </div>

        <div v-if="loading && activeRequests.length === 0" class="text-center py-5 text-secondary">
          <div class="spinner-border text-danger mb-2"></div>
          <div>Loading emergency requests...</div>
        </div>

        <div v-else-if="activeRequests.length === 0" class="empty-state text-center py-5">
          <i class="bi bi-shield-check fs-1"></i>
          <p class="mt-2 mb-0">No active emergency requests with location.</p>
        </div>

        <div v-else class="request-list">
          <article
            v-for="request in activeRequests"
            :key="request.request_id"
            class="request-card"
            :class="{ selected: selectedRequest?.request_id === request.request_id }"
          >
            <div class="request-card-header">
              <div>
                <div class="d-flex align-items-center gap-2 flex-wrap">
                  <span class="badge text-bg-danger">Emergency</span>
                  <span class="font-monospace text-info small">Request {{ request.request_id || '-' }}</span>
                </div>
                <h3 class="h6 mt-2 mb-0">{{ request.visitor_name || 'Unknown visitor' }}</h3>
              </div>

              <button
                class="btn btn-sm btn-outline-success"
                :disabled="solvingIds.has(request.request_id)"
                @click="solveRequest(request)"
              >
                <span v-if="solvingIds.has(request.request_id)" class="spinner-border spinner-border-sm me-1"></span>
                <i v-else class="bi bi-check2-circle me-1"></i>
                Solved
              </button>
            </div>

            <div class="request-info">
              <span><i class="bi bi-person-badge me-1"></i>{{ request.visitor_id || '-' }}</span>
              <span><i class="bi bi-telephone me-1"></i>{{ request.phone || '-' }}</span>
              <span><i class="bi bi-clock me-1"></i>{{ formatDate(request.created_at || request.updated_at) }}</span>
              <span><i class="bi bi-geo-alt me-1"></i>{{ locationLabel(request) }}</span>
            </div>

            <p v-if="request.message" class="request-message mb-3">{{ request.message }}</p>

            <button
              class="btn btn-sm btn-danger"
              :disabled="request.latitude == null || request.longitude == null"
              @click="trackRequest(request)"
            >
              <i class="bi bi-crosshair me-1"></i>
              Track
            </button>
          </article>
        </div>
      </section>

      <section class="emergency-panel">
        <div class="d-flex justify-content-between align-items-center gap-2 flex-wrap mb-3">
          <div>
            <h2 class="h5 mb-1">Emergency Location Map</h2>
            <p class="text-secondary small mb-0">
              {{ selectedRequest ? `Tracking request ${selectedRequest.request_id}` : 'Select Track on a request to focus the visitor location.' }}
            </p>
          </div>
          <span v-if="selectedRequest" class="device-chip">{{ locationLabel(selectedRequest) }}</span>
        </div>

        <div id="emergency-map"></div>

        <div class="trail-legend mt-3">
          <span v-for="(trail, index) in trails" :key="trail.id" class="trail-legend-item">
            <span class="trail-legend-line" :style="{ background: trailColor(index) }"></span>
            Trail {{ trail.id }} · {{ trail.name }}
          </span>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
.emergency-page {
  background: #0b1220;
  color: #f8fafc;
  min-height: calc(100vh - 58px);
}

.emergency-panel {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 8px;
  padding: 1rem;
}

.empty-state {
  background: rgba(255, 255, 255, 0.04);
  border: 1px dashed rgba(255, 255, 255, 0.14);
  border-radius: 8px;
  color: #94a3b8;
}

.request-list {
  display: grid;
  gap: 0.75rem;
}

.request-card {
  background: rgba(15, 23, 42, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-left: 4px solid #dc3545;
  border-radius: 8px;
  padding: 1rem;
}

.request-card.selected {
  border-color: rgba(14, 165, 233, 0.58);
  box-shadow: 0 0 0 1px rgba(14, 165, 233, 0.25);
}

.request-card-header {
  align-items: flex-start;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
}

.request-info {
  color: #cbd5e1;
  display: grid;
  gap: 0.45rem;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  margin: 0.8rem 0;
}

.request-message {
  color: #e2e8f0;
}

.device-chip {
  background: rgba(14, 165, 233, 0.16);
  border: 1px solid rgba(14, 165, 233, 0.42);
  border-radius: 999px;
  color: #7dd3fc;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.82rem;
  font-weight: 700;
  padding: 0.25rem 0.65rem;
}

#emergency-map {
  border-radius: 8px;
  height: 430px;
  min-height: 320px;
  overflow: hidden;
  width: 100%;
}

.trail-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.trail-legend-item {
  align-items: center;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  color: #cbd5e1;
  display: inline-flex;
  font-size: 0.8rem;
  gap: 0.45rem;
  padding: 0.3rem 0.65rem;
}

.trail-legend-line {
  border-radius: 999px;
  display: inline-block;
  height: 0.25rem;
  width: 1.4rem;
}

:deep(.emergency-marker) {
  background: transparent;
  border: 0;
}

:deep(.emergency-person-pin) {
  height: 44px;
  overflow: visible;
  paint-order: stroke;
  stroke: #ffffff;
  stroke-linejoin: round;
  stroke-width: 2.5px;
  filter: drop-shadow(0 8px 12px rgba(0, 0, 0, 0.35));
  width: 36px;
}

:deep(.emergency-person-pin path:first-child) {
  fill: #dc3545;
}

:deep(.emergency-person-pin circle) {
  fill: #ffffff;
  stroke: none;
}

:deep(.emergency-person-pin .person) {
  fill: #dc3545;
  stroke: none;
}
</style>
