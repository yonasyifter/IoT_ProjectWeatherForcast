<!-- S6000Dashboard.vue - Multi-Device Support with Auto-Fit Charts & Expandable Panels -->
<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import api from '../../utils/api.js'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

/* -----------------------
 * Constants
 * --------------------- */
const SVG_WIDTH = 1200
const SVG_HEIGHT = 280
const PADDING = { left: 126, right: 118, top: 30, bottom: 88 }
const INNER_WIDTH = SVG_WIDTH - PADDING.left - PADDING.right
const INNER_HEIGHT = SVG_HEIGHT - PADDING.top - PADDING.bottom
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 70

// Expanded modal chart dims (larger viewport)
const EXP_WIDTH = 1100
const EXP_HEIGHT = 400
const EXP_PAD = { left: 96, right: 108, top: 36, bottom: 78 }
const EXP_INNER_W = EXP_WIDTH - EXP_PAD.left - EXP_PAD.right
const EXP_INNER_H = EXP_HEIGHT - EXP_PAD.top - EXP_PAD.bottom

const TIME_RANGES = {
  '1h': 60,
  '3h': 180,
  '6h': 360,
  '24h': 1440
}

/* -----------------------
 * State
 * --------------------- */
const selectedDevice = ref('')
const deviceNotFound = ref(false)
const availableDevices = ref([])
const timeRange = ref('3h')
const refreshSeconds = ref(30)

const sensorData = ref([])
const loading = ref(false)
const error = ref('')

const currentReadings = ref({
  temperature: 23.2,
  humidity: 49,
  pressure: 1013,
  distance: 50,
  tilt: 10,
  noise: 55,
  gps: { latitude: 39.0742, longitude: 16.3027 }
})

const hoveredPoint = ref(null)

// Expanded chart modal state
const expandedChart = ref(null) // 'tempHum' | 'noise' | null
const expandedHovered = ref(null)

let refreshTimer = null
let map = null
let marker = null
const mapContainer = ref(null)

/* -----------------------
 * Utility
 * --------------------- */
const toNum = (v) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

const formatTimestamp = (ts) => {
  try {
    return new Date(ts).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch { return '' }
}

const formatShortTime = (ts) => {
  try {
    return new Date(ts).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch { return '' }
}

const minutesForRange = (range) => TIME_RANGES[range] || 180

const fmt = (value, digits = 1) => {
  const n = toNum(value)
  return n === null ? '—' : n.toFixed(digits)
}

/* -----------------------
 * Auto-fit helpers
 * Adds 5% padding above/below data range so lines never hug axes
 * --------------------- */
const fitRange = (min, max) => {
  const safeMin = Number.isFinite(min) ? min : 0
  const safeMax = Number.isFinite(max) ? max : safeMin + 1
  const rawLo = safeMin === safeMax ? safeMin - 1 : safeMin
  const rawHi = safeMin === safeMax ? safeMax + 1 : safeMax
  const paddedLo = rawLo - (rawHi - rawLo) * 0.08
  const paddedHi = rawHi + (rawHi - rawLo) * 0.08
  const rawStep = (paddedHi - paddedLo || 1) / 5
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)))
  const normalized = rawStep / magnitude
  const niceStep = (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10) * magnitude
  return {
    lo: Math.floor(paddedLo / niceStep) * niceStep,
    hi: Math.ceil(paddedHi / niceStep) * niceStep
  }
}

/* -----------------------
 * Coordinate helpers – normal chart
 * --------------------- */
const xForIndex = (i, len, pad = PADDING, iw = INNER_WIDTH) => {
  if (len <= 1) return pad.left + iw / 2
  return pad.left + (iw * i) / (len - 1)
}

const yForValue = (v, lo, hi, pad = PADDING, ih = INNER_HEIGHT) => {
  if (v == null) return null
  const range = hi - lo || 1
  const t = (v - lo) / range
  return pad.top + (1 - t) * ih
}

/* -----------------------
 * Axis labels
 * --------------------- */
const buildTimeLabels = (rows, targetCount, pad = PADDING, iw = INNER_WIDTH) => {
  const len = rows.length
  if (len === 0) return []
  const maxLabels = Math.max(2, Math.min(targetCount, len))
  const seen = new Set()
  const labels = Array.from({ length: maxLabels }, (_, i) => {
    const index = maxLabels === 1 ? 0 : Math.round((i * (len - 1)) / (maxLabels - 1))
    return index
  })
    .filter(index => {
      if (seen.has(index)) return false
      seen.add(index)
      return true
    })
    .map(index => ({
      x: xForIndex(index, len, pad, iw),
      text: formatShortTime(rows[index].time),
      index
    }))
  return labels
}

const getTimeLabels = computed(() => buildTimeLabels(sensorData.value, 6))

const getTimeLabelsExp = computed(() => buildTimeLabels(sensorData.value, 8, EXP_PAD, EXP_INNER_W))

const makeYLabels = (lo, hi, unit = '', count = 5, pad = PADDING, ih = INNER_HEIGHT) => {
  const range = hi - lo || 1
  const rawStep = range / count
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)))
  const normalized = rawStep / magnitude
  const niceStep = (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10) * magnitude
  const niceLo = Math.floor(lo / niceStep) * niceStep
  const niceHi = Math.ceil(hi / niceStep) * niceStep
  return Array.from({ length: count + 1 }, (_, i) => ({
    y: pad.top + ih - (ih * i / count),
    text: (niceLo + ((niceHi - niceLo) / count) * i).toFixed(niceStep < 1 ? 2 : 1) + unit
  }))
}

/* -----------------------
 * Stats
 * --------------------- */
const calcStat = (key, op) => {
  const vals = sensorData.value.map(d => d[key]).filter(v => v != null)
  if (!vals.length) return 0
  if (op === 'avg') return vals.reduce((a, b) => a + b, 0) / vals.length
  if (op === 'min') return Math.min(...vals)
  return Math.max(...vals)
}

const avgTemperature = computed(() => calcStat('temperature', 'avg'))
const minTemperature = computed(() => calcStat('temperature', 'min'))
const maxTemperature = computed(() => calcStat('temperature', 'max'))
const avgHumidity = computed(() => calcStat('humidity', 'avg'))
const minHumidity = computed(() => calcStat('humidity', 'min'))
const maxHumidity = computed(() => calcStat('humidity', 'max'))
const avgPressure = computed(() => calcStat('pressure', 'avg'))
const avgNoise = computed(() => calcStat('noise', 'avg'))
const minNoise = computed(() => calcStat('noise', 'min'))
const maxNoise = computed(() => calcStat('noise', 'max'))
const avgPredictionTime = computed(() => calcStat('prediction_time', 'avg'))
const minPredictionTime = computed(() => calcStat('prediction_time', 'min'))
const maxPredictionTime = computed(() => calcStat('prediction_time', 'max'))

// Auto-fit ranges
const tempRange = computed(() => fitRange(minTemperature.value, maxTemperature.value))
const humRange = computed(() => fitRange(minHumidity.value, maxHumidity.value))
const noiseRange = computed(() => fitRange(minNoise.value, maxNoise.value))
const predictionTimeRange = computed(() => fitRange(minPredictionTime.value, maxPredictionTime.value))

/* -----------------------
 * Y-axis labels (auto-fit)
 * --------------------- */
const temperatureYLabels = computed(() => makeYLabels(tempRange.value.lo, tempRange.value.hi, '°C'))
const humidityYLabels = computed(() => makeYLabels(humRange.value.lo, humRange.value.hi, '%'))
const noiseYLabels = computed(() => makeYLabels(noiseRange.value.lo, noiseRange.value.hi, 'dB'))

const temperatureYLabelsExp = computed(() => makeYLabels(tempRange.value.lo, tempRange.value.hi, '°C', 6, EXP_PAD, EXP_INNER_H))
const humidityYLabelsExp = computed(() => makeYLabels(humRange.value.lo, humRange.value.hi, '%', 6, EXP_PAD, EXP_INNER_H))
const noiseYLabelsExp = computed(() => makeYLabels(noiseRange.value.lo, noiseRange.value.hi, 'dB', 6, EXP_PAD, EXP_INNER_H))

/* -----------------------
 * Series builders (shared for normal + expanded)
 * --------------------- */
const buildSeries = (key, lo, hi, pad = PADDING, iw = INNER_WIDTH, ih = INNER_HEIGHT) => {
  const len = sensorData.value.length
  return sensorData.value
    .map((row, i) => {
      const v = row?.[key] ?? null
      const x = xForIndex(i, len, pad, iw)
      const y = yForValue(v, lo, hi, pad, ih)
      return y != null ? { x, y, v, t: row.time, i } : null
    })
    .filter(Boolean)
}

// Normal charts
const temperatureSeries = computed(() => buildSeries('temperature', tempRange.value.lo, tempRange.value.hi))
const humiditySeries = computed(() => buildSeries('humidity', humRange.value.lo, humRange.value.hi))
const noiseSeries = computed(() => buildSeries('noise', noiseRange.value.lo, noiseRange.value.hi))
const predictionTimeSeries = computed(() => buildSeries('prediction_time', predictionTimeRange.value.lo, predictionTimeRange.value.hi))

// Expanded modal charts
const temperatureSeriesExp = computed(() => buildSeries('temperature', tempRange.value.lo, tempRange.value.hi, EXP_PAD, EXP_INNER_W, EXP_INNER_H))
const humiditySeriesExp = computed(() => buildSeries('humidity', humRange.value.lo, humRange.value.hi, EXP_PAD, EXP_INNER_W, EXP_INNER_H))
const noiseSeriesExp = computed(() => buildSeries('noise', noiseRange.value.lo, noiseRange.value.hi, EXP_PAD, EXP_INNER_W, EXP_INNER_H))

const polylinePoints = (series) => series.map(p => `${p.x},${p.y}`).join(' ')

const temperatureLinePoints = computed(() => polylinePoints(temperatureSeries.value))
const humidityLinePoints = computed(() => polylinePoints(humiditySeries.value))
const predictionTimeLinePoints = computed(() => polylinePoints(predictionTimeSeries.value))
const temperatureLinePointsExp = computed(() => polylinePoints(temperatureSeriesExp.value))
const humidityLinePointsExp = computed(() => polylinePoints(humiditySeriesExp.value))

/* -----------------------
 * Noise bar chart
 * --------------------- */
const buildNoiseBars = (series, pad, iw, ih, len) => {
  const spacing = iw / (len || 1)
  const barWidth = Math.max(2, Math.min(10, spacing * 0.8))
  const baseY = pad.top + ih
  const lo = noiseRange.value.lo
  const hi = noiseRange.value.hi
  const range = hi - lo || 1

  return series.map(p => {
    const normalized = (p.v - lo) / range
    const height = Math.max(1, normalized * ih)
    return { x: p.x - barWidth / 2, y: baseY - height, w: barWidth, h: height, v: p.v, t: p.t, i: p.i }
  })
}

const noiseBars = computed(() =>
  buildNoiseBars(noiseSeries.value, PADDING, INNER_WIDTH, INNER_HEIGHT, sensorData.value.length)
)
const noiseBarsExp = computed(() =>
  buildNoiseBars(noiseSeriesExp.value, EXP_PAD, EXP_INNER_W, EXP_INNER_H, sensorData.value.length)
)

const predictionTimeYLabels = computed(() => makeYLabels(predictionTimeRange.value.lo, predictionTimeRange.value.hi, 'ms'))

/* -----------------------
 * Grid line helpers
 * --------------------- */
const gridLines = (count, pad, iw, ih) =>
  Array.from({ length: count }, (_, i) => ({
    y: pad.top + (ih / count) * (i + 1)
  }))

/* -----------------------
 * Gauge calculations
 * --------------------- */
const humidityGauge = computed(() => {
  const percent = currentReadings.value.humidity / 100
  const offset = GAUGE_CIRCUMFERENCE * (1 - percent * 0.75)
  let color = '#10b981'
  if (currentReadings.value.humidity < 30) color = '#ef4444'
  else if (currentReadings.value.humidity > 60) color = '#3b82f6'
  return { offset, color }
})

const pressureGauge = computed(() => {
  const percent = (currentReadings.value.pressure - 900) / 200
  const offset = GAUGE_CIRCUMFERENCE * (1 - percent * 0.75)
  let color = '#10b981'
  if (currentReadings.value.pressure < 1000) color = '#3b82f6'
  else if (currentReadings.value.pressure > 1020) color = '#ef4444'
  return { offset, color }
})

/* -----------------------
 * Visual helpers
 * --------------------- */
const temperaturePercent = computed(() =>
  Math.min(100, Math.max(0, (currentReadings.value.temperature / 100) * 100))
)

const s6000Position = computed(() => {
  const maxDistance = 200
  const normalized = 1 - Math.min(currentReadings.value.distance, maxDistance) / maxDistance
  return 20 + (200 - 20) * normalized
})

/* -----------------------
 * Leaflet map
 * --------------------- */
const initMap = () => {
  if (!mapContainer.value) return
  if (map) { map.remove(); map = null }
  map = L.map(mapContainer.value).setView(
    [currentReadings.value.gps.latitude, currentReadings.value.gps.longitude], 14
  )
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
  }).addTo(map)
  marker = L.marker([currentReadings.value.gps.latitude, currentReadings.value.gps.longitude]).addTo(map)
  marker.bindPopup(`<b>S6000 Device ${selectedDevice.value}</b><br>
    Lat: ${currentReadings.value.gps.latitude.toFixed(6)}<br>
    Lon: ${currentReadings.value.gps.longitude.toFixed(6)}`)
}

const updateMapMarker = () => {
  if (!map || !marker) return
  const ll = [currentReadings.value.gps.latitude, currentReadings.value.gps.longitude]
  marker.setLatLng(ll)
  marker.setPopupContent(`<b>S6000 Device ${selectedDevice.value}</b><br>
    Lat: ${currentReadings.value.gps.latitude.toFixed(6)}<br>
    Lon: ${currentReadings.value.gps.longitude.toFixed(6)}`)
  map.setView(ll, map.getZoom())
}

/* -----------------------
 * Data fetching
 * --------------------- */
const fetchSensorData = async () => {
  loading.value = true
  error.value = ''
  hoveredPoint.value = null
  deviceNotFound.value = false

  try {
    const minutes = minutesForRange(timeRange.value)
    const data = await api.get(`/api/weather/forecast/?minutes=${minutes}`)
    if (!Array.isArray(data)) throw new Error('Invalid API response format')

    const uniqueDevices = [...new Set(
      data
        .map(d => String(d.device_id ?? '').trim())
        .filter(Boolean)
    )].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    availableDevices.value = uniqueDevices

    const activeDevice = uniqueDevices.includes(String(selectedDevice.value))
      ? String(selectedDevice.value)
      : uniqueDevices[0] || ''

    if (selectedDevice.value !== activeDevice) {
      selectedDevice.value = activeDevice
    }

    const filteredData = data.filter(d => String(d.device_id) === activeDevice)

    if (filteredData.length === 0) {
      deviceNotFound.value = true
      sensorData.value = []
      loading.value = false
      return
    }

    const normalizedData = filteredData
      .map(d => ({
        time: new Date(d._time || d.time).getTime(),
        temperature: toNum(d.temperature),
        humidity: toNum(d.humidity),
        pressure: toNum(d.pressure),
        noise: toNum(d.noise),
        tof: toNum(d.tof),
        angle: toNum(d.angle),
        vibrAccX: toNum(d.vibrAccX),
        vibrAccY: toNum(d.vibrAccY),
        vibrAccZ: toNum(d.vibrAccZ),
        prediction_time: toNum(d.prediction_time),
        latitude: toNum(d.latitude),
        longitude: toNum(d.longitude),
        device_id: d.device_id || activeDevice
      }))
      .filter(d => Number.isFinite(d.time))
      .sort((a, b) => a.time - b.time)

    sensorData.value = normalizedData
    updateCurrentReadings(normalizedData)
    deviceNotFound.value = false
  } catch (e) {
    error.value = e.message || 'Failed to load sensor data'
    if (!deviceNotFound.value) generateSimulatedData()
  } finally {
    loading.value = false
  }
}

const handleDeviceChange = async () => {
  await fetchSensorData()
  if (!deviceNotFound.value && sensorData.value.length > 0) {
    setTimeout(() => { if (map && marker) updateMapMarker(); else initMap() }, 300)
  }
}

const updateCurrentReadings = (data) => {
  if (!data.length) return
  const latest = data[data.length - 1]
  currentReadings.value = {
    temperature: latest.temperature ?? currentReadings.value.temperature,
    humidity: latest.humidity ?? currentReadings.value.humidity,
    pressure: latest.pressure ?? currentReadings.value.pressure,
    distance: latest.tof ?? currentReadings.value.distance,
    tilt: latest.angle ?? currentReadings.value.tilt,
    noise: latest.noise ?? currentReadings.value.noise,
    gps: (latest.latitude && latest.longitude)
      ? { latitude: latest.latitude, longitude: latest.longitude }
      : currentReadings.value.gps
  }
  if (map && marker) updateMapMarker()
}

const generateSimulatedData = () => {
  const now = Date.now()
  const minutes = minutesForRange(timeRange.value)
  const points = Math.min(minutes, 180)
  const deviceIndex = Math.max(0, availableDevices.value.indexOf(selectedDevice.value))
  const numericSuffix = Number(String(selectedDevice.value).match(/\d+$/)?.[0])
  const deviceOffset = Number.isFinite(numericSuffix) ? numericSuffix % 5 : deviceIndex
  const tempBase = 22 + deviceOffset * 0.5
  const humBase = 47 + deviceOffset * 2
  const noiseBase = 50 + deviceOffset * 3
  const gpsOffsets = [
    { lat: 0, lng: 0 }, { lat: 0.002, lng: 0.003 },
    { lat: -0.001, lng: 0.002 }, { lat: 0.003, lng: -0.001 }, { lat: -0.002, lng: -0.002 }
  ]
  const go = gpsOffsets[deviceOffset] || gpsOffsets[0]

  sensorData.value = Array.from({ length: points }, (_, i) => ({
    time: now - (points - i) * 60000,
    temperature: tempBase + Math.random() * 3 + Math.sin(i / 20) * 2,
    humidity: humBase + Math.random() * 5 + Math.cos(i / 15) * 3,
    pressure: 1010 + Math.random() * 10,
    noise: noiseBase + Math.random() * 12,
    tof: 30 + Math.random() * 100,
    angle: -15 + Math.random() * 30,
    vibrAccX: Math.random() * 2 - 1,
    vibrAccY: Math.random() * 2 - 1,
    vibrAccZ: Math.random() * 2 - 1,
    prediction_time: 60 + Math.random() * 120,
    latitude: 39.0742 + go.lat + (Math.random() - 0.5) * 0.001,
    longitude: 16.3027 + go.lng + (Math.random() - 0.5) * 0.001,
    device_id: selectedDevice.value
  }))
  updateCurrentReadings(sensorData.value)
}

/* -----------------------
 * Expand / collapse
 * --------------------- */
const openChart = (type) => {
  expandedChart.value = type
  expandedHovered.value = null
  document.body.style.overflow = 'hidden'
}

const closeChart = () => {
  expandedChart.value = null
  expandedHovered.value = null
  document.body.style.overflow = ''
}

/* -----------------------
 * Event handlers
 * --------------------- */
const handleMouseOver = (type, value, time, isExpanded = false, meta = {}) => {
  const pt = { type, v: value, t: time, ...meta }
  if (isExpanded) expandedHovered.value = pt
  else hoveredPoint.value = pt
}

const handleMouseOut = (isExpanded = false) => {
  if (isExpanded) expandedHovered.value = null
  else hoveredPoint.value = null
}

/* -----------------------
 * Timer / lifecycle
 * --------------------- */
const stopRefreshTimer = () => { if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null } }
const startRefreshTimer = () => {
  stopRefreshTimer()
  if (!refreshSeconds.value || refreshSeconds.value <= 0) return
  refreshTimer = setInterval(fetchSensorData, refreshSeconds.value * 1000)
}

watch(refreshSeconds, startRefreshTimer)
watch(timeRange, fetchSensorData)

onMounted(() => {
  fetchSensorData()
  startRefreshTimer()
  setTimeout(initMap, 100)
  window.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeChart() })
})

onBeforeUnmount(() => {
  stopRefreshTimer()
  if (map) { map.remove(); map = null }
  document.body.style.overflow = ''
})
</script>

<template>
  <div class="dashboard">
    <!-- ===================== EXPAND MODAL ===================== -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="expandedChart" class="modal-overlay" @click.self="closeChart">
          <div class="modal-panel">
            <div class="modal-header">
              <h2 class="modal-title">
                <i :class="expandedChart === 'noise' ? 'bi bi-soundwave' : 'bi bi-graph-up'"></i>
                {{ expandedChart === 'noise' ? 'Sound Level — Expanded' : 'Temperature & Humidity — Expanded' }}
              </h2>
              <button class="close-btn" @click="closeChart" aria-label="Close">
                <i class="bi bi-x-lg"></i>
              </button>
            </div>

            <!-- EXPANDED: Temp + Humidity -->
            <div v-if="expandedChart === 'tempHum'" class="modal-chart-wrap" style="position:relative">
              <svg :viewBox="`0 0 ${EXP_WIDTH} ${EXP_HEIGHT}`" style="width:100%;display:block">
                <!-- Grid -->
                <g class="chart-grid-lines">
                  <line v-for="(g,i) in gridLines(8, EXP_PAD, EXP_INNER_W, EXP_INNER_H)"
                    :key="`eg-h-${i}`"
                    :x1="EXP_PAD.left" :y1="g.y"
                    :x2="EXP_PAD.left + EXP_INNER_W" :y2="g.y"
                    stroke="currentColor" stroke-width="1"/>
                  <line v-for="j in 10" :key="`eg-v-${j}`"
                    :x1="EXP_PAD.left + (EXP_INNER_W / 10) * j" :y1="EXP_PAD.top"
                    :x2="EXP_PAD.left + (EXP_INNER_W / 10) * j" :y2="EXP_PAD.top + EXP_INNER_H"
                    stroke="currentColor" stroke-width="1"/>
                </g>
                <!-- Axes -->
                <line :x1="EXP_PAD.left" :y1="EXP_PAD.top" :x2="EXP_PAD.left" :y2="EXP_PAD.top + EXP_INNER_H" stroke="#64748b" stroke-width="2"/>
                <line :x1="EXP_PAD.left + EXP_INNER_W" :y1="EXP_PAD.top" :x2="EXP_PAD.left + EXP_INNER_W" :y2="EXP_PAD.top + EXP_INNER_H" stroke="#64748b" stroke-width="2"/>
                <line :x1="EXP_PAD.left" :y1="EXP_PAD.top + EXP_INNER_H" :x2="EXP_PAD.left + EXP_INNER_W" :y2="EXP_PAD.top + EXP_INNER_H" stroke="#64748b" stroke-width="2"/>
                <!-- Y temp labels -->
                <text v-for="(l,i) in temperatureYLabelsExp" :key="`ety-${i}`"
                  :x="EXP_PAD.left - 10" :y="l.y"
                  text-anchor="end" dominant-baseline="middle" fill="#ff9b3d" font-size="11" font-weight="600">{{ l.text }}</text>
                <!-- Y hum labels -->
                <text v-for="(l,i) in humidityYLabelsExp" :key="`ehy-${i}`"
                  :x="EXP_PAD.left + EXP_INNER_W + 10" :y="l.y"
                  text-anchor="start" dominant-baseline="middle" fill="#3d9fff" font-size="11" font-weight="600">{{ l.text }}</text>
                <!-- X time labels -->
                <text v-for="(l,i) in getTimeLabelsExp" :key="`etx-${i}`"
                  :x="l.x" :y="EXP_PAD.top + EXP_INNER_H + 28"
                  text-anchor="end" fill="#cbd5e1" font-size="10" font-weight="600"
                  :transform="`rotate(-28, ${l.x}, ${EXP_PAD.top + EXP_INNER_H + 28})`">{{ l.text }}</text>
                <line v-if="expandedHovered?.x" :x1="expandedHovered.x" :y1="EXP_PAD.top" :x2="expandedHovered.x" :y2="EXP_PAD.top + EXP_INNER_H" stroke="#94a3b8" stroke-width="1" stroke-dasharray="4 4" opacity="0.55"/>
                <!-- Temp line -->
                <polyline v-if="temperatureSeriesExp.length"
                  :points="temperatureLinePointsExp"
                  fill="none" stroke="#ff9b3d" stroke-width="2"/>
                <!-- Hum line -->
                <polyline v-if="humiditySeriesExp.length"
                  :points="humidityLinePointsExp"
                  fill="none" stroke="#3d9fff" stroke-width="2"/>
                <!-- Temp points -->
                <circle v-for="p in temperatureSeriesExp" :key="`etp-${p.i}`"
                  :cx="p.x" :cy="p.y" r="4"
                  fill="#ff9b3d" class="chart-point"
                  @mouseover="handleMouseOver('temp', p.v, p.t, true, { x: p.x, y: p.y })"
                  @mouseout="handleMouseOut(true)">
                  <title>{{ p.v?.toFixed(2) }}°C @ {{ formatTimestamp(p.t) }}</title>
                </circle>
                <!-- Hum points -->
                <circle v-for="p in humiditySeriesExp" :key="`ehp-${p.i}`"
                  :cx="p.x" :cy="p.y" r="4"
                  fill="#3d9fff" class="chart-point"
                  @mouseover="handleMouseOver('hum', p.v, p.t, true, { x: p.x, y: p.y })"
                  @mouseout="handleMouseOut(true)">
                  <title>{{ p.v?.toFixed(2) }}% @ {{ formatTimestamp(p.t) }}</title>
                </circle>
                <!-- Axis labels -->
                <text :x="EXP_PAD.left - 50" :y="EXP_PAD.top + EXP_INNER_H / 2"
                  text-anchor="middle" fill="#ff9b3d" font-size="12" font-weight="700"
                  :transform="`rotate(-90, ${EXP_PAD.left - 50}, ${EXP_PAD.top + EXP_INNER_H / 2})`">Temperature (°C)</text>
                <text :x="EXP_PAD.left + EXP_INNER_W + 58" :y="EXP_PAD.top + EXP_INNER_H / 2"
                  text-anchor="middle" fill="#3d9fff" font-size="12" font-weight="700"
                  :transform="`rotate(90, ${EXP_PAD.left + EXP_INNER_W + 58}, ${EXP_PAD.top + EXP_INNER_H / 2})`">Humidity (%)</text>
                <text :x="EXP_PAD.left + EXP_INNER_W / 2" :y="EXP_PAD.top + EXP_INNER_H + 50"
                  text-anchor="middle" fill="#cbd5e1" font-size="12" font-weight="700">Time</text>
              </svg>
              <!-- Crosshair tooltip -->
              <div v-if="expandedHovered" class="tooltip" :class="`tooltip-${expandedHovered.type}`" style="bottom:24px;left:24px">
                {{ expandedHovered.v?.toFixed(2) }}{{ expandedHovered.type === 'temp' ? '°C' : '%' }}
                <div class="tooltip-sub">{{ formatTimestamp(expandedHovered.t) }}</div>
              </div>
            </div>

            <!-- EXPANDED: Noise -->
            <div v-if="expandedChart === 'noise'" class="modal-chart-wrap" style="position:relative">
              <svg :viewBox="`0 0 ${EXP_WIDTH} ${EXP_HEIGHT}`" style="width:100%;display:block">
                <!-- Grid -->
                <g class="chart-grid-lines">
                  <line v-for="(g,i) in gridLines(8, EXP_PAD, EXP_INNER_W, EXP_INNER_H)"
                    :key="`en-h-${i}`"
                    :x1="EXP_PAD.left" :y1="g.y"
                    :x2="EXP_PAD.left + EXP_INNER_W" :y2="g.y"
                    stroke="currentColor" stroke-width="1"/>
                </g>
                <!-- Axes -->
                <line :x1="EXP_PAD.left" :y1="EXP_PAD.top" :x2="EXP_PAD.left" :y2="EXP_PAD.top + EXP_INNER_H" stroke="#64748b" stroke-width="2"/>
                <line :x1="EXP_PAD.left" :y1="EXP_PAD.top + EXP_INNER_H" :x2="EXP_PAD.left + EXP_INNER_W" :y2="EXP_PAD.top + EXP_INNER_H" stroke="#64748b" stroke-width="2"/>
                <!-- Y labels -->
                <text v-for="(l,i) in noiseYLabelsExp" :key="`eny-${i}`"
                  :x="EXP_PAD.left - 10" :y="l.y"
                  text-anchor="end" dominant-baseline="middle" fill="#22c55e" font-size="11" font-weight="600">{{ l.text }}</text>
                <!-- X labels -->
                <text v-for="(l,i) in getTimeLabelsExp" :key="`enx-${i}`"
                  :x="l.x" :y="EXP_PAD.top + EXP_INNER_H + 28"
                  text-anchor="end" fill="#cbd5e1" font-size="10" font-weight="600"
                  :transform="`rotate(-28, ${l.x}, ${EXP_PAD.top + EXP_INNER_H + 28})`">{{ l.text }}</text>
                <line v-if="expandedHovered?.type === 'noise' && expandedHovered.x" :x1="expandedHovered.x" :y1="EXP_PAD.top" :x2="expandedHovered.x" :y2="EXP_PAD.top + EXP_INNER_H" stroke="#94a3b8" stroke-width="1" stroke-dasharray="4 4" opacity="0.55"/>
                <!-- Bars -->
                <rect v-for="b in noiseBarsExp" :key="`enb-${b.i}`"
                  :x="b.x" :y="b.y" :width="b.w" :height="b.h" rx="1"
                  :fill="`hsl(${120 - ((b.v - noiseRange.lo) / ((noiseRange.hi - noiseRange.lo) || 1)) * 60}, 70%, 50%)`"
                  class="noise-bar"
                  @mouseover="handleMouseOver('noise', b.v, b.t, true, { x: b.x + b.w / 2, y: b.y })"
                  @mouseout="handleMouseOut(true)">
                  <title>{{ b.v?.toFixed(2) }} dB @ {{ formatTimestamp(b.t) }}</title>
                </rect>
                <!-- Axis labels -->
                <text :x="EXP_PAD.left - 50" :y="EXP_PAD.top + EXP_INNER_H / 2"
                  text-anchor="middle" fill="#22c55e" font-size="12" font-weight="700"
                  :transform="`rotate(-90, ${EXP_PAD.left - 50}, ${EXP_PAD.top + EXP_INNER_H / 2})`">Sound Level (dB)</text>
                <text :x="EXP_PAD.left + EXP_INNER_W / 2" :y="EXP_PAD.top + EXP_INNER_H + 50"
                  text-anchor="middle" fill="#cbd5e1" font-size="12" font-weight="700">Time</text>
              </svg>
              <div v-if="expandedHovered?.type === 'noise'" class="tooltip tooltip-noise" style="bottom:24px;left:24px">
                {{ expandedHovered.v?.toFixed(2) }} dB
                <div class="tooltip-sub">{{ formatTimestamp(expandedHovered.t) }}</div>
              </div>
            </div>

            <!-- Expanded legend & stats -->
            <div class="modal-footer">
              <template v-if="expandedChart === 'tempHum'">
                <span class="legend-item"><span class="legend-dot temp"></span> Temperature · avg {{ avgTemperature.toFixed(2) }}°C · min {{ minTemperature.toFixed(2) }}°C · max {{ maxTemperature.toFixed(2) }}°C</span>
                <span class="legend-item"><span class="legend-dot hum"></span> Humidity · avg {{ avgHumidity.toFixed(2) }}% · min {{ minHumidity.toFixed(2) }}% · max {{ maxHumidity.toFixed(2) }}%</span>
              </template>
              <template v-else>
                <span class="legend-item"><span class="legend-dot noise"></span> Sound Level · avg {{ avgNoise.toFixed(2) }} dB · min {{ minNoise.toFixed(2) }} dB · max {{ maxNoise.toFixed(2) }} dB</span>
              </template>
              <span class="legend-item muted">{{ sensorData.length }} data points · {{ timeRange }} · Device {{ selectedDevice }}</span>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Header -->
    <header class="header">
      <div class="header-left">
        <h1 class="header-title">
          <i class="bi bi-cpu"></i>
          S6000 SENSOR DASHBOARD
        </h1>
        <p class="header-subtitle">Real-time IoT sensor monitoring with InfluxDB integration</p>
      </div>
      <div class="header-right">
        <span class="header-pill device-pill">
          <i class="bi bi-hdd-rack"></i> Device {{ selectedDevice }}
        </span>
        <span class="header-pill">
          <i class="bi bi-clock"></i> {{ timeRange }}
        </span>
        <span class="header-pill">
          <i class="bi bi-arrow-repeat"></i>
          {{ refreshSeconds ? `${refreshSeconds}s` : 'off' }}
        </span>
        <span class="header-pill" :class="{ 'pill-active': !loading }">
          <i :class="loading ? 'bi bi-hourglass-split' : 'bi bi-check-circle-fill'"></i>
          {{ loading ? 'Loading' : 'Live' }}
        </span>
      </div>
    </header>

    <!-- Controls -->
    <section class="panel">
      <div class="controls-grid">
        <div>
          <label class="label"><i class="bi bi-hdd-rack"></i> Device ID</label>
          <select
            v-model="selectedDevice"
            class="input"
            :disabled="loading && availableDevices.length === 0"
            @change="handleDeviceChange"
          >
            <option value="" disabled>
              {{ loading ? 'Loading devices...' : 'Select device' }}
            </option>
            <option
              v-for="deviceId in availableDevices"
              :key="deviceId"
              :value="deviceId"
            >
              {{ deviceId }}
            </option>
          </select>
          <div class="help">
            <strong>Available devices:</strong>
            {{ availableDevices.length ? availableDevices.join(', ') : (loading ? 'Loading…' : '—') }}
          </div>
        </div>
        <div>
          <label class="label"><i class="bi bi-calendar-range"></i> Time Range</label>
          <select v-model="timeRange" class="input">
            <option value="1h">Last 1 Hour</option>
            <option value="3h">Last 3 Hours</option>
            <option value="6h">Last 6 Hours</option>
            <option value="24h">Last 24 Hours</option>
          </select>
        </div>
        <div>
          <label class="label"><i class="bi bi-arrow-repeat"></i> Auto Refresh</label>
          <select v-model.number="refreshSeconds" class="input">
            <option :value="0">Off</option>
            <option :value="10">Every 10s</option>
            <option :value="30">Every 30s</option>
            <option :value="60">Every 60s</option>
          </select>
        </div>
        <div class="load-wrap">
          <button class="btn btn-primary" @click="fetchSensorData" :disabled="loading">
            <i :class="loading ? 'bi bi-hourglass-split' : 'bi bi-arrow-clockwise'"></i>
            {{ loading ? 'Loading…' : 'Refresh Data' }}
          </button>
        </div>
      </div>

      <div v-if="error && !deviceNotFound" class="error">
        <i class="bi bi-exclamation-triangle"></i>
        <span>{{ error }} (using simulated data for Device {{ selectedDevice }})</span>
      </div>

      <div v-if="deviceNotFound" class="device-not-found">
        <i class="bi bi-x-circle"></i>
        <div>
          <h3>No Device Found</h3>
          <p>Device ID <strong>{{ selectedDevice }}</strong> was not found in the database.</p>
          <p>Please check the device ID and try again.</p>
        </div>
      </div>
    </section>

    <!-- Main Grid -->
    <div v-if="!deviceNotFound" class="main-grid">

      <!-- Thermometer -->
      <section class="panel thermometer-panel">
        <h3 class="chart-title"><i class="bi bi-thermometer-half"></i> Temperature</h3>
        <div class="thermometer-container">
          <div class="thermometer-scale">
            <span>100°C</span><span>50°C</span><span>0°C</span>
          </div>
          <div class="thermometer-tube">
            <div class="thermometer-fill" :style="{ height: temperaturePercent + '%' }"></div>
          </div>
          <div class="thermometer-bulb"></div>
        </div>
        <div class="temp-display">{{ currentReadings.temperature.toFixed(1) }}°C</div>
      </section>

      <!-- Temperature & Humidity Chart -->
      <section class="panel chart-panel expandable-panel" @click="openChart('tempHum')">
        <h3 class="chart-title">
          <i class="bi bi-graph-up"></i> Temperature &amp; Humidity
          <span class="expand-hint"><i class="bi bi-arrows-fullscreen"></i> click to expand</span>
        </h3>
        <div class="chart-wrap">
          <svg :viewBox="`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`">
            <!-- Grid -->
            <g class="chart-grid-lines">
              <line v-for="i in 8" :key="`grid-h-${i}`"
                :x1="PADDING.left" :y1="PADDING.top + (INNER_HEIGHT / 8) * i"
                :x2="PADDING.left + INNER_WIDTH" :y2="PADDING.top + (INNER_HEIGHT / 8) * i"
                stroke="currentColor" stroke-width="1"/>
            </g>
            <!-- Axes -->
            <line :x1="PADDING.left" :y1="PADDING.top" :x2="PADDING.left" :y2="PADDING.top + INNER_HEIGHT" stroke="#64748b" stroke-width="2"/>
            <line :x1="PADDING.left + INNER_WIDTH" :y1="PADDING.top" :x2="PADDING.left + INNER_WIDTH" :y2="PADDING.top + INNER_HEIGHT" stroke="#64748b" stroke-width="2"/>
            <line :x1="PADDING.left" :y1="PADDING.top + INNER_HEIGHT" :x2="PADDING.left + INNER_WIDTH" :y2="PADDING.top + INNER_HEIGHT" stroke="#64748b" stroke-width="2"/>
            <!-- Y temp -->
            <text v-for="(l,i) in temperatureYLabels" :key="`ty-${i}`"
              :x="PADDING.left - 10" :y="l.y"
              text-anchor="end" dominant-baseline="middle" fill="#ff9b3d" font-size="10" font-weight="600">{{ l.text }}</text>
            <!-- Y hum -->
            <text v-for="(l,i) in humidityYLabels" :key="`hy-${i}`"
              :x="PADDING.left + INNER_WIDTH + 10" :y="l.y"
              text-anchor="start" dominant-baseline="middle" fill="#3d9fff" font-size="10" font-weight="600">{{ l.text }}</text>
            <!-- X time -->
            <text v-for="(l,i) in getTimeLabels" :key="`tx-${i}`"
              :x="l.x" :y="PADDING.top + INNER_HEIGHT + 26"
              text-anchor="end" fill="#cbd5e1" font-size="9" font-weight="600"
              :transform="`rotate(-28, ${l.x}, ${PADDING.top + INNER_HEIGHT + 26})`">{{ l.text }}</text>
            <line v-if="hoveredPoint && ['temp','hum'].includes(hoveredPoint.type) && hoveredPoint.x" :x1="hoveredPoint.x" :y1="PADDING.top" :x2="hoveredPoint.x" :y2="PADDING.top + INNER_HEIGHT" stroke="#94a3b8" stroke-width="1" stroke-dasharray="4 4" opacity="0.55"/>
            <!-- Lines -->
            <polyline v-if="temperatureSeries.length" :points="temperatureLinePoints"
              fill="none" stroke="#ff9b3d" stroke-width="1.5"/>
            <polyline v-if="humiditySeries.length" :points="humidityLinePoints"
              fill="none" stroke="#3d9fff" stroke-width="1.5"/>
            <!-- Points -->
            <circle v-for="p in temperatureSeries" :key="`tp-${p.i}`"
              :cx="p.x" :cy="p.y" r="3" fill="#ff9b3d" class="chart-point"
              @mouseover.stop="handleMouseOver('temp', p.v, p.t, false, { x: p.x, y: p.y })"
              @mouseout.stop="handleMouseOut">
              <title>{{ p.v?.toFixed(2) }}°C</title>
            </circle>
            <circle v-for="p in humiditySeries" :key="`hp-${p.i}`"
              :cx="p.x" :cy="p.y" r="3" fill="#3d9fff" class="chart-point"
              @mouseover.stop="handleMouseOver('hum', p.v, p.t, false, { x: p.x, y: p.y })"
              @mouseout.stop="handleMouseOut">
              <title>{{ p.v?.toFixed(2) }}%</title>
            </circle>
            <!-- Axis text -->
            <text :x="PADDING.left - 78" :y="PADDING.top + INNER_HEIGHT / 2"
              text-anchor="middle" fill="#ff9b3d" font-size="11" font-weight="700"
              :transform="`rotate(-90, ${PADDING.left - 78}, ${PADDING.top + INNER_HEIGHT / 2})`">Temperature (°C)</text>
            <text :x="PADDING.left + INNER_WIDTH + 78" :y="PADDING.top + INNER_HEIGHT / 2"
              text-anchor="middle" fill="#3d9fff" font-size="11" font-weight="700"
              :transform="`rotate(90, ${PADDING.left + INNER_WIDTH + 78}, ${PADDING.top + INNER_HEIGHT / 2})`">Humidity (%)</text>
            <text :x="PADDING.left + INNER_WIDTH / 2" :y="PADDING.top + INNER_HEIGHT + 40"
              text-anchor="middle" fill="#cbd5e1" font-size="11" font-weight="700">Time</text>
          </svg>
          <div v-if="hoveredPoint && ['temp','hum'].includes(hoveredPoint.type)" class="tooltip" :class="`tooltip-${hoveredPoint.type}`">
            {{ hoveredPoint.v?.toFixed(2) }}{{ hoveredPoint.type === 'temp' ? '°C' : '%' }}
            <div class="tooltip-sub">{{ formatTimestamp(hoveredPoint.t) }}</div>
          </div>
        </div>
        <div class="legend">
          <span class="legend-item"><span class="legend-dot temp"></span> Temperature</span>
          <span class="legend-item"><span class="legend-dot hum"></span> Humidity</span>
        </div>
      </section>

      <!-- Humidity Gauge -->
      <section class="panel gauge-panel-humidity">
        <h3 class="chart-title"><i class="bi bi-droplet-half"></i> Humidity</h3>
        <div class="gauge-container">
          <svg class="gauge-svg" width="160" height="160" viewBox="0 0 160 160">
            <circle cx="80" cy="80" r="70" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="12"/>
            <circle cx="80" cy="80" r="70" fill="none"
              :stroke="humidityGauge.color" stroke-width="12"
              :stroke-dasharray="GAUGE_CIRCUMFERENCE"
              :stroke-dashoffset="humidityGauge.offset"
              stroke-linecap="round" class="gauge-fill"/>
          </svg>
          <div class="gauge-value">{{ currentReadings.humidity.toFixed(0) }}%</div>
        </div>
      </section>

      <!-- Sound Level Chart -->
      <section class="panel chart-panel-wide expandable-panel" @click="openChart('noise')">
        <h3 class="chart-title">
          <i class="bi bi-soundwave"></i> Sound Level
          <span class="expand-hint"><i class="bi bi-arrows-fullscreen"></i> click to expand</span>
        </h3>
        <div class="chart-wrap-noise">
          <svg :viewBox="`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`">
            <!-- Grid -->
            <g class="chart-grid-lines">
              <line v-for="i in 8" :key="`ng-${i}`"
                :x1="PADDING.left" :y1="PADDING.top + (INNER_HEIGHT / 8) * i"
                :x2="PADDING.left + INNER_WIDTH" :y2="PADDING.top + (INNER_HEIGHT / 8) * i"
                stroke="currentColor" stroke-width="1"/>
            </g>
            <!-- Axes -->
            <line :x1="PADDING.left" :y1="PADDING.top" :x2="PADDING.left" :y2="PADDING.top + INNER_HEIGHT" stroke="#64748b" stroke-width="2"/>
            <line :x1="PADDING.left" :y1="PADDING.top + INNER_HEIGHT" :x2="PADDING.left + INNER_WIDTH" :y2="PADDING.top + INNER_HEIGHT" stroke="#64748b" stroke-width="2"/>
            <!-- Y labels -->
            <text v-for="(l,i) in noiseYLabels" :key="`ny-${i}`"
              :x="PADDING.left - 10" :y="l.y"
              text-anchor="end" dominant-baseline="middle" fill="#22c55e" font-size="10" font-weight="600">{{ l.text }}</text>
            <!-- X labels -->
            <text v-for="(l,i) in getTimeLabels" :key="`nt-${i}`"
              :x="l.x" :y="PADDING.top + INNER_HEIGHT + 26"
              text-anchor="end" fill="#cbd5e1" font-size="9" font-weight="600"
              :transform="`rotate(-28, ${l.x}, ${PADDING.top + INNER_HEIGHT + 26})`">{{ l.text }}</text>
            <line v-if="hoveredPoint?.type === 'noise' && hoveredPoint.x" :x1="hoveredPoint.x" :y1="PADDING.top" :x2="hoveredPoint.x" :y2="PADDING.top + INNER_HEIGHT" stroke="#94a3b8" stroke-width="1" stroke-dasharray="4 4" opacity="0.55"/>
            <!-- Bars -->
            <rect v-for="b in noiseBars" :key="`nb-${b.i}`"
              :x="b.x" :y="b.y" :width="b.w" :height="b.h" rx="1"
              :fill="`hsl(${120 - ((b.v - noiseRange.lo) / ((noiseRange.hi - noiseRange.lo) || 1)) * 60}, 70%, 50%)`"
              class="noise-bar"
              @mouseover.stop="handleMouseOver('noise', b.v, b.t, false, { x: b.x + b.w / 2, y: b.y })"
              @mouseout.stop="handleMouseOut">
              <title>{{ b.v?.toFixed(2) }} dB</title>
            </rect>
            <!-- Axis text -->
            <text :x="PADDING.left - 78" :y="PADDING.top + INNER_HEIGHT / 2"
              text-anchor="middle" fill="#22c55e" font-size="11" font-weight="700"
              :transform="`rotate(-90, ${PADDING.left - 78}, ${PADDING.top + INNER_HEIGHT / 2})`">Sound Level (dB)</text>
            <text :x="PADDING.left + INNER_WIDTH / 2" :y="PADDING.top + INNER_HEIGHT + 40"
              text-anchor="middle" fill="#cbd5e1" font-size="11" font-weight="700">Time</text>
          </svg>
          <div v-if="hoveredPoint?.type === 'noise'" class="tooltip tooltip-noise">
            {{ hoveredPoint.v?.toFixed(2) }} dB
            <div class="tooltip-sub">{{ formatTimestamp(hoveredPoint.t) }}</div>
          </div>
        </div>
      </section>

      <!-- Tilt -->
      <section class="panel svg-panel">
        <h3 class="chart-title"><i class="bi bi-phone-landscape"></i> Tilt</h3>
        <div class="svg-display">
          <div class="tilt-viz">
            <div class="tilt-label">{{ currentReadings.tilt.toFixed(1) }}°</div>
            <div class="tilt-indicator" :style="{ transform: `rotate(${currentReadings.tilt}deg)` }"></div>
            <div class="tilt-device" :style="{ transform: `translateX(-50%) rotate(${currentReadings.tilt}deg)` }">S6000</div>
            <div class="tilt-surface"></div>
          </div>
        </div>
      </section>

      <!-- Distance -->
      <section class="panel svg-panel">
        <h3 class="chart-title"><i class="bi bi-rulers"></i> Distance</h3>
        <div class="svg-display">
          <div class="distance-viz">
            <div class="s6000-box" :style="{ left: `${s6000Position}px` }">S6000</div>
            <div class="obstacle"></div>
            <div class="distance-line" :style="{ left: `${s6000Position + 70}px`, width: `${220 - s6000Position}px` }"></div>
            <div class="distance-label">{{ currentReadings.distance.toFixed(0) }}cm</div>
          </div>
        </div>
      </section>

      <!-- Pressure Gauge -->
      <section class="panel gauge-panel">
        <h3 class="chart-title"><i class="bi bi-speedometer2"></i> Pressure</h3>
        <div class="gauge-container">
          <svg class="gauge-svg" width="160" height="160" viewBox="0 0 160 160">
            <circle cx="80" cy="80" r="70" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="12"/>
            <circle cx="80" cy="80" r="70" fill="none"
              :stroke="pressureGauge.color" stroke-width="12"
              :stroke-dasharray="GAUGE_CIRCUMFERENCE"
              :stroke-dashoffset="pressureGauge.offset"
              stroke-linecap="round" class="gauge-fill"/>
          </svg>
          <div class="gauge-value" style="font-size:20px">
            {{ (currentReadings.pressure / 1000).toFixed(3) }}
            <span style="font-size:12px;color:var(--muted)"> kPa</span>
          </div>
        </div>
      </section>

      <!-- GPS Map -->
      <section class="panel map-panel">
        <h3 class="chart-title"><i class="bi bi-geo-alt"></i> GPS Location</h3>
        <div class="map-container">
          <div ref="mapContainer" class="leaflet-map"></div>
          <div class="map-coords">
            {{ currentReadings.gps.latitude.toFixed(6) }}°N,
            {{ currentReadings.gps.longitude.toFixed(6) }}°E
          </div>
        </div>
      </section>

      <!-- Prediction Time Distribution -->
      <section class="panel prediction-panel">
        <h3 class="chart-title">
          <i class="bi bi-activity"></i> Prediction-Time Trend
          <span class="chart-meta">avg {{ fmt(avgPredictionTime) }} ms · {{ predictionTimeSeries.length }} points</span>
        </h3>
        <div class="chart-wrap-inline">
          <svg :viewBox="`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`">
            <g class="chart-grid-lines">
              <line v-for="i in 8" :key="`pg-${i}`"
                :x1="PADDING.left" :y1="PADDING.top + (INNER_HEIGHT / 8) * i"
                :x2="PADDING.left + INNER_WIDTH" :y2="PADDING.top + (INNER_HEIGHT / 8) * i"
                stroke="currentColor" stroke-width="1"/>
            </g>
            <line :x1="PADDING.left" :y1="PADDING.top" :x2="PADDING.left" :y2="PADDING.top + INNER_HEIGHT" stroke="#64748b" stroke-width="2"/>
            <line :x1="PADDING.left" :y1="PADDING.top + INNER_HEIGHT" :x2="PADDING.left + INNER_WIDTH" :y2="PADDING.top + INNER_HEIGHT" stroke="#64748b" stroke-width="2"/>
            <text v-for="(l,i) in predictionTimeYLabels" :key="`py-${i}`"
              :x="PADDING.left - 10" :y="l.y"
              text-anchor="end" dominant-baseline="middle" fill="#a78bfa" font-size="10" font-weight="600">{{ l.text }}</text>
            <text v-for="(l,i) in getTimeLabels" :key="`px-${i}`"
              :x="l.x" :y="PADDING.top + INNER_HEIGHT + 26"
              text-anchor="end" fill="#cbd5e1" font-size="9" font-weight="600"
              :transform="`rotate(-28, ${l.x}, ${PADDING.top + INNER_HEIGHT + 26})`">{{ l.text }}</text>
            <line v-if="hoveredPoint?.type === 'prediction' && hoveredPoint.x" :x1="hoveredPoint.x" :y1="PADDING.top" :x2="hoveredPoint.x" :y2="PADDING.top + INNER_HEIGHT" stroke="#94a3b8" stroke-width="1" stroke-dasharray="4 4" opacity="0.55"/>
            <polyline v-if="predictionTimeSeries.length" :points="predictionTimeLinePoints"
              fill="none" stroke="#a78bfa" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <circle v-for="p in predictionTimeSeries" :key="`pred-${p.i}`"
              :cx="p.x" :cy="p.y" r="3.5"
              fill="#a78bfa" class="chart-point prediction-point"
              @mouseover.stop="handleMouseOver('prediction', p.v, p.t, false, { x: p.x, y: p.y })"
              @mouseout.stop="handleMouseOut">
              <title>{{ p.v?.toFixed(2) }} ms @ {{ formatTimestamp(p.t) }}</title>
            </circle>
            <text :x="PADDING.left - 78" :y="PADDING.top + INNER_HEIGHT / 2"
              text-anchor="middle" fill="#a78bfa" font-size="11" font-weight="700"
              :transform="`rotate(-90, ${PADDING.left - 78}, ${PADDING.top + INNER_HEIGHT / 2})`">Prediction Time (ms)</text>
            <text :x="PADDING.left + INNER_WIDTH / 2" :y="PADDING.top + INNER_HEIGHT + 40"
              text-anchor="middle" fill="#cbd5e1" font-size="11" font-weight="700">Time</text>
          </svg>
          <div v-if="hoveredPoint?.type === 'prediction'" class="tooltip tooltip-prediction">
            {{ hoveredPoint.v?.toFixed(2) }} ms
            <div class="tooltip-sub">{{ formatTimestamp(hoveredPoint.t) }}</div>
          </div>
          <div v-if="!predictionTimeSeries.length" class="empty-chart">
            No prediction-time values are available for this device and range.
          </div>
        </div>
      </section>
    </div>

    <!-- Stats Footer -->
    <footer v-if="!deviceNotFound" class="stats-grid">
      <div class="stat stat-temp">
        <div class="stat-label"><i class="bi bi-thermometer-half"></i> Temperature</div>
        <div class="stat-value">{{ avgTemperature.toFixed(1) }}°C</div>
        <div class="stat-sub">Min: {{ minTemperature.toFixed(1) }}°C · Max: {{ maxTemperature.toFixed(1) }}°C</div>
      </div>
      <div class="stat stat-hum">
        <div class="stat-label"><i class="bi bi-droplet-half"></i> Humidity</div>
        <div class="stat-value">{{ avgHumidity.toFixed(1) }}%</div>
        <div class="stat-sub">Min: {{ minHumidity.toFixed(1) }}% · Max: {{ maxHumidity.toFixed(1) }}%</div>
      </div>
      <div class="stat stat-pres">
        <div class="stat-label"><i class="bi bi-speedometer2"></i> Pressure</div>
        <div class="stat-value">{{ (avgPressure / 1000).toFixed(3) }} kPa</div>
        <div class="stat-sub">Average over {{ timeRange }}</div>
      </div>
      <div class="stat stat-count">
        <div class="stat-label"><i class="bi bi-graph-up"></i> Data Points</div>
        <div class="stat-value">{{ sensorData.length }}</div>
        <div class="stat-sub">Range: {{ timeRange }} · Device: {{ selectedDevice }}</div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.dashboard {
  --bg: #0b0f14;
  --panel: #111827;
  --panel-2: #0b1118;
  --panel-border: #1f2937;
  --text: #e5e7eb;
  --muted: #94a3b8;
  --accent: #60a5fa;
  --accent-2: #22c55e;
  background:
    radial-gradient(1200px 600px at 20% -10%, rgba(29, 78, 216, 0.15), transparent 60%),
    radial-gradient(900px 500px at 90% 10%, rgba(14, 165, 233, 0.12), transparent 55%),
    var(--bg);
  min-height: 100vh;
  padding: 20px;
  font-family: "Space Grotesk", "IBM Plex Sans", "Segoe UI", sans-serif;
  color: var(--text);
}

/* ============ MODAL ============ */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(6px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.modal-panel {
  background: #111827;
  border: 1px solid #1f2937;
  border-radius: 10px;
  width: 100%;
  max-width: 1160px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 32px 80px rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #1f2937;
  flex-shrink: 0;
}

.modal-title {
  margin: 0;
  font-size: 14px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
}

.close-btn {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid #1f2937;
  color: var(--muted);
  width: 32px;
  height: 32px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: background 0.2s, color 0.2s;
}
.close-btn:hover { background: rgba(255,255,255,0.12); color: var(--text); }

.modal-chart-wrap {
  padding: 16px 20px;
  background: #0b1118;
  flex: 1;
}

.modal-footer {
  padding: 12px 20px;
  border-top: 1px solid #1f2937;
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  font-size: 12px;
}

/* Transition */
.modal-enter-active, .modal-leave-active { transition: opacity 0.22s ease, transform 0.22s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; transform: scale(0.97); }

/* ============ EXPAND HINT ============ */
.expandable-panel {
  cursor: pointer;
  transition: border-color 0.2s;
}
.expandable-panel:hover { border-color: #374151; }

.expand-hint {
  margin-left: auto;
  font-size: 10px;
  font-weight: 600;
  color: #4b5563;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: color 0.2s;
}
.expandable-panel:hover .expand-hint { color: var(--accent); }

/* ============ HEADER ============ */
.header {
  background: rgba(17, 24, 39, 0.8);
  padding: 16px 18px;
  border-radius: 6px;
  margin-bottom: 16px;
  border: 1px solid var(--panel-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  backdrop-filter: blur(8px);
}

.header-left { display: flex; flex-direction: column; gap: 4px; }

.header-title {
  color: var(--text);
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.3px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-subtitle { color: var(--muted); margin: 0; font-size: 12px; }

.header-right { display: flex; align-items: center; gap: 8px; }

.header-pill {
  background: #0f172a;
  border: 1px solid var(--panel-border);
  color: var(--muted);
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  transition: all 0.3s ease;
}

.device-pill { border-color: var(--accent); color: var(--accent); background: rgba(96, 165, 250, 0.1); }
.pill-active { border-color: var(--accent-2); color: var(--accent-2); }

/* ============ PANELS ============ */
.panel {
  background: var(--panel);
  padding: 16px;
  border-radius: 6px;
  border: 1px solid var(--panel-border);
  box-shadow: 0 10px 24px rgba(0,0,0,0.2);
  margin-bottom: 16px;
  transition: box-shadow 0.3s ease, border-color 0.2s;
}
.panel:hover { box-shadow: 0 14px 32px rgba(0,0,0,0.3); }

.controls-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.help { margin-top: 8px; color: #94a3b8; font-size: 11px; line-height: 1.4; }
.help strong { color: #cbd5e0; font-weight: 700; }

.device-not-found {
  margin-top: 12px;
  padding: 24px;
  background: rgba(127, 29, 29, 0.3);
  border: 2px solid #dc2626;
  border-radius: 8px;
  color: #fecaca;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  font-size: 14px;
  animation: slideDown 0.3s ease-out;
}
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
.device-not-found i { font-size: 40px; color: #ef4444; flex-shrink: 0; animation: pulse 2s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
.device-not-found h3 { margin: 0 0 12px 0; color: #fca5a5; font-size: 20px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; }
.device-not-found p { margin: 6px 0; line-height: 1.6; font-size: 14px; }
.device-not-found strong { color: white; font-weight: 800; background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 3px; }

.label { color: var(--muted); font-weight: 700; display: flex; align-items: center; gap: 6px; margin-bottom: 6px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.4px; }

.input {
  width: 100%;
  padding: 8px 10px;
  background: #0f172a;
  color: var(--text);
  border: 1px solid var(--panel-border);
  border-radius: 4px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s ease;
}
.input:focus { border-color: var(--accent); }

.load-wrap { display: flex; flex-direction: column; justify-content: flex-end; }

.btn {
  padding: 8px 14px;
  border: 1px solid var(--panel-border);
  border-radius: 4px;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.15s ease;
  text-transform: uppercase;
  font-size: 12px;
  letter-spacing: 0.4px;
  background: #0f172a;
  color: var(--text);
}
.btn:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-primary { background: #0f172a; color: var(--text); border-color: var(--accent); }
.btn-primary:hover:not(:disabled) {
  background: #0b1220;
  box-shadow: 0 0 14px rgba(96, 165, 250, 0.25);
  transform: translateY(-1px);
}

.error {
  margin-top: 12px;
  padding: 10px 12px;
  background: #3f1d22;
  border: 1px solid #7f1d1d;
  border-radius: 6px;
  color: #fecaca;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

/* ============ GRID ============ */
.main-grid {
  display: grid;
  grid-template-columns: repeat(24, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.thermometer-panel { grid-column: span 2; display: flex; flex-direction: column; align-items: center; }
.chart-panel { grid-column: span 18; }
.gauge-panel { grid-column: span 8; display: flex; flex-direction: column; align-items: center; }
.gauge-panel-humidity { grid-column: span 4; display: flex; flex-direction: column; align-items: center; }
.chart-panel-wide { grid-column: span 24; }
.svg-panel { grid-column: span 8; }
.map-panel { grid-column: span 24; }
.prediction-panel { grid-column: span 24; }

.chart-title {
  color: var(--text);
  margin: 0 0 12px 0;
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.chart-meta {
  margin-left: auto;
  color: #a78bfa;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

/* ============ THERMOMETER ============ */
.thermometer-container { position: relative; width: 60px; height: 180px; margin: 10px 0; }
.thermometer-scale { position: absolute; left: -40px; top: 0; height: 140px; display: flex; flex-direction: column; justify-content: space-between; font-size: 10px; color: var(--muted); }
.thermometer-tube { width: 18px; height: 140px; background: rgba(255,255,255,0.05); border: 2px solid var(--panel-border); border-radius: 10px; position: relative; overflow: hidden; margin: 0 auto; }
.thermometer-fill { position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(to top, #ef4444, #ff9b3d); transition: height 1s cubic-bezier(0.4,0,0.2,1); border-radius: 0 0 8px 8px; }
.thermometer-bulb { width: 26px; height: 26px; background: radial-gradient(circle, #ef4444, #cc0000); border-radius: 50%; margin: 8px auto 0; border: 2px solid var(--panel-border); position: relative; }
.thermometer-bulb::after { content: ''; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 10px; height: 10px; background: rgba(255,255,255,0.3); border-radius: 50%; }
.temp-display { font-size: 18px; font-weight: 700; color: #ff9b3d; margin-top: 10px; text-align: center; }

/* ============ CHARTS ============ */
.chart-wrap {
  height: 300px;
  background: var(--panel-2);
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}
.chart-wrap-noise {
  height: 300px;
  background: var(--panel-2);
  border: 0.5px solid var(--panel-border);
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}
.chart-wrap-inline {
  height: 300px;
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.72), rgba(11, 17, 24, 0.98)),
    var(--panel-2);
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}
.chart-wrap svg,
.chart-wrap-noise svg,
.chart-wrap-inline svg,
.modal-chart-wrap svg {
  width: 100%;
  height: 100%;
}
.chart-grid-lines {
  color: rgba(148, 163, 184, 0.34);
}

.chart-point {
  opacity: 0.68;
  cursor: pointer;
  transition: opacity 0.2s, r 0.15s, filter 0.2s;
  filter: drop-shadow(0 0 4px rgba(255,255,255,0.12));
}
.chart-point:hover { opacity: 1; r: 5; filter: drop-shadow(0 0 8px currentColor); }

.noise-bar {
  opacity: 0.86;
  cursor: pointer;
  transition: opacity 0.2s, filter 0.2s, transform 0.2s;
  transform-box: fill-box;
  transform-origin: center bottom;
}
.noise-bar:hover {
  opacity: 1;
  filter: drop-shadow(0 0 8px rgba(96, 165, 250, 0.38));
  transform: scaleY(1.04);
}
.prediction-point {
  filter: drop-shadow(0 0 7px rgba(167, 139, 250, 0.45));
}

.tooltip {
  position: absolute;
  bottom: 12px;
  left: 12px;
  background: rgba(10, 15, 20, 0.95);
  padding: 8px 12px;
  border-radius: 6px;
  font-weight: 800;
  border: 1px solid var(--panel-border);
  font-size: 14px;
  pointer-events: none;
  z-index: 10;
}
.tooltip-sub { font-size: 10px; opacity: 0.8; margin-top: 4px; font-weight: 600; }
.tooltip-temp { color: #ff9b3d; border-color: rgba(255,155,61,0.7); }
.tooltip-hum { color: #3d9fff; border-color: rgba(61,159,255,0.7); }
.tooltip-noise { color: #22c55e; border-color: rgba(34,197,94,0.7); }
.tooltip-prediction { color: #a78bfa; border-color: rgba(167,139,250,0.7); }
.empty-chart {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-align: center;
  padding: 16px;
}

.legend { display: flex; gap: 16px; justify-content: center; margin-top: 10px; font-size: 11px; }
.legend-item { display: flex; align-items: center; gap: 6px; color: var(--muted); }
.legend-item.muted { color: #4b5563; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; }
.legend-dot.temp { background: #ff9b3d; }
.legend-dot.hum { background: #3d9fff; }
.legend-dot.noise { background: #22c55e; }

/* ============ GAUGES ============ */
.gauge-container { width: 160px; height: 160px; position: relative; margin: 10px 0; }
.gauge-svg { transform: rotate(-90deg); }
.gauge-fill { transition: stroke-dashoffset 1s cubic-bezier(0.4,0,0.2,1), stroke 0.3s ease; }
.gauge-value { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 32px; font-weight: 700; color: var(--text); }

/* ============ TILT ============ */
.svg-display { width: 100%; height: 200px; display: flex; align-items: center; justify-content: center; }
.tilt-viz { width: 100%; max-width: 240px; height: 180px; position: relative; }
.tilt-surface { position: absolute; bottom: 30px; left: 50%; transform: translateX(-50%); width: 180px; height: 3px; background: repeating-linear-gradient(90deg, #4a5568, #4a5568 10px, transparent 10px, transparent 20px); }
.tilt-device { position: absolute; bottom: 36px; left: 50%; width: 50px; height: 16px; background: #4d4d4d; border: 1px solid var(--panel-border); border-radius: 2px; transform-origin: center bottom; transition: transform 1s cubic-bezier(0.4,0,0.2,1); display: flex; align-items: center; justify-content: center; font-size: 9px; color: white; font-weight: 700; }
.tilt-indicator { position: absolute; bottom: 52px; left: 50%; width: 2px; height: 80px; background: linear-gradient(to top, #ef4444, transparent); transform-origin: center bottom; transition: transform 1s cubic-bezier(0.4,0,0.2,1); }
.tilt-label { position: absolute; top: 10px; left: 50%; transform: translateX(-50%); font-size: 16px; color: #ef4444; font-weight: 700; }

/* ============ DISTANCE ============ */
.distance-viz { width: 100%; max-width: 260px; height: 180px; position: relative; }
.s6000-box { position: absolute; top: 50%; transform: translateY(-50%); background: #4d4d4d; padding: 6px 14px; border-radius: 4px; font-size: 12px; color: white; font-weight: 700; transition: left 1s cubic-bezier(0.4,0,0.2,1); }
.obstacle { position: absolute; right: 20px; top: 50%; transform: translateY(-50%); width: 30px; height: 100px; background: repeating-linear-gradient(45deg, #4a5568, #4a5568 8px, #374151 8px, #374151 16px); border: 2px solid var(--panel-border); }
.distance-line { position: absolute; top: 50%; height: 2px; background: rgba(239,68,68,0.4); border-top: 2px dashed #ef4444; transition: left 1s cubic-bezier(0.4,0,0.2,1), width 1s cubic-bezier(0.4,0,0.2,1); }
.distance-label { position: absolute; top: 35%; left: 50%; transform: translateX(-50%); font-size: 14px; color: #ef4444; font-weight: 700; }

/* ============ MAP ============ */
.map-container { width: 100%; height: 400px; background: var(--panel-2); border-radius: 6px; border: 1px solid var(--panel-border); position: relative; overflow: hidden; }
.leaflet-map { width: 100%; height: 100%; border-radius: 6px; }
.map-coords { position: absolute; bottom: 12px; left: 12px; font-size: 11px; color: var(--text); background: rgba(17,24,39,0.95); padding: 8px 12px; border-radius: 4px; font-weight: 700; backdrop-filter: blur(8px); border: 1px solid var(--panel-border); z-index: 1000; }

/* ============ STATS ============ */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; }
.stat { padding: 14px; border-radius: 6px; color: var(--text); background: var(--panel); border: 1px solid var(--panel-border); box-shadow: 0 8px 18px rgba(0,0,0,0.2); transition: transform 0.2s ease, box-shadow 0.2s ease; }
.stat:hover { transform: translateY(-2px); box-shadow: 0 12px 24px rgba(0,0,0,0.3); }
.stat-temp { border-left: 3px solid #ef4444; }
.stat-hum { border-left: 3px solid #3b82f6; }
.stat-pres { border-left: 3px solid #10b981; }
.stat-count { border-left: 3px solid #8b5cf6; }
.stat-label { font-size: 11px; opacity: 0.85; margin-bottom: 6px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; display: flex; align-items: center; gap: 6px; }
.stat-value { font-size: 26px; font-weight: 900; margin-bottom: 6px; }
.stat-sub { font-size: 11px; opacity: 0.75; }

/* ============ RESPONSIVE ============ */
@media (max-width: 1400px) {
  .chart-panel { grid-column: span 24; }
  .thermometer-panel, .gauge-panel { grid-column: span 8; }
}
@media (max-width: 768px) {
  .main-grid > * { grid-column: span 24 !important; }
  .header { flex-direction: column; align-items: flex-start; }
  .header-right { width: 100%; justify-content: space-between; }
}
@media (max-width: 480px) {
  .controls-grid { grid-template-columns: 1fr; }
  .stats-grid { grid-template-columns: 1fr; }
}
</style>
