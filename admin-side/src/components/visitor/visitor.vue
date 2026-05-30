<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import trailsRaw from '@/map/trails.json?raw'
import resultsRaw from '@/map/results.csv?raw'

const TRAFFIC_URL = 'https://l6wlyfij89.execute-api.eu-north-1.amazonaws.com/prod/admin/traffic'

const loading = ref(false)
const error = ref('')
const lastUpdated = ref(null)
const trafficRows = ref([])
const mapContainer = ref(null)
const selectedTrailId = ref(null)
const isolatedTrailId = ref(null)

let map = null
let trailLayerGroup = null
let refreshTimer = null

const trails = loadTrails()

const totalUsers = computed(() =>
  trafficRows.value.reduce((sum, row) => sum + row.userCount, 0)
)

const trailDashboard = computed(() =>
  trails
    .map((trail) => {
      const traffic = trafficRows.value.find(row => row.trailID === trail.id)
      return {
        ...trail,
        userCount: traffic?.userCount ?? 0,
      }
    })
    .sort((a, b) => a.userCount - b.userCount || Number(a.id) - Number(b.id))
)

const visibleTrailDashboard = computed(() =>
  isolatedTrailId.value
    ? trailDashboard.value.filter(trail => trail.id === isolatedTrailId.value)
    : trailDashboard.value
)

async function fetchTraffic() {
  loading.value = true
  error.value = ''

  try {
    const response = await fetch(TRAFFIC_URL, { method: 'GET' })
    if (!response.ok) throw new Error(`Traffic API error: ${response.status}`)

    const payload = await response.json()
    const rows = Array.isArray(payload?.trails) ? payload.trails : []

    trafficRows.value = rows.map(row => ({
      trailID: String(row.trailID ?? row.trailId ?? row.id ?? '').replace(/^0+/, '') || '0',
      userCount: Math.max(0, Number(row.userCount ?? row.users ?? 0) || 0),
    }))
    lastUpdated.value = new Date()

    await nextTick()
    renderMapLayers()
  } catch (err) {
    error.value = err.message || 'Failed to load visitor traffic'
  } finally {
    loading.value = false
  }
}

function loadTrails() {
  const parsedFromJson = parseTrailsJson()
  if (parsedFromJson.length > 0) return parsedFromJson
  return parseTrailsCsv()
}

function parseTrailsJson() {
  try {
    const parsed = JSON.parse(`{${trailsRaw}}`)
    return Object.entries(parsed.trails || {})
      .map(([key, trail]) => {
        const id = String(key.match(/\d+/)?.[0] || '').replace(/^0+/, '') || String(trail.trail_id?.[0] || '')
        return normalizeTrail({
          id,
          name: trail.name || `Trail ${id}`,
          length: trail.length || '-',
          coords: trail.coords || [],
        })
      })
      .filter(trail => trail.coords.length > 1 && trail.id)
  } catch {
    return []
  }
}

function parseTrailsCsv() {
  const lines = resultsRaw.trim().split(/\r?\n/)
  if (lines.length < 2) return []

  const headers = parseCsvLine(lines[0]).map(header => header.replaceAll('"', ''))
  return lines.slice(1)
    .map((line) => {
      const values = parseCsvLine(line)
      const row = Object.fromEntries(headers.map((header, index) => [header, values[index]]))
      return normalizeTrail({
        id: String(row.ID || '').replace(/^0+/, ''),
        name: row.name || `Trail ${row.ID}`,
        length: row.length || '-',
        coords: parseDynamoCoords(row.coords),
      })
    })
    .filter(trail => trail.coords.length > 1 && trail.id)
}

function parseCsvLine(line) {
  const cells = []
  let current = ''
  let quoted = false

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index]
    const next = line[index + 1]

    if (char === '"' && quoted && next === '"') {
      current += '"'
      index += 1
    } else if (char === '"') {
      quoted = !quoted
    } else if (char === ',' && !quoted) {
      cells.push(current)
      current = ''
    } else {
      current += char
    }
  }

  cells.push(current)
  return cells
}

function parseDynamoCoords(value) {
  try {
    return JSON.parse(value || '[]').map(item => ({
      lat: Number(item.M?.lat?.N),
      lng: Number(item.M?.lng?.N),
    }))
  } catch {
    return []
  }
}

function normalizeTrail(trail) {
  return {
    id: String(trail.id),
    name: trail.name,
    length: trail.length,
    coords: trail.coords
      .map(point => ({ lat: Number(point.lat), lng: Number(point.lng) }))
      .filter(point => Number.isFinite(point.lat) && Number.isFinite(point.lng)),
  }
}

function initMap() {
  if (map || !mapContainer.value) return

  map = L.map(mapContainer.value, {
    zoomControl: false,
    preferCanvas: true,
  })

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 20,
    minZoom: 15,
  }).addTo(map)

  L.control.zoom({ position: 'topright' }).addTo(map)
  trailLayerGroup = L.layerGroup().addTo(map)

  fitTrailBounds()
  renderMapLayers()
}

function renderMapLayers() {
  if (!map || !trailLayerGroup) return

  trailLayerGroup.clearLayers()

  visibleTrailDashboard.value.forEach((trail) => {
    const isSelected = selectedTrailId.value === trail.id
    const color = trailColor(trail.userCount)
    const polyline = L.polyline(trail.coords.map(point => [point.lat, point.lng]), {
      color,
      opacity: isSelected ? 1 : 0.78,
      weight: isSelected ? 7 : 4,
      lineCap: 'round',
      lineJoin: 'round',
    }).addTo(trailLayerGroup)

    polyline.bindTooltip(trailCardHtml(trail), {
      className: 'trail-density-tooltip',
      sticky: true,
      direction: 'top',
    })
    polyline.bindPopup(trailCardHtml(trail), {
      className: 'trail-density-popup',
      closeButton: false,
    })
    polyline.on('click', () => {
      isolateTrail(trail)
      polyline.openPopup()
    })
  })
}

function fitTrailBounds() {
  if (!map || trails.length === 0) return
  const points = trails.flatMap(trail => trail.coords.map(point => [point.lat, point.lng]))
  if (points.length === 0) return
  map.fitBounds(L.latLngBounds(points), { padding: [38, 38] })
}

function isolateTrail(trail) {
  isolatedTrailId.value = trail.id
  selectedTrailId.value = trail.id
  if (!map) return
  map.fitBounds(L.latLngBounds(trail.coords.map(point => [point.lat, point.lng])), { padding: [70, 70] })
}

function resetMap() {
  selectedTrailId.value = null
  isolatedTrailId.value = null
  fitTrailBounds()
}

function trailColor(count) {
  if (count >= 12) return '#ef4444'
  if (count >= 7) return '#f59e0b'
  if (count > 0) return '#22c55e'
  return '#64748b'
}

function densityLabel(count) {
  if (count >= 12) return 'High'
  if (count >= 7) return 'Medium'
  if (count > 0) return 'Low'
  return 'Empty'
}

function trailCardHtml(trail) {
  return `
    <div class="trail-density-card">
      <span>Trail ${escapeHtml(trail.id)}</span>
      <strong>${escapeHtml(trail.name)}</strong>
      <div>${trail.userCount} visitors</div>
    </div>
  `
}

function formatDate(value) {
  if (!value) return '-'
  return value.toLocaleString()
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

watch([selectedTrailId, isolatedTrailId], renderMapLayers)

onMounted(async () => {
  await nextTick()
  initMap()
  await fetchTraffic()
  refreshTimer = setInterval(fetchTraffic, 15000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <main class="visitor-page">
    <div class="container-fluid py-4">
      <div class="visitor-header mb-3">
        <div>
          <h1 class="h4 mb-1">Visitor Density</h1>
          <p class="text-secondary mb-0">Live trail occupancy from visitor traffic telemetry.</p>
        </div>

        <div class="header-actions">
          <div class="total-users">
            <span>Total users</span>
            <strong>{{ totalUsers }}</strong>
          </div>
          <button class="btn btn-sm btn-outline-light" :disabled="loading" @click="fetchTraffic">
            <i class="bi bi-arrow-clockwise me-1"></i>
            Refresh
          </button>
        </div>
      </div>

      <div v-if="error" class="alert alert-danger">
        <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
      </div>

      <section class="visitor-shell">
        <aside class="trail-panel">
          <div class="panel-head">
            <div>
              <h2 class="h6 mb-1">Trail Density</h2>
              <p class="text-secondary small mb-0">{{ formatDate(lastUpdated) }}</p>
            </div>
            <span class="badge text-bg-info">{{ trails.length }} trails</span>
          </div>

          <div v-if="loading && trafficRows.length === 0" class="text-center py-5 text-secondary">
            <div class="spinner-border text-info mb-2"></div>
            <div>Loading visitor traffic...</div>
          </div>

          <div v-else class="trail-list">
            <button
              v-for="trail in trailDashboard"
              :key="trail.id"
              class="trail-row"
              :class="{ selected: selectedTrailId === trail.id }"
              type="button"
              @click="isolateTrail(trail)"
            >
              <span class="trail-color" :style="{ background: trailColor(trail.userCount) }"></span>
              <span class="trail-meta">
                <span class="trail-title">Trail {{ trail.id }}</span>
                <strong>{{ trail.name }}</strong>
                <small>{{ trail.length }} · {{ densityLabel(trail.userCount) }}</small>
              </span>
              <span class="trail-count">{{ trail.userCount }}</span>
            </button>

            <button
              class="all-trails-button"
              type="button"
              @click="resetMap"
            >
              <i class="bi bi-people-fill me-1"></i>
              All Trial Visitor
              <span>{{ totalUsers }}</span>
            </button>
          </div>
        </aside>

        <section class="map-panel">
          <div class="map-toolbar">
            <div>
              <span class="map-title">
                {{ isolatedTrailId ? `Trail ${isolatedTrailId} Focus` : 'Smart Park Trails' }}
              </span>
              <span class="map-subtitle">Hover or click a trail to see its visitor count</span>
            </div>
            <button class="btn btn-sm btn-outline-light" @click="resetMap">
              <i class="bi bi-arrows-fullscreen me-1"></i>
              Fit
            </button>
          </div>
          <div ref="mapContainer" class="visitor-map"></div>
        </section>
      </section>
    </div>
  </main>
</template>

<style scoped>
.visitor-page {
  background: #0f172a;
  color: #f8fafc;
  min-height: 100vh;
}

.visitor-header,
.header-actions,
.panel-head,
.map-toolbar {
  align-items: center;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
}

.header-actions {
  flex-wrap: wrap;
}

.total-users {
  align-items: center;
  background: rgba(14, 165, 233, 0.14);
  border: 1px solid rgba(14, 165, 233, 0.36);
  border-radius: 8px;
  display: flex;
  gap: 0.7rem;
  padding: 0.45rem 0.75rem;
}

.total-users span {
  color: #bae6fd;
  font-size: 0.78rem;
  text-transform: uppercase;
}

.total-users strong {
  color: #f8fafc;
  font-size: 1.1rem;
}

.visitor-shell {
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
}

.trail-panel,
.map-panel {
  background: rgba(15, 23, 42, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 8px;
}

.trail-panel {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 150px);
  min-height: 620px;
  padding: 1rem;
}

.trail-list {
  display: grid;
  gap: 0.65rem;
  margin-top: 1rem;
  overflow: auto;
  padding-right: 0.25rem;
}

.trail-row {
  align-items: center;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  color: #f8fafc;
  display: grid;
  gap: 0.65rem;
  grid-template-columns: 0.55rem minmax(0, 1fr) auto;
  min-height: 5.4rem;
  padding: 0.75rem;
  text-align: left;
}

.trail-row:hover,
.trail-row.selected {
  background: rgba(14, 165, 233, 0.12);
  border-color: rgba(14, 165, 233, 0.42);
}

.all-trails-button {
  align-items: center;
  background: rgba(14, 165, 233, 0.12);
  border: 1px solid rgba(14, 165, 233, 0.38);
  border-radius: 8px;
  color: #e0f2fe;
  display: flex;
  font-weight: 800;
  justify-content: space-between;
  margin-top: 0.25rem;
  min-height: 2.8rem;
  padding: 0.65rem 0.8rem;
}

.all-trails-button:hover {
  background: rgba(14, 165, 233, 0.2);
}

.all-trails-button span {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  color: #ffffff;
  min-width: 2.5rem;
  padding: 0.25rem 0.55rem;
  text-align: center;
}

.trail-color {
  align-self: stretch;
  border-radius: 999px;
}

.trail-meta {
  display: grid;
  gap: 0.15rem;
  min-width: 0;
}

.trail-meta strong,
.trail-title,
.trail-meta small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trail-title {
  color: #7dd3fc;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.78rem;
  font-weight: 800;
}

.trail-meta small {
  color: #94a3b8;
}

.trail-count {
  align-items: center;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  display: inline-flex;
  font-size: 1.15rem;
  font-weight: 800;
  height: 2.6rem;
  justify-content: center;
  min-width: 3rem;
}

.map-panel {
  min-height: 620px;
  overflow: hidden;
  position: relative;
}

.map-toolbar {
  background: rgba(15, 23, 42, 0.92);
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  padding: 0.85rem 1rem;
}

.map-title,
.map-subtitle {
  display: block;
}

.map-title {
  font-weight: 800;
}

.map-subtitle {
  color: #94a3b8;
  font-size: 0.85rem;
}

.visitor-map {
  height: calc(100% - 64px);
  min-height: 556px;
  width: 100%;
}

:deep(.leaflet-container) {
  background: #111827;
  color: #111827;
}

:deep(.leaflet-tooltip) {
  background: rgba(15, 23, 42, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 6px;
  color: #f8fafc;
}

:deep(.leaflet-popup-content-wrapper) {
  background: rgba(15, 23, 42, 0.96);
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  color: #f8fafc;
}

:deep(.leaflet-popup-tip) {
  background: rgba(15, 23, 42, 0.96);
}

:deep(.trail-density-card) {
  display: grid;
  gap: 0.15rem;
  min-width: 140px;
}

:deep(.trail-density-card span) {
  color: #7dd3fc;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.78rem;
  font-weight: 800;
}

:deep(.trail-density-card strong) {
  color: #f8fafc;
}

:deep(.trail-density-card div) {
  color: #fbbf24;
  font-size: 1rem;
  font-weight: 900;
}

@media (max-width: 992px) {
  .visitor-header,
  .map-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .visitor-shell {
    grid-template-columns: 1fr;
  }

  .trail-panel {
    max-height: none;
    min-height: auto;
  }

  .map-panel {
    min-height: 540px;
  }

  .visitor-map {
    min-height: 476px;
  }
}
</style>
