// SensorPanel.vue - Attractive Design (Updated)
<script setup>
import { ref, computed } from 'vue'
import * as echarts from 'echarts'
import VChart from 'vue-echarts'
import logo from '@/assets/Logo.svg'

const props = defineProps({
  title: { type: String, default: 'Weather Data' },
  temperature: { type: [String, Number], default: '—' },
  humidity: { type: [String, Number], default: '—' },
  pressure: { type: [String, Number], default: '—' },
  light: { type: [String, Number], default: '—' },
  noise: { type: [String, Number], default: '—' },
  tof: { type: [String, Number], default: '—' },
  angle: { type: [String, Number], default: '—' },
  accX: { type: [String, Number], default: '—' },
  accY: { type: [String, Number], default: '—' },
  accZ: { type: [String, Number], default: '—' },
  vibrAccX: { type: [String, Number], default: '—' },
  vibrAccY: { type: [String, Number], default: '—' },
  vibrAccZ: { type: [String, Number], default: '—' },
  cpuTemperature: { type: [String, Number], default: '—' },
  ramUsage: { type: [String, Number], default: '—' },
  storageUsage: { type: [String, Number], default: '—' },
  history: { type: Array, default: () => [] },
  deviceId: { type: String, default: '—' },
  observedAt: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  formatValue: { type: Function, required: true },
})

const emit = defineEmits(['refresh'])
const isZooming = ref(false)

function computeChartOption(metric, color) {
  const data = props.history.map(r => r[metric] ?? 0)
  const times = props.history.map(r => {
    const date = new Date(r.time)
    return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`
  })

  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: '#222', textStyle: { color: '#fff' } },
    grid: { top: 10, bottom: 20, left: 30, right: 10 },
    xAxis: {
      type: 'category',
      data: times,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.2)' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 9, interval: Math.floor(times.length / 4) },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: true, lineStyle: { color: 'rgba(255,255,255,0.2)' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)', fontSize: 9 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    series: [{
      data: data,
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: { color: color, width: 2 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: color + '66' },
            { offset: 1, color: color + '00' }
          ]
        }
      }
    }]
  }
}

const tempChartOption = computed(() => computeChartOption('temperature', '#ff6b6b'))
const humChartOption = computed(() => computeChartOption('humidity', '#0dcaf0'))
const pressChartOption = computed(() => computeChartOption('pressure', '#20c997'))

function toNumber(value) {
  if (value === '—' || value === null || value === undefined || value === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function metricHealth(metric, value) {
  const n = toNumber(value)
  if (n === null) return { color: '#6c757d', label: 'No data' }

  if (metric === 'cpu') {
    if (n > 80) return { color: '#dc3545', label: 'Critical' }
    if (n > 50) return { color: '#ffc107', label: 'Warning' }
    return { color: '#20c997', label: 'Healthy' }
  }

  if (n > 90) return { color: '#dc3545', label: 'Critical' }
  if (n > 70) return { color: '#ffc107', label: 'Warning' }
  return { color: '#20c997', label: 'Healthy' }
}

function formatMetric(value, unit) {
  const n = toNumber(value)
  if (n === null) return '—'
  return `${n.toFixed(1)}${unit}`
}

const systemMetrics = computed(() => [
  {
    key: 'cpu',
    label: 'CPU',
    icon: 'bi-cpu',
    value: formatMetric(props.cpuTemperature, '°C'),
    ...metricHealth('cpu', props.cpuTemperature)
  },
  {
    key: 'ram',
    label: 'RAM',
    icon: 'bi-memory',
    value: formatMetric(props.ramUsage, '%'),
    ...metricHealth('ram', props.ramUsage)
  },
  {
    key: 'storage',
    label: 'Storage',
    icon: 'bi-device-hdd',
    value: formatMetric(props.storageUsage, '%'),
    ...metricHealth('storage', props.storageUsage)
  }
])

async function handleCardClick() {
  isZooming.value = true
  setTimeout(() => {
    emit('refresh')
    isZooming.value = false
  }, 250)
}

</script>

<template>
  <div class="card bg-dark border-0 shadow-lg h-100 overflow-hidden position-relative">
    <!-- Gradient Overlay -->
    <div class="position-absolute top-0 start-0 w-100 h-100"
         style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(147, 51, 234, 0.1) 100%); pointer-events: none;"></div>

    <div class="card-body position-relative">
      <!-- Header Section -->
      <div class="d-flex justify-content-between align-items-start mb-4">
        <div class="d-flex align-items-center gap-3">
          <div class="bg-primary bg-opacity-25 p-3 rounded-3">
            <img :src="logo" alt="Logo" width="40" height="40" class="d-block"/>
          </div>
          <div>
            <h5 class="text-white fw-bold mb-1">Weather Station Robustel {{ deviceId }}</h5>
            <span class="badge bg-primary bg-opacity-50 text-white px-3 py-2">
              <i class="bi bi-broadcast-pin me-1"></i>
              {{ deviceId }}
            </span>
          </div>
        </div>

        <button
          class="btn btn-outline-light btn-sm rounded-pill px-3"
          @click="emit('refresh')"
          :disabled="loading"
        >
          <i class="bi bi-arrow-clockwise me-1" :class="{ 'spinner': loading }"></i>
          Detail
        </button>
      </div>

      <!-- Timestamp -->
      <div class="text-white-50 small mb-4 d-flex align-items-center gap-2">
        <i class="bi bi-clock-history"></i>
        <span>{{ observedAt }}</span>
      </div>

      <!-- Edge System Metrics -->
      <div class="row g-2 mb-4">
        <div v-for="metric in systemMetrics" :key="metric.key" class="col-12 col-sm-4">
          <div class="system-chip" :style="{ '--system-color': metric.color }" :title="metric.status">
            <i :class="['bi', metric.icon]"></i>
            <div class="min-w-0">
              <div class="system-chip-label">{{ metric.label }}</div>
              <div class="system-chip-value">{{ metric.value }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Weather Metrics Grid -->
      <div class="row g-3">
        <!-- Temperature Card -->
        <div class="col-12">
          <div class="metric-card bg-gradient text-white p-4 rounded-4 border border-danger border-opacity-25"
               style="background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);">
            <div class="d-flex justify-content-between align-items-start">
              <div class="flex-grow-1">
                <div class="d-flex align-items-center gap-2 mb-2">
                  <i class="bi bi-thermometer-half fs-4"></i>
                  <span class="text-white-50 small text-uppercase fw-semibold letter-spacing">Temperature</span>
                </div>
                <div class="display-4 fw-bold">
                  {{ formatValue(temperature, '°C') }}
                </div>
              </div>
              <div class="metric-icon">
                <i class="bi bi-thermometer-sun fs-1 opacity-25"></i>
              </div>
            </div>
          </div>
        </div>

        <!-- Humidity Card -->
        <div class="col-12 col-md-6">
          <div class="metric-card bg-gradient text-white p-4 rounded-4 border border-info border-opacity-25"
               style="background: linear-gradient(135deg, #0dcaf0 0%, #0d6efd 100%);">
            <div class="d-flex justify-content-between align-items-start">
              <div class="flex-grow-1">
                <div class="d-flex align-items-center gap-2 mb-2">
                  <i class="bi bi-droplet-half fs-5"></i>
                  <span class="text-white-50 small text-uppercase fw-semibold letter-spacing">Humidity</span>
                </div>
                <div class="display-6 fw-bold">
                  {{ formatValue(humidity, '%') }}
                </div>
              </div>
              <div class="metric-icon">
                <i class="bi bi-water fs-2 opacity-25"></i>
              </div>
            </div>
          </div>
        </div>

        <!-- Pressure Card -->
        <div class="col-12 col-md-6">
          <div class="metric-card bg-gradient text-white p-4 rounded-4 border border-success border-opacity-25"
               style="background: linear-gradient(135deg, #20c997 0%, #198754 100%);">
            <div class="d-flex justify-content-between align-items-start">
              <div class="flex-grow-1">
                <div class="d-flex align-items-center gap-2 mb-2">
                  <i class="bi bi-speedometer2 fs-5"></i>
                  <span class="text-white-50 small text-uppercase fw-semibold letter-spacing">Pressure</span>
                </div>
                <div class="display-6 fw-bold">
                  {{ formatValue(pressure, 'kPa') }}
                </div>
              </div>
              <div class="metric-icon">
                <i class="bi bi-arrows-expand fs-2 opacity-25"></i>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="mt-4">
        <div class="d-flex align-items-center justify-content-center gap-2 text-primary bg-primary bg-opacity-10 rounded-3 py-3">
          <div class="spinner-border spinner-border-sm" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <span class="small fw-semibold">Updating data...</span>
        </div>
      </div>

      <!-- Error State -->
      <div v-if="error" class="alert alert-danger alert-dismissible fade show mt-4 mb-0" role="alert">
        <div class="d-flex align-items-center">
          <i class="bi bi-exclamation-triangle-fill fs-5 me-2"></i>
          <div>
            <strong>Error Loading Data</strong>
            <p class="mb-0 small mt-1">{{ error }}</p>
          </div>
        </div>
        <button type="button" class="btn-close" @click="$emit('refresh')" aria-label="Retry"></button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.metric-card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  cursor: default;
  position: relative;
  overflow: hidden;
}

.metric-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(45deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 100%);
  pointer-events: none;
}

.metric-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.metric-icon {
  line-height: 1;
}

.letter-spacing {
  letter-spacing: 0.05em;
}

.system-chip {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-height: 58px;
  padding: 0.75rem;
  border: 1px solid color-mix(in srgb, var(--system-color), transparent 50%);
  border-radius: 0.5rem;
  background: color-mix(in srgb, var(--system-color), transparent 86%);
  color: #fff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
}

.system-chip i {
  color: var(--system-color);
  font-size: 1.25rem;
  line-height: 1;
}

.system-chip-label {
  color: rgba(255, 255, 255, 0.58);
  font-size: 0.72rem;
  font-weight: 700;
  line-height: 1.1;
  text-transform: uppercase;
}

.system-chip-value {
  color: #fff;
  font-size: 1rem;
  font-weight: 800;
  line-height: 1.2;
}

@keyframes spinner {
  to {
    transform: rotate(360deg);
  }
}

.spinner {
  animation: spinner 1s linear infinite;
  display: inline-block;
}

/* Glassmorphism effect for cards */
.card {
  backdrop-filter: blur(10px);
  background: rgba(33, 37, 41, 0.95) !important;
  transition: transform 0.2s ease;
}

.card:hover {
  transform: translateY(-2px);
}

/* Badge styling */
.badge {
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

/* Responsive font sizes */
@media (max-width: 768px) {
  .display-4 {
    font-size: 2.5rem;
  }

  .display-6 {
    font-size: 1.75rem;
  }

  .metric-card {
    padding: 1rem !important;
  }
}

/* Loading state styling */
.bg-primary.bg-opacity-10 {
  backdrop-filter: blur(5px);
}

/* Alert improvements */
.alert {
  border-radius: 0.75rem;
  border: none;
}
</style>
