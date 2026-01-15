<!-- ChartPage.vue - Complete Grafana-like Dashboard (final, cleaned + working) -->
<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

/* -----------------------
 * State
 * --------------------- */
const selectedDevice = ref('101')
const timeRange = ref('6h')
const bucketMinutes = ref(5)
const refreshSeconds = ref(30)
const selectedVisualization = ref('line')

const chartData = ref([]) // [{ t, temperature, humidity, pressure }]
const availableDevices = ref([])
const loading = ref(false)
const error = ref('')

const zoomLevel = ref(1)
const panX = ref(0)
const panY = ref(0)
const hoveredPoint = ref(null)

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

/* -----------------------
 * Chart constants
 * --------------------- */
const svgWidth = 800
const svgHeight = 350

const PADDING = { left: 50, right: 30, top: 20, bottom: 30 }
const innerWidth = svgWidth - PADDING.left - PADDING.right
const innerHeight = svgHeight - PADDING.top - PADDING.bottom

let timer = null

const visualizationTypes = [
  { id: 'line', label: 'Line Chart', icon: 'bi-graph-up', number: '1' },
  { id: 'area', label: 'Area Chart', icon: 'bi-graph-up', number: '2' },
  { id: 'bar', label: 'Bar Chart', icon: 'bi-bar-chart', number: '3' },
  { id: 'scatter', label: 'Scatter Plot', icon: 'bi-scatter', number: '4' },
  { id: 'pie', label: 'Pie Chart', icon: 'bi-pie-chart', number: '5' }
]

/* -----------------------
 * Helpers
 * --------------------- */
function toNum(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function minutesForRange(range) {
  switch (range) {
    case '1h':
      return 60
    case '6h':
      return 360
    case '24h':
      return 1440
    case '7d':
      return 10080
    case '30d':
      return 43200
    default:
      return 360
  }
}

function formatTs(ts) {
  try {
    return new Date(ts).toLocaleString()
  } catch {
    return ''
  }
}

function xForIndex(i, len) {
  if (len <= 1) return PADDING.left + innerWidth / 2
  return PADDING.left + (innerWidth * i) / (len - 1)
}

function yForValue(v, min, max) {
  if (v == null) return null
  const range = max - min || 1
  const t = (v - min) / range // 0..1
  return PADDING.top + (1 - t) * innerHeight
}

function bucketize(rows) {
  const bm = bucketMinutes.value
  if (!bm || bm <= 0) return rows

  const bucketMs = bm * 60 * 1000
  const m = new Map()

  for (const r of rows) {
    const b = Math.floor(r.t / bucketMs) * bucketMs
    const cur =
      m.get(b) || {
        t: b,
        tempSum: 0,
        humSum: 0,
        presSum: 0,
        tempN: 0,
        humN: 0,
        presN: 0
      }

    if (r.temperature != null) {
      cur.tempSum += r.temperature
      cur.tempN++
    }
    if (r.humidity != null) {
      cur.humSum += r.humidity
      cur.humN++
    }
    if (r.pressure != null) {
      cur.presSum += r.pressure
      cur.presN++
    }
    m.set(b, cur)
  }

  return [...m.values()]
    .sort((a, b) => a.t - b.t)
    .map(b => ({
      t: b.t,
      temperature: b.tempN ? b.tempSum / b.tempN : null,
      humidity: b.humN ? b.humSum / b.humN : null,
      pressure: b.presN ? b.presSum / b.presN : null
    }))
}

/* -----------------------
 * Fetch + normalize
 * --------------------- */
async function loadChartData() {
  loading.value = true
  error.value = ''
  hoveredPoint.value = null
  resetView()

  try {
    const minutes = minutesForRange(timeRange.value)

    const url = new URL(`${API_BASE}/api/weather/forecast/`)
    url.searchParams.set('minutes', String(minutes))

    const res = await fetch(url.toString())
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    const data = await res.json()

    if (!Array.isArray(data)) throw new Error('Unexpected API response (expected array)')

    const uniqueDevices = [...new Set(data.map(d => String(d.device_id ?? 'unknown')))].sort()
    availableDevices.value = uniqueDevices

    const filtered = data.filter(d => String(d.device_id) === String(selectedDevice.value))

    const normalized = filtered
      .map(d => ({
        t: new Date(d.time).getTime(),
        temperature: toNum(d.temperature),
        humidity: toNum(d.humidity),
        pressure: toNum(d.pressure)
      }))
      .filter(d => Number.isFinite(d.t))
      .sort((a, b) => a.t - b.t)

    chartData.value = bucketize(normalized)
  } catch (e) {
    error.value = String(e?.message || e)
    chartData.value = []
    availableDevices.value = []
  } finally {
    loading.value = false
  }
}

/* -----------------------
 * Stats (computed)
 * --------------------- */
function avgOf(key) {
  const vals = chartData.value.map(d => d[key]).filter(v => v != null)
  if (!vals.length) return 0
  return vals.reduce((a, b) => a + b, 0) / vals.length
}

function minOf(key) {
  const vals = chartData.value.map(d => d[key]).filter(v => v != null)
  return vals.length ? Math.min(...vals) : 0
}

function maxOf(key) {
  const vals = chartData.value.map(d => d[key]).filter(v => v != null)
  return vals.length ? Math.max(...vals) : 0
}

const avgTemperature = computed(() => avgOf('temperature'))
const avgHumidity = computed(() => avgOf('humidity'))
const avgPressure = computed(() => avgOf('pressure'))

const minTemperature = computed(() => minOf('temperature'))
const maxTemperature = computed(() => maxOf('temperature'))
const minHumidity = computed(() => minOf('humidity'))
const maxHumidity = computed(() => maxOf('humidity'))
const minPressure = computed(() => minOf('pressure'))
const maxPressure = computed(() => maxOf('pressure'))

/* -----------------------
 * Series builders
 * --------------------- */
function buildSeries(key, minV, maxV) {
  const len = chartData.value.length
  const pts = []
  for (let i = 0; i < len; i++) {
    const row = chartData.value[i]
    const v = row?.[key] ?? null
    const x = xForIndex(i, len)
    const y = yForValue(v, minV, maxV)
    if (y != null) {
      pts.push({
        x,
        y,
        v,
        t: row.t,
        i
      })
    }
  }
  return pts
}

const temperatureSeries = computed(() => buildSeries('temperature', minTemperature.value, maxTemperature.value))
const humiditySeries = computed(() => buildSeries('humidity', minHumidity.value, maxHumidity.value))
const pressureSeries = computed(() => buildSeries('pressure', minPressure.value, maxPressure.value))

function polylinePoints(series) {
  return series.map(p => `${p.x},${p.y}`).join(' ')
}

function areaPath(series) {
  if (!series.length) return ''
  const first = series[0]
  const last = series[series.length - 1]
  const topLine = series.map(p => `${p.x},${p.y}`).join(' ')
  const baseY = PADDING.top + innerHeight
  return `M ${first.x},${baseY} L ${topLine} L ${last.x},${baseY} Z`
}

const temperatureLinePoints = computed(() => polylinePoints(temperatureSeries.value))
const humidityLinePoints = computed(() => polylinePoints(humiditySeries.value))
const pressureLinePoints = computed(() => polylinePoints(pressureSeries.value))

const temperatureAreaPath = computed(() => areaPath(temperatureSeries.value))
const humidityAreaPath = computed(() => areaPath(humiditySeries.value))
const pressureAreaPath = computed(() => areaPath(pressureSeries.value))

/* -----------------------
 * Bar helpers (SVG rects)
 * --------------------- */
function barRects(series, minV, maxV) {
  const len = chartData.value.length || 1
  const spacing = innerWidth / len
  const bw = Math.max(6, Math.min(22, spacing * 0.7))

  const baseY = PADDING.top + innerHeight
  const range = maxV - minV || 1

  return series.map(p => {
    const t = (p.v - minV) / range
    const h = Math.max(1, t * innerHeight)
    return {
      x: p.x - bw / 2,
      y: baseY - h,
      w: bw,
      h,
      v: p.v,
      t: p.t,
      i: p.i
    }
  })
}

const tempBars = computed(() => barRects(temperatureSeries.value, minTemperature.value, maxTemperature.value))
const humBars = computed(() => barRects(humiditySeries.value, minHumidity.value, maxHumidity.value))
const presBars = computed(() => barRects(pressureSeries.value, minPressure.value, maxPressure.value))

/* -----------------------
 * Pie segments (summary)
 * --------------------- */
const pieSegments = computed(() => {
  const temp = avgTemperature.value
  const hum = avgHumidity.value
  const pres = avgPressure.value / 100 // scale down so pie makes sense

  const total = temp + hum + pres
  if (!total) return []

  const data = [
    { label: 'Temperature', value: temp, color: '#ef4444' },
    { label: 'Humidity', value: hum, color: '#3b82f6' },
    { label: 'Pressure', value: pres, color: '#10b981' }
  ]

  const segments = []
  let startAngle = 0
  for (const item of data) {
    const pct = (item.value / total) * 100
    const angle = (pct / 100) * 360
    segments.push({
      ...item,
      percentage: pct.toFixed(1),
      startAngle,
      angle
    })
    startAngle += angle
  }
  return segments
})

function generatePiePath(startAngle, angle) {
  const radius = 80
  const centerX = 150
  const centerY = 120

  const startRad = ((startAngle - 90) * Math.PI) / 180
  const endRad = ((startAngle + angle - 90) * Math.PI) / 180

  const x1 = centerX + radius * Math.cos(startRad)
  const y1 = centerY + radius * Math.sin(startRad)

  const x2 = centerX + radius * Math.cos(endRad)
  const y2 = centerY + radius * Math.sin(endRad)

  const largeArc = angle > 180 ? 1 : 0

  return `M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`
}

/* -----------------------
 * Zoom + Pan
 * --------------------- */
const isPanning = ref(false)
let panStart = null

const svgTransformStyle = computed(() => ({
  width: '100%',
  height: '100%',
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${zoomLevel.value})`,
  transformOrigin: 'top left',
  transition: isPanning.value ? 'none' : 'transform 0.15s ease'
}))

function zoomIn() {
  zoomLevel.value = Math.min(zoomLevel.value + 0.2, 3)
}

function zoomOut() {
  zoomLevel.value = Math.max(zoomLevel.value - 0.2, 1)
}

function resetView() {
  zoomLevel.value = 1
  panX.value = 0
  panY.value = 0
}

function handleWheel(event) {
  event.preventDefault()
  if (event.deltaY < 0) zoomIn()
  else zoomOut()
}

function onPanMove(e) {
  if (!isPanning.value || !panStart) return
  panX.value = panStart.x + (e.clientX - panStart.startX)
  panY.value = panStart.y + (e.clientY - panStart.startY)
}

function endPan() {
  isPanning.value = false
  panStart = null
  window.removeEventListener('mousemove', onPanMove)
  window.removeEventListener('mouseup', endPan)
}

function startPan(e) {
  // Only left click
  if (e.button !== 0) return
  isPanning.value = true
  panStart = {
    startX: e.clientX,
    startY: e.clientY,
    x: panX.value,
    y: panY.value
  }
  window.addEventListener('mousemove', onPanMove)
  window.addEventListener('mouseup', endPan)
}

/* -----------------------
 * Timer
 * --------------------- */
function stopTimer() {
  if (timer) clearInterval(timer)
  timer = null
}

function startTimer() {
  stopTimer()
  if (!refreshSeconds.value || refreshSeconds.value <= 0) return
  timer = setInterval(loadChartData, refreshSeconds.value * 1000)
}

/* -----------------------
 * Watches / lifecycle
 * --------------------- */
watch(refreshSeconds, startTimer)
watch([selectedDevice, timeRange, bucketMinutes], () => loadChartData())

onMounted(() => {
  loadChartData()
  startTimer()
})

onBeforeUnmount(() => {
  stopTimer()
  endPan()
})
</script>

<template>
  <div class="dashboard">
    <!-- Header -->
    <div class="header">
      <div class="header-left">
        <h1 class="header-title">
          <i class="bi bi-graph-up"></i>
          S6000 Sensor Dashboard
        </h1>
        <p class="header-subtitle">Real-time monitoring and visualization of IoT sensors</p>
      </div>
      <div class="header-right">
        <span class="header-pill"><i class="bi bi-clock"></i> {{ timeRange }}</span>
        <span class="header-pill"><i class="bi bi-arrow-repeat"></i> {{ refreshSeconds ? `${refreshSeconds}s` : 'off' }}</span>
      </div>
    </div>

    <!-- Controls -->
    <div class="panel">
      <div class="controls-grid">
        <!-- Device -->
        <div>
          <label class="label"><i class="bi bi-hdd"></i> Device ID</label>
          <input
            v-model="selectedDevice"
            type="text"
            class="input"
            placeholder="Enter device ID (e.g., 101, 102)"
          />
          <div class="help">
            <strong>Available devices:</strong>
            {{ availableDevices.length ? availableDevices.join(', ') : (loading ? 'Loading…' : '—') }}
          </div>
        </div>

        <!-- Time Range -->
        <div>
          <label class="label"><i class="bi bi-calendar"></i> Time Range</label>
          <select v-model="timeRange" class="input">
            <option value="1h">Last 1 Hour</option>
            <option value="6h">Last 6 Hours</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
        </div>

        <!-- Aggregation -->
        <div>
          <label class="label"><i class="bi bi-clock"></i> Aggregation</label>
          <select v-model.number="bucketMinutes" class="input">
            <option :value="0">Raw Data</option>
            <option :value="1">1 Minute</option>
            <option :value="5">5 Minutes</option>
            <option :value="15">15 Minutes</option>
            <option :value="60">1 Hour</option>
          </select>
        </div>

        <!-- Auto Refresh -->
        <div>
          <label class="label"><i class="bi bi-arrow-repeat"></i> Auto Refresh</label>
          <select v-model.number="refreshSeconds" class="input">
            <option :value="0">Off</option>
            <option :value="10">Every 10s</option>
            <option :value="30">Every 30s</option>
            <option :value="60">Every 60s</option>
          </select>
        </div>

        <!-- Load -->
        <div class="load-wrap">
          <button class="btn btn-primary" @click="loadChartData" :disabled="loading">
            <i :class="loading ? 'bi bi-hourglass-split' : 'bi bi-arrow-clockwise'"></i>
            {{ loading ? 'Loading…' : 'Load Data' }}
          </button>
        </div>
      </div>

      <div v-if="error" class="error">
        <i class="bi bi-exclamation-triangle"></i>
        <span>{{ error }}</span>
      </div>
    </div>

    <!-- Stats -->
    <div v-if="chartData.length" class="stats-grid">
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
        <div class="stat-value">{{ avgPressure.toFixed(1) }} hPa</div>
        <div class="stat-sub">Min: {{ minPressure.toFixed(1) }} · Max: {{ maxPressure.toFixed(1) }}</div>
      </div>

      <div class="stat stat-count">
        <div class="stat-label"><i class="bi bi-graph-up"></i> Data Points</div>
        <div class="stat-value">{{ chartData.length }}</div>
        <div class="stat-sub">Range: {{ timeRange }} · Bucket: {{ bucketMinutes ? `${bucketMinutes}m` : 'raw' }}</div>
      </div>
    </div>

    <!-- Visualization selector -->
    <div class="panel viz-panel" v-if="chartData.length">
      <div class="viz-title">Select Visualization:</div>
      <button
        v-for="viz in visualizationTypes"
        :key="viz.id"
        class="viz-btn"
        :class="{ active: selectedVisualization === viz.id }"
        @click="selectedVisualization = viz.id"
      >
        <span class="viz-num">{{ viz.number }}</span>
        <i :class="`bi ${viz.icon}`"></i>
        {{ viz.label }}
      </button>
    </div>

    <!-- Pie (summary) -->
    <div v-if="chartData.length && selectedVisualization === 'pie'" class="panel chart-panel">
      <h3 class="chart-title"><i class="bi bi-pie-chart"></i> Summary (Avg Temperature / Humidity / Pressure)</h3>

      <div class="chart-wrap">
        <div class="pie-wrap">
          <svg viewBox="0 0 300 240" class="pie-svg">
            <circle cx="150" cy="120" r="80" fill="none" stroke="#2d3748" stroke-width="1" style="opacity: 0.35" />
            <path
              v-for="(seg, i) in pieSegments"
              :key="`pie-${i}`"
              :d="generatePiePath(seg.startAngle, seg.angle)"
              :fill="seg.color"
              class="pie-seg"
              @mouseover="hoveredPoint = { type: 'pie', label: seg.label, percentage: seg.percentage }"
              @mouseout="hoveredPoint = null"
            >
              <title>{{ seg.label }}: {{ seg.percentage }}%</title>
            </path>
          </svg>

          <div v-if="hoveredPoint?.type === 'pie'" class="pie-center">
            <div class="pie-label">{{ hoveredPoint.label }}</div>
            <div class="pie-pct">{{ hoveredPoint.percentage }}%</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div
      v-else-if="chartData.length"
      class="charts-grid"
    >
      <!-- Temperature -->
      <div class="panel chart-panel">
        <h3 class="chart-title"><i class="bi bi-thermometer-half"></i> Temperature Over Time</h3>

        <div class="chart-wrap" @wheel="handleWheel" @mousedown="startPan">
          <svg :viewBox="`0 0 ${svgWidth} ${svgHeight}`" :style="svgTransformStyle">
            <!-- Grid -->
            <g style="opacity: 0.12">
              <line v-for="i in 10" :key="`t-h-${i}`" :x1="0" :y1="(svgHeight / 10) * i" :x2="svgWidth" :y2="(svgHeight / 10) * i" stroke="white" stroke-width="1" />
              <line v-for="i in 15" :key="`t-v-${i}`" :x1="(svgWidth / 15) * i" :y1="0" :x2="(svgWidth / 15) * i" :y2="svgHeight" stroke="white" stroke-width="1" />
            </g>

            <!-- Axes -->
            <line :x1="PADDING.left" :y1="PADDING.top" :x2="PADDING.left" :y2="PADDING.top + innerHeight" stroke="#4a5568" stroke-width="2" />
            <line :x1="PADDING.left" :y1="PADDING.top + innerHeight" :x2="PADDING.left + innerWidth" :y2="PADDING.top + innerHeight" stroke="#4a5568" stroke-width="2" />

            <!-- Area -->
            <path
              v-if="selectedVisualization === 'area'"
              :d="temperatureAreaPath"
              fill="#ef4444"
              style="opacity: 0.18"
            />

            <!-- Line -->
            <polyline
              v-if="selectedVisualization === 'line' || selectedVisualization === 'area'"
              :points="temperatureLinePoints"
              fill="none"
              stroke="#ef4444"
              stroke-width="2.5"
              style="filter: drop-shadow(0 0 4px rgba(239, 68, 68, 0.6))"
            />

            <!-- Scatter -->
            <template v-if="selectedVisualization === 'scatter' || selectedVisualization === 'line' || selectedVisualization === 'area'">
              <circle
                v-for="p in temperatureSeries"
                :key="`t-pt-${p.i}`"
                :cx="p.x"
                :cy="p.y"
                :r="selectedVisualization === 'scatter' ? 6 : 4"
                fill="#ef4444"
                style="opacity: 0.65; cursor: pointer"
                @mouseover="hoveredPoint = { type: 'temp', v: p.v, t: p.t }"
                @mouseout="hoveredPoint = null"
              >
                <title>{{ p.v?.toFixed(2) }}°C · {{ formatTs(p.t) }}</title>
              </circle>
            </template>

            <!-- Bars -->
            <template v-if="selectedVisualization === 'bar'">
              <rect
                v-for="b in tempBars"
                :key="`t-bar-${b.i}`"
                :x="b.x"
                :y="b.y"
                :width="b.w"
                :height="b.h"
                rx="3"
                fill="#ef4444"
                style="opacity: 0.75; cursor: pointer"
                @mouseover="hoveredPoint = { type: 'temp', v: b.v, t: b.t }"
                @mouseout="hoveredPoint = null"
              >
                <title>{{ b.v?.toFixed(2) }}°C · {{ formatTs(b.t) }}</title>
              </rect>
            </template>
          </svg>

          <div v-if="hoveredPoint?.type === 'temp'" class="tooltip tooltip-temp">
            {{ hoveredPoint.v?.toFixed(2) }}°C
            <div class="tooltip-sub">{{ formatTs(hoveredPoint.t) }}</div>
          </div>
        </div>

        <div class="zoom-row">
          <button class="btn btn-primary btn-sm" @click="zoomIn"><i class="bi bi-zoom-in"></i> Zoom In</button>
          <button class="btn btn-primary btn-sm" @click="zoomOut"><i class="bi bi-zoom-out"></i> Zoom Out</button>
          <button class="btn btn-muted btn-sm" @click="resetView"><i class="bi bi-arrow-counterclockwise"></i> Reset</button>
          <span class="zoom-label">Zoom: {{ (zoomLevel * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <!-- Humidity -->
      <div class="panel chart-panel">
        <h3 class="chart-title"><i class="bi bi-droplet-half"></i> Humidity Over Time</h3>

        <div class="chart-wrap" @wheel="handleWheel" @mousedown="startPan">
          <svg :viewBox="`0 0 ${svgWidth} ${svgHeight}`" :style="svgTransformStyle">
            <g style="opacity: 0.12">
              <line v-for="i in 10" :key="`h-h-${i}`" :x1="0" :y1="(svgHeight / 10) * i" :x2="svgWidth" :y2="(svgHeight / 10) * i" stroke="white" stroke-width="1" />
              <line v-for="i in 15" :key="`h-v-${i}`" :x1="(svgWidth / 15) * i" :y1="0" :x2="(svgWidth / 15) * i" :y2="svgHeight" stroke="white" stroke-width="1" />
            </g>

            <line :x1="PADDING.left" :y1="PADDING.top" :x2="PADDING.left" :y2="PADDING.top + innerHeight" stroke="#4a5568" stroke-width="2" />
            <line :x1="PADDING.left" :y1="PADDING.top + innerHeight" :x2="PADDING.left + innerWidth" :y2="PADDING.top + innerHeight" stroke="#4a5568" stroke-width="2" />

            <path v-if="selectedVisualization === 'area'" :d="humidityAreaPath" fill="#3b82f6" style="opacity: 0.18" />

            <polyline
              v-if="selectedVisualization === 'line' || selectedVisualization === 'area'"
              :points="humidityLinePoints"
              fill="none"
              stroke="#3b82f6"
              stroke-width="2.5"
              style="filter: drop-shadow(0 0 4px rgba(59, 130, 246, 0.6))"
            />

            <template v-if="selectedVisualization === 'scatter' || selectedVisualization === 'line' || selectedVisualization === 'area'">
              <circle
                v-for="p in humiditySeries"
                :key="`h-pt-${p.i}`"
                :cx="p.x"
                :cy="p.y"
                :r="selectedVisualization === 'scatter' ? 6 : 4"
                fill="#3b82f6"
                style="opacity: 0.65; cursor: pointer"
                @mouseover="hoveredPoint = { type: 'hum', v: p.v, t: p.t }"
                @mouseout="hoveredPoint = null"
              >
                <title>{{ p.v?.toFixed(2) }}% · {{ formatTs(p.t) }}</title>
              </circle>
            </template>

            <template v-if="selectedVisualization === 'bar'">
              <rect
                v-for="b in humBars"
                :key="`h-bar-${b.i}`"
                :x="b.x"
                :y="b.y"
                :width="b.w"
                :height="b.h"
                rx="3"
                fill="#3b82f6"
                style="opacity: 0.75; cursor: pointer"
                @mouseover="hoveredPoint = { type: 'hum', v: b.v, t: b.t }"
                @mouseout="hoveredPoint = null"
              >
                <title>{{ b.v?.toFixed(2) }}% · {{ formatTs(b.t) }}</title>
              </rect>
            </template>
          </svg>

          <div v-if="hoveredPoint?.type === 'hum'" class="tooltip tooltip-hum">
            {{ hoveredPoint.v?.toFixed(2) }}%
            <div class="tooltip-sub">{{ formatTs(hoveredPoint.t) }}</div>
          </div>
        </div>

        <div class="zoom-row">
          <button class="btn btn-primary btn-sm" @click="zoomIn"><i class="bi bi-zoom-in"></i> Zoom In</button>
          <button class="btn btn-primary btn-sm" @click="zoomOut"><i class="bi bi-zoom-out"></i> Zoom Out</button>
          <button class="btn btn-muted btn-sm" @click="resetView"><i class="bi bi-arrow-counterclockwise"></i> Reset</button>
          <span class="zoom-label">Zoom: {{ (zoomLevel * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <!-- Pressure -->
      <div class="panel chart-panel chart-span">
        <h3 class="chart-title"><i class="bi bi-speedometer2"></i> Pressure Over Time</h3>

        <div class="chart-wrap" @wheel="handleWheel" @mousedown="startPan">
          <svg :viewBox="`0 0 ${svgWidth} ${svgHeight}`" :style="svgTransformStyle">
            <g style="opacity: 0.12">
              <line v-for="i in 10" :key="`p-h-${i}`" :x1="0" :y1="(svgHeight / 10) * i" :x2="svgWidth" :y2="(svgHeight / 10) * i" stroke="white" stroke-width="1" />
              <line v-for="i in 15" :key="`p-v-${i}`" :x1="(svgWidth / 15) * i" :y1="0" :x2="(svgWidth / 15) * i" :y2="svgHeight" stroke="white" stroke-width="1" />
            </g>

            <line :x1="PADDING.left" :y1="PADDING.top" :x2="PADDING.left" :y2="PADDING.top + innerHeight" stroke="#4a5568" stroke-width="2" />
            <line :x1="PADDING.left" :y1="PADDING.top + innerHeight" :x2="PADDING.left + innerWidth" :y2="PADDING.top + innerHeight" stroke="#4a5568" stroke-width="2" />

            <path v-if="selectedVisualization === 'area'" :d="pressureAreaPath" fill="#10b981" style="opacity: 0.18" />

            <polyline
              v-if="selectedVisualization === 'line' || selectedVisualization === 'area'"
              :points="pressureLinePoints"
              fill="none"
              stroke="#10b981"
              stroke-width="2.5"
              style="filter: drop-shadow(0 0 4px rgba(16, 185, 129, 0.6))"
            />

            <template v-if="selectedVisualization === 'scatter' || selectedVisualization === 'line' || selectedVisualization === 'area'">
              <circle
                v-for="p in pressureSeries"
                :key="`p-pt-${p.i}`"
                :cx="p.x"
                :cy="p.y"
                :r="selectedVisualization === 'scatter' ? 6 : 4"
                fill="#10b981"
                style="opacity: 0.65; cursor: pointer"
                @mouseover="hoveredPoint = { type: 'pres', v: p.v, t: p.t }"
                @mouseout="hoveredPoint = null"
              >
                <title>{{ p.v?.toFixed(2) }} hPa · {{ formatTs(p.t) }}</title>
              </circle>
            </template>

            <template v-if="selectedVisualization === 'bar'">
              <rect
                v-for="b in presBars"
                :key="`p-bar-${b.i}`"
                :x="b.x"
                :y="b.y"
                :width="b.w"
                :height="b.h"
                rx="3"
                fill="#10b981"
                style="opacity: 0.75; cursor: pointer"
                @mouseover="hoveredPoint = { type: 'pres', v: b.v, t: b.t }"
                @mouseout="hoveredPoint = null"
              >
                <title>{{ b.v?.toFixed(2) }} hPa · {{ formatTs(b.t) }}</title>
              </rect>
            </template>
          </svg>

          <div v-if="hoveredPoint?.type === 'pres'" class="tooltip tooltip-pres">
            {{ hoveredPoint.v?.toFixed(2) }} hPa
            <div class="tooltip-sub">{{ formatTs(hoveredPoint.t) }}</div>
          </div>
        </div>

        <div class="zoom-row">
          <button class="btn btn-primary btn-sm" @click="zoomIn"><i class="bi bi-zoom-in"></i> Zoom In</button>
          <button class="btn btn-primary btn-sm" @click="zoomOut"><i class="bi bi-zoom-out"></i> Zoom Out</button>
          <button class="btn btn-muted btn-sm" @click="resetView"><i class="bi bi-arrow-counterclockwise"></i> Reset</button>
          <span class="zoom-label">Zoom: {{ (zoomLevel * 100).toFixed(0) }}%</span>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="panel empty">
      <i class="bi bi-inbox empty-icon"></i>
      <p class="empty-text">No data available. Select a device and load data to begin.</p>
    </div>
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

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-title {
  color: var(--text);
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.3px;
}

.header-subtitle {
  color: var(--muted);
  margin: 0;
  font-size: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

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
}

.panel {
  background: var(--panel);
  padding: 16px;
  border-radius: 6px;
  border: 1px solid var(--panel-border);
  box-shadow: 0 10px 24px rgba(0,0,0,0.2);
  margin-bottom: 16px;
}

.controls-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 15px;
}

.label {
  color: var(--muted);
  font-weight: 700;
  display: block;
  margin-bottom: 6px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.input {
  width: 100%;
  padding: 8px 10px;
  background: #0f172a;
  color: var(--text);
  border: 1px solid var(--panel-border);
  border-radius: 4px;
  font-size: 13px;
  outline: none;
}

.input:focus {
  border-color: var(--accent);
}

.help {
  margin-top: 8px;
  color: var(--muted);
  font-size: 12px;
}

.load-wrap {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

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
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
  text-transform: uppercase;
  font-size: 12px;
  letter-spacing: 0.4px;
  background: #0f172a;
  color: var(--text);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #0f172a;
  color: var(--text);
  border-color: var(--accent);
}

.btn-primary:hover:not(:disabled) {
  background: #0b1220;
  box-shadow: 0 0 14px rgba(96, 165, 250, 0.25);
  transform: translateY(-1px);
}

.btn-muted {
  background: #0f172a;
  color: var(--muted);
}

.btn-muted:hover {
  color: var(--text);
  border-color: var(--muted);
  transform: translateY(-1px);
}

.btn-sm {
  padding: 8px 12px;
  font-size: 12px;
  border-radius: 5px;
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
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.stat {
  padding: 16px;
  border-radius: 6px;
  color: var(--text);
  background: var(--panel);
  border: 1px solid var(--panel-border);
  box-shadow: 0 8px 18px rgba(0,0,0,0.2);
}

.stat-temp { border-left: 3px solid #ef4444; }
.stat-hum { border-left: 3px solid #3b82f6; }
.stat-pres { border-left: 3px solid #10b981; }
.stat-count { border-left: 3px solid #8b5cf6; }

.stat-label { font-size: 14px; opacity: 0.9; margin-bottom: 8px; font-weight: 700; }
.stat-value { font-size: 30px; font-weight: 900; margin-bottom: 8px; }
.stat-sub { font-size: 12px; opacity: 0.85; }

.viz-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.viz-title {
  color: var(--muted);
  font-weight: 800;
  margin-right: 10px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  font-size: 12px;
}

.viz-btn {
  padding: 8px 12px;
  background: #0f172a;
  color: var(--text);
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: box-shadow 0.15s ease, transform 0.15s ease, background 0.15s ease, border-color 0.15s ease;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.viz-btn:hover {
  box-shadow: 0 0 12px rgba(96, 165, 250, 0.2);
  transform: translateY(-1px);
}

.viz-btn.active {
  background: #0b1220;
  border: 1px solid var(--accent);
  font-weight: 800;
  color: #fff;
}

.viz-num {
  background: rgba(0,0,0,0.35);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 900;
  font-size: 11px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(560px, 1fr));
  gap: 16px;
}

.chart-panel {
  transition: box-shadow 0.2s ease;
}

.chart-panel:hover {
  box-shadow: 0 14px 32px rgba(0,0,0,0.35);
}

.chart-span {
  grid-column: 1 / -1;
}

.chart-title {
  color: var(--text);
  margin: 0 0 12px 0;
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.chart-wrap {
  height: 350px;
  background: var(--panel-2);
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  overflow: hidden;
  position: relative;
  cursor: grab;
}

.chart-wrap:active {
  cursor: grabbing;
}

.tooltip {
  position: absolute;
  bottom: 18px;
  left: 18px;
  background: rgba(10, 15, 20, 0.92);
  padding: 10px 14px;
  border-radius: 6px;
  font-weight: 800;
  border: 1px solid var(--panel-border);
}

.tooltip-sub {
  font-size: 11px;
  opacity: 0.8;
  margin-top: 4px;
  font-weight: 600;
}

.tooltip-temp { color: #ef4444; border-color: rgba(239, 68, 68, 0.7); }
.tooltip-hum { color: #3b82f6; border-color: rgba(59, 130, 246, 0.7); }
.tooltip-pres { color: #10b981; border-color: rgba(16, 185, 129, 0.7); }

.zoom-row {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
}

.zoom-label {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.empty {
  padding: 60px;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  color: #4a5568;
  display: block;
  margin-bottom: 18px;
}

.empty-text {
  color: var(--muted);
  font-size: 16px;
  margin: 0;
}

/* Pie */
.pie-wrap {
  position: relative;
  width: 300px;
  height: 300px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pie-svg {
  width: 100%;
  height: 100%;
}

.pie-seg {
  opacity: 0.85;
  cursor: pointer;
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.pie-seg:hover {
  opacity: 1;
}

.pie-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: var(--text);
}

.pie-label {
  font-size: 14px;
  opacity: 0.85;
  font-weight: 700;
}

.pie-pct {
  font-size: 22px;
  font-weight: 900;
}
</style>
