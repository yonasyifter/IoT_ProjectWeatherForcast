<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import { rcmsApi } from '../services/rcmsApi.js'

const loading  = ref(false)
const error    = ref('')
const devices  = ref([])
const selectedSn = ref('')
const gpsPoints  = ref([])    // history track
const liveGps    = ref(null)  // current position
const pageNum  = ref(1)
const pageSize = ref(50)

const now = Date.now()
const beginTime = ref(now - 24 * 60 * 60 * 1000) // last 24h
const endTime   = ref(now)

let map = null
let L   = null
let trackLine = null
let markers   = []

async function initLeaflet() {
  L = (await import('leaflet')).default
  await import('leaflet/dist/leaflet.css')

  // Fix default marker icon path broken by bundlers
  delete L.Icon.Default.prototype._getIconUrl
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    iconUrl:       'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    shadowUrl:     'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  })

  map = L.map('rcms-gps-map', { zoomControl: true }).setView([0, 0], 2)
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '© OpenStreetMap © CARTO',
    maxZoom: 19,
  }).addTo(map)
}

async function loadDevices() {
  try {
    const data = await rcmsApi.getDevices(1, 50)
    devices.value = Array.isArray(data) ? data : (data?.list || data?.records || [])
    if (devices.value.length) selectedSn.value = devices.value[0].sn
  } catch(e) { error.value = e.message }
}

async function loadGpsTrack() {
  if (!selectedSn.value) return
  loading.value = true
  error.value   = ''
  gpsPoints.value = []
  liveGps.value   = null
  clearMap()

  try {
    const [trackData, liveData] = await Promise.all([
      rcmsApi.getGpsReport(selectedSn.value, {
        pageNum: pageNum.value, pageSize: pageSize.value,
        beginTime: beginTime.value, endTime: endTime.value,
      }).catch(() => null),
      rcmsApi.getDeviceGpsData(selectedSn.value).catch(() => null),
    ])

    const points = Array.isArray(trackData) ? trackData : (trackData?.list || trackData?.records || [])
    gpsPoints.value = points

    if (liveData) liveGps.value = liveData

    await nextTick()
    renderMap(points, liveData)
  } catch(e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function clearMap() {
  if (!map) return
  markers.forEach(m => map.removeLayer(m))
  markers = []
  if (trackLine) { map.removeLayer(trackLine); trackLine = null }
}

function renderMap(points, live) {
  if (!map || !L) return
  clearMap()

  const latLngs = points
    .filter(p => p.lat != null && p.lng != null)
    .map(p => [parseFloat(p.lat), parseFloat(p.lng)])

  if (latLngs.length > 1) {
    trackLine = L.polyline(latLngs, { color: '#60a5fa', weight: 3, opacity: 0.8 }).addTo(map)

    // Start marker (green)
    const startM = L.circleMarker(latLngs[0], { radius: 8, color: '#22c55e', fillColor: '#22c55e', fillOpacity: 1 })
      .bindPopup(`<b>Start</b><br>${formatTs(points[0].time)}`)
      .addTo(map)
    markers.push(startM)

    map.fitBounds(trackLine.getBounds(), { padding: [40, 40] })
  }

  // Live position (blue pulsing)
  const liveCoord = live?.lat && live?.lng
    ? [parseFloat(live.lat), parseFloat(live.lng)]
    : latLngs[latLngs.length - 1]

  if (liveCoord) {
    const liveMarker = L.marker(liveCoord, {
      icon: L.divIcon({
        className: '',
        html: `<div style="width:16px;height:16px;background:#3b82f6;border:3px solid white;border-radius:50%;box-shadow:0 0 0 4px rgba(59,130,246,0.3)"></div>`,
        iconSize: [16, 16], iconAnchor: [8, 8],
      })
    }).bindPopup(`<b>Current Position</b><br>Lat: ${liveCoord[0].toFixed(5)}<br>Lng: ${liveCoord[1].toFixed(5)}`).addTo(map)
    markers.push(liveMarker)
    if (!latLngs.length) map.setView(liveCoord, 14)
  }
}

function formatTs(ts) {
  if (!ts) return '—'
  return new Date(Number(ts)).toLocaleString()
}

onMounted(async () => {
  await loadDevices()
  await nextTick()
  await initLeaflet()
  if (selectedSn.value) await loadGpsTrack()
})

onUnmounted(() => { if (map) { map.remove(); map = null } })
</script>

<template>
  <AppShell
    :breadcrumbs="['IOT-Smart Park', 'RCMS', 'GPS Tracking']"
    title="GPS Device Tracking"
    :tabs="[]" active-tab=""
  >
    <template #toolbar>
      <div class="d-flex flex-wrap gap-2 align-items-center">
        <select v-model="selectedSn"
                class="form-select form-select-sm bg-dark text-white border-secondary" style="width:200px">
          <option v-for="d in devices" :key="d.sn" :value="d.sn">{{ d.sn }}</option>
        </select>
        <button class="btn btn-sm btn-primary" @click="pageNum=1; loadGpsTrack()" :disabled="loading">
          <i class="bi bi-geo-alt me-1"></i>Track Device
        </button>
      </div>
    </template>

    <div v-if="error" class="alert alert-danger mx-3 mt-3">
      <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
    </div>

    <div class="d-flex flex-column flex-md-row gap-3 p-3" style="height: calc(100vh - 200px); min-height: 500px;">
      <!-- Map -->
      <div class="flex-grow-1 rounded-3 overflow-hidden position-relative" style="min-height: 400px;">
        <div id="rcms-gps-map" style="width:100%; height:100%; border-radius:12px;"></div>

        <!-- Live info overlay -->
        <div v-if="liveGps" class="position-absolute top-0 start-0 m-2 px-3 py-2 rounded-3 text-white small"
             style="background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); z-index: 1000;">
          <div class="fw-semibold mb-1 text-info"><i class="bi bi-geo-alt-fill me-1"></i>Live Position</div>
          <div>Lat: {{ liveGps.lat ?? '—' }}</div>
          <div>Lng: {{ liveGps.lng ?? '—' }}</div>
          <div class="text-secondary">{{ formatTs(liveGps.time) }}</div>
        </div>

        <div v-if="loading" class="position-absolute top-50 start-50 translate-middle"
             style="z-index:1000;">
          <div class="spinner-border text-primary"></div>
        </div>
      </div>

      <!-- Track table sidebar -->
      <div class="card border-0 text-white" style="background: rgba(255,255,255,0.04); border-radius:12px; width:300px; flex-shrink:0; overflow:hidden;">
        <div class="card-header border-0" style="background: rgba(255,255,255,0.05);">
          <span class="fw-semibold small">
            <i class="bi bi-list-ul me-2 text-primary"></i>GPS History
            <span class="badge bg-primary ms-2">{{ gpsPoints.length }}</span>
          </span>
        </div>
        <div class="overflow-auto" style="flex:1; max-height: 100%;">
          <div v-if="gpsPoints.length === 0" class="text-center text-secondary py-4">
            <i class="bi bi-map fs-2"></i>
            <p class="mt-2 small">Select a device and click Track</p>
          </div>
          <table v-else class="table table-dark table-sm table-hover mb-0">
            <thead class="sticky-top">
              <tr style="background: #1a1a2e;">
                <th class="small">Time</th>
                <th class="small">Lat</th>
                <th class="small">Lng</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(p, i) in gpsPoints" :key="i" style="border-color: rgba(255,255,255,0.05)">
                <td class="small text-secondary text-nowrap">{{ formatTs(p.time) }}</td>
                <td class="small font-monospace">{{ p.lat?.toFixed?.(4) ?? p.lat }}</td>
                <td class="small font-monospace">{{ p.lng?.toFixed?.(4) ?? p.lng }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- Pagination -->
        <div class="d-flex justify-content-between px-2 py-1 border-top border-secondary small">
          <button class="btn btn-sm btn-outline-secondary py-0 px-2" :disabled="pageNum<=1" @click="pageNum--; loadGpsTrack()">‹</button>
          <span class="text-secondary align-self-center">{{ pageNum }}</span>
          <button class="btn btn-sm btn-outline-secondary py-0 px-2" :disabled="gpsPoints.length < pageSize" @click="pageNum++; loadGpsTrack()">›</button>
        </div>
      </div>
    </div>
  </AppShell>
</template>
