<template>
  <div class="container py-3">
    <!-- Controls -->
    <div class="card shadow-sm mb-3">
      <div class="card-body">
        <div class="row g-3 align-items-end">
          <div class="col-12 col-md-3">
            <label class="form-label">Device ID</label>
            <input v-model="deviceId" class="form-control" placeholder="e.g. device-001" />
          </div>

          <div class="col-12 col-md-2">
            <label class="form-label">Range</label>
            <select v-model="range" class="form-select">
              <option value="1h">Last 1 hour</option>
              <option value="6h">Last 6 hours</option>
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
            </select>
          </div>

          <div class="col-12 col-md-3">
            <label class="form-label">Bucket (discrete time)</label>
            <select v-model.number="bucketMinutes" class="form-select">
              <option :value="0">No bucketing (raw)</option>
              <option :value="1">1 minute</option>
              <option :value="5">5 minutes</option>
              <option :value="15">15 minutes</option>
              <option :value="60">60 minutes</option>
            </select>
            <div class="form-text">
              Groups points into fixed intervals and averages values.
            </div>
          </div>

          <div class="col-12 col-md-2">
            <label class="form-label">Auto refresh</label>
            <select v-model.number="refreshSeconds" class="form-select">
              <option :value="0">Off</option>
              <option :value="10">Every 10s</option>
              <option :value="30">Every 30s</option>
              <option :value="60">Every 60s</option>
            </select>
          </div>

          <div class="col-12 col-md-2 d-grid">
            <button class="btn btn-primary" @click="loadSeries" :disabled="loading">
              <span v-if="loading" class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
              {{ loading ? "Loading..." : "Load" }}
            </button>
          </div>
        </div>

        <div v-if="error" class="alert alert-danger mt-3 mb-0">
          {{ error }}
        </div>

        <div v-else-if="!loading && series.length === 0" class="alert alert-secondary mt-3 mb-0">
          No data returned.
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div class="row g-3">
      <div class="col-12 col-lg-6">
        <div class="card shadow-sm h-100">
          <div class="card-header bg-white">
            <strong>Pressure vs Time</strong>
          </div>
          <div class="card-body">
            <VChart :option="pressureOption" autoresize style="height: 340px; width: 100%" />
          </div>
        </div>
      </div>

      <div class="col-12 col-lg-6">
        <div class="card shadow-sm h-100">
          <div class="card-header bg-white">
            <strong>Temperature vs Time</strong>
          </div>
          <div class="card-body">
            <VChart :option="temperatureOption" autoresize style="height: 340px; width: 100%" />
          </div>
        </div>
      </div>

      <div class="col-12">
        <div class="card shadow-sm">
          <div class="card-header bg-white">
            <strong>Combined (Pressure + Temperature)</strong>
          </div>
          <div class="card-body">
            <VChart :option="combinedOption" autoresize style="height: 360px; width: 100%" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue"
import VChart from "vue-echarts"
import * as echarts from "echarts/core"
import { LineChart } from "echarts/charts"
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
} from "echarts/components"
import { CanvasRenderer } from "echarts/renderers"

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

/**
 * Expected backend JSON (InfluxDB -> your API -> browser):
 * [
 *   { time: "2025-12-30T10:00:00Z", pressure: 1012.3, temperature: 21.8 },
 *   ...
 * ]
 */
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000"

const deviceId = ref("device-101")
const range = ref("6h")
const bucketMinutes = ref(5)
const refreshSeconds = ref(30)

const series = ref([]) // [{t(ms), pressure, temperature}]
const loading = ref(false)
const error = ref("")
let timer = null

function parseTimeToMs(t) {
  const ms = Date.parse(t)
  return Number.isFinite(ms) ? ms : null
}

function normalizePayload(payload) {
  if (!Array.isArray(payload)) return []
  return payload
    .map((row) => {
      const tms = parseTimeToMs(row.time ?? row.timestamp ?? row._time)
      const p = Number(row.pressure ?? row.p ?? row._pressure)
      const temp = Number(row.temperature ?? row.temp ?? row._temperature)
      if (tms == null) return null
      return {
        t: tms,
        pressure: Number.isFinite(p) ? p : null,
        temperature: Number.isFinite(temp) ? temp : null,
      }
    })
    .filter(Boolean)
    .sort((a, b) => a.t - b.t)
}

/**
 * Discrete time bucket: average per interval (ignores nulls)
 */
function bucketize(points, bucketMin) {
  if (!bucketMin || bucketMin <= 0) return points
  const bucketMs = bucketMin * 60 * 1000
  const map = new Map()

  for (const pt of points) {
    const key = Math.floor(pt.t / bucketMs) * bucketMs
    if (!map.has(key)) map.set(key, { t: key, pSum: 0, pN: 0, tSum: 0, tN: 0 })
    const agg = map.get(key)
    if (pt.pressure != null) { agg.pSum += pt.pressure; agg.pN += 1 }
    if (pt.temperature != null) { agg.tSum += pt.temperature; agg.tN += 1 }
  }

  return Array.from(map.values())
    .sort((a, b) => a.t - b.t)
    .map((a) => ({
      t: a.t,
      pressure: a.pN ? a.pSum / a.pN : null,
      temperature: a.tN ? a.tSum / a.tN : null,
    }))
}

async function loadSeries() {
  loading.value = true
  error.value = ""
  try {
    // Adjust to your endpoint
    const url = new URL(`${API_BASE}/api/weather/forecast/?minutes=60`)
    url.searchParams.set("device_id", deviceId.value)
    url.searchParams.set("range", range.value)
    // If your backend supports it, send bucket too:
    url.searchParams.set("bucket_minutes", String(bucketMinutes.value))

    const res = await fetch(url.toString())
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    const payload = await res.json()

    const normalized = normalizePayload(payload)

    // If backend already buckets, you can skip this bucketize.
    // Keeping it here makes the UI work even if backend doesn't bucket.
    series.value = bucketize(normalized, bucketMinutes.value)
  } catch (e) {
    error.value = e?.message || String(e)
    series.value = []
  } finally {
    loading.value = false
  }
}

function stopTimer() {
  if (timer) clearInterval(timer)
  timer = null
}

function startTimer() {
  stopTimer()
  if (!refreshSeconds.value || refreshSeconds.value <= 0) return
  timer = setInterval(loadSeries, refreshSeconds.value * 1000)
}

watch(refreshSeconds, startTimer)

onMounted(() => { loadSeries(); startTimer() })
onBeforeUnmount(stopTimer)

const pressureData = computed(() =>
  series.value.filter(p => p.pressure != null).map(p => [p.t, p.pressure])
)
const temperatureData = computed(() =>
  series.value.filter(p => p.temperature != null).map(p => [p.t, p.temperature])
)

function baseTimeOption() {
  return {
    animation: false,
    tooltip: { trigger: "axis" },
    grid: { left: 55, right: 20, top: 20, bottom: 55 },
    dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 15 }],
    xAxis: { type: "time", axisLabel: { hideOverlap: true } },
  }
}

const pressureOption = computed(() => ({
  ...baseTimeOption(),
  yAxis: { type: "value", name: "hPa" },
  series: [{ name: "Pressure", type: "line", showSymbol: false, data: pressureData.value }],
}))

const temperatureOption = computed(() => ({
  ...baseTimeOption(),
  yAxis: { type: "value", name: "°C" },
  series: [{ name: "Temperature", type: "line", showSymbol: false, data: temperatureData.value }],
}))

const combinedOption = computed(() => ({
  animation: false,
  tooltip: { trigger: "axis" },
  legend: { top: 0 },
  grid: { left: 60, right: 60, top: 30, bottom: 55 },
  dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 15 }],
  xAxis: { type: "time" },
  yAxis: [
    { type: "value", name: "hPa" },
    { type: "value", name: "°C" },
  ],
  series: [
    { name: "Pressure", type: "line", yAxisIndex: 0, showSymbol: false, data: pressureData.value },
    { name: "Temperature", type: "line", yAxisIndex: 1, showSymbol: false, data: temperatureData.value },
  ],
}))
</script>
