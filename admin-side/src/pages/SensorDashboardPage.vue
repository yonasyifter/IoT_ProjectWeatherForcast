// SensorDashboardPage.vue - Updated with Detail Modal and Weather Prediction
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

import api from '../utils/api.js'
import AppShell from '../components/layout/AppShell.vue'
import SensorPanel from '../components/sensors/SensorPanel.vue'
import RagChatbot from '../components/RagChatbot.vue'

const devices = ref([]) // Array to store all device readings
const error = ref('')
const loading = ref(false)
const searchQuery = ref('')
const searchAttempted = ref(false)
const notFoundMessage = ref('')
const showDetailModal = ref(false)
const selectedDevice = ref(null)
const detailLoading = ref(false)
const deviceHistory = ref([])

// Required by AppShell but not used for tab switching in this page
const tabs = []
const activeTab = ref('')
// Alias for RagChatbot prop
const sensorRows = computed(() => devices.value)

let timer = null

function toNumber(value) {
  if (value === '—' || value === null || value === undefined || value === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function firstNumber(reading, keys) {
  for (const key of keys) {
    const n = toNumber(reading?.[key])
    if (n !== null) return n
  }
  return null
}

function parseStorageValue(value) {
  if (value === null || value === undefined || value === '' || value === '—') return null
  if (typeof value === 'number') return Number.isFinite(value) ? value : null

  const match = String(value).trim().match(/^([\d.]+)\s*([kmgt]?i?b?|bytes?)?$/i)
  if (!match) return null

  const n = Number(match[1])
  if (!Number.isFinite(n)) return null

  const unit = (match[2] || '').toLowerCase()
  const multipliers = {
    k: 1024,
    kb: 1024,
    kib: 1024,
    m: 1024 ** 2,
    mb: 1024 ** 2,
    mib: 1024 ** 2,
    g: 1024 ** 3,
    gb: 1024 ** 3,
    gib: 1024 ** 3,
    t: 1024 ** 4,
    tb: 1024 ** 4,
    tib: 1024 ** 4,
    b: 1,
    byte: 1,
    bytes: 1
  }

  return n * (multipliers[unit] || 1)
}

function usageFromTotalFree(total, free) {
  const totalNumber = toNumber(total)
  const freeNumber = toNumber(free)
  if (totalNumber === null || freeNumber === null || totalNumber <= 0) return null
  return Math.min(100, Math.max(0, ((totalNumber - freeNumber) / totalNumber) * 100))
}

function normalizeSystemMetrics(reading) {
  const ramTotal = firstNumber(reading, ['EG5120_RAM_total_mb', 'ram_total_mb', 'RAM_total_mb'])
  const ramFree = firstNumber(reading, ['EG5120_RAM_free_mb', 'ram_free_mb', 'RAM_free_mb'])
  const storageTotalRaw = reading?.EG5120_Storage_total ?? reading?.storage_total ?? reading?.Storage_total
  const storageFreeRaw = reading?.EG5120_Storage_free ?? reading?.storage_free ?? reading?.Storage_free
  const storageTotal = parseStorageValue(storageTotalRaw)
  const storageFree = parseStorageValue(storageFreeRaw)

  return {
    cpuTemperature: firstNumber(reading, ['EG5120_CPU_Temprature', 'EG5120_CPU_Temperature', 'CPU_temprature', 'CPU_temperature']),
    cpuStatus: reading?.EG5120_CPU_status ?? '—',
    ramTotalMb: ramTotal,
    ramFreeMb: ramFree,
    ramUsage: firstNumber(reading, ['EG5120_RAM_usage', 'EG5120_RAM_Usage', 'RAM_Usage', 'ram_usage']) ?? usageFromTotalFree(ramTotal, ramFree),
    storageTotal: storageTotalRaw ?? '—',
    storageFree: storageFreeRaw ?? '—',
    storageUsage: firstNumber(reading, ['EG5120_Storage_usage', 'EG5120_Storage_Usage', 'Storage_Usage', 'storage_usage']) ?? usageFromTotalFree(storageTotal, storageFree)
  }
}

function clampPercent(value) {
  const n = toNumber(value)
  if (n === null) return 0
  return Math.min(100, Math.max(0, n))
}

function systemHealth(metric, value) {
  const n = toNumber(value)
  if (n === null) return { color: '#6c757d', label: 'No data' }

  if (metric === 'cpu') {
    if (n > 70) return { color: '#dc3545', label: 'Critical' }
    if (n > 45) return { color: '#ffc107', label: 'Warning' }
    return { color: '#20c997', label: 'Healthy' }
  }

  if (n > 80) return { color: '#dc3545', label: 'Critical' }
  if (n > 70) return { color: '#ffc107', label: 'Warning' }
  return { color: '#20c997', label: 'Healthy' }
}

function formatGaugeValue(value, unit) {
  const n = toNumber(value)
  if (n === null) return '—'
  return `${n.toFixed(1)}${unit}`
}

const systemGauges = computed(() => {
  const device = selectedDevice.value || {}
  const gauges = [
    {
      key: 'cpu',
      label: 'CPU Temperature',
      icon: 'bi-cpu',
      value: device.cpuTemperature,
      unit: '°C',
      percent: Math.min(100, Math.max(0, ((toNumber(device.cpuTemperature) ?? 0) / 80) * 100)),
      detail: device.cpuStatus && device.cpuStatus !== '—' ? device.cpuStatus : 'Thresholds: 45°C / 70°C'
    },
    {
      key: 'ram',
      label: 'RAM Usage',
      icon: 'bi-memory',
      value: device.ramUsage,
      unit: '%',
      percent: clampPercent(device.ramUsage),
      detail: device.ramTotalMb ? `${Math.round(device.ramFreeMb ?? 0)} MB free of ${Math.round(device.ramTotalMb)} MB` : 'Thresholds: 70% / 80%'
    },
    {
      key: 'storage',
      label: 'Storage Usage',
      icon: 'bi-device-hdd',
      value: device.storageUsage,
      unit: '%',
      percent: clampPercent(device.storageUsage),
      detail: device.storageFree !== '—' && device.storageTotal !== '—' ? `${device.storageFree} free of ${device.storageTotal}` : 'Thresholds: 70% / 80%'
    }
  ]

  return gauges.map(gauge => {
    const health = systemHealth(gauge.key, gauge.value)
    return {
      ...gauge,
      color: health.color,
      status: health.label,
      displayValue: formatGaugeValue(gauge.value, gauge.unit),
      fillDegrees: `${gauge.percent * 3.6}deg`
    }
  })
})

async function loadLatest() {
  try {
    error.value = ''
    loading.value = true

    const data = await api.get(`/api/weather/forecast/?minutes=60`)

    if (!Array.isArray(data) || data.length === 0) {
      devices.value = []
      return
    }

    // Group readings by device_id and get the latest reading and history for each device
    const deviceMap = new Map()

    data.forEach(reading => {
      const deviceId = reading.device_id

      // Skip readings without a timestamp
      if (!reading.time) return

      if (!deviceMap.has(deviceId)) {
        deviceMap.set(deviceId, {
          latest: reading,
          history: []
        })
      }

      const deviceData = deviceMap.get(deviceId)
      deviceData.history.push(reading)

      const currentTime = new Date(reading.time).getTime()
      const latestTime = new Date(deviceData.latest.time).getTime()

      if (currentTime > latestTime) {
        deviceData.latest = reading
      }
    })

    // Convert map to array, transform data, and sort by device_id
    devices.value = Array.from(deviceMap.values()).map(item => {
      const reading = item.latest
      const systemMetrics = normalizeSystemMetrics(reading)
      return {
        deviceId: reading.device_id,
        temperature: reading.temperature ?? '—',
        humidity: reading.humidity ?? '—',
        pressure: reading.pressure ? (reading.pressure / 1000).toFixed(2) : '—',
        light: reading.light ?? '—',
        noise: reading.noise ?? '—',
        tof: reading.tof ?? '—',
        angle: reading.angle ?? '—',
        weather_prediction: reading.weather_prediction ?? '—',
        accX: reading.accX ?? '—',
        accY: reading.accY ?? '—',
        accZ: reading.accZ ?? '—',
        vibrAccX: reading.vibrAccX ?? '—',
        vibrAccY: reading.vibrAccY ?? '—',
        vibrAccZ: reading.vibrAccZ ?? '—',
        ...systemMetrics,
        observedAt: reading.time ? new Date(reading.time).toLocaleString() : '—',
        timestamp: reading.time,
        history: item.history.sort((a, b) => new Date(a.time) - new Date(b.time))
      }
    }).sort((a, b) => {
      const idA = String(a.deviceId || '')
      const idB = String(b.deviceId || '')
      return idA.localeCompare(idB)
    })

  } catch (e) {
    error.value = String(e)
    console.error('Error loading data:', e)
  } finally {
    loading.value = false
  }
}

// Load detailed device information for specific device only
async function loadDeviceDetails(deviceId) {
  try {
    detailLoading.value = true
    
    // Fetch all device history for the last 1 hour, then filter by deviceId client-side
    // (the backend /forecast/ endpoint does not support device_id filtering)
    const data = await api.get(`/api/weather/forecast/?minutes=60`)
    
    // Filter to ensure we only have data for this specific device
    const filteredData = Array.isArray(data)
      ? data.filter(reading => reading.device_id === deviceId)
      : []
    
    deviceHistory.value = filteredData.map(reading => ({
      time: reading.time ? new Date(reading.time).toLocaleString() : '—',
      temperature: reading.temperature ?? '—',
      humidity: reading.humidity ?? '—',
      pressure: reading.pressure ?? '—',
      light: reading.light ?? '—',
      noise: reading.noise ?? '—',
      tof: reading.tof ?? '—',
      angle: reading.angle ?? '—',
      weather_prediction: reading.weather_prediction ?? '—',
      accX: reading.accX ?? '—',
      accY: reading.accY ?? '—',
      accZ: reading.accZ ?? '—',
      vibrAccX: reading.vibrAccX ?? '—',
      vibrAccY: reading.vibrAccY ?? '—',
      vibrAccZ: reading.vibrAccZ ?? '—',
      deviceId: reading.device_id
    })).reverse() // Most recent first
    
  } catch (e) {
    console.error('Error loading device details:', e)
    deviceHistory.value = []
  } finally {
    detailLoading.value = false
  }
}

// Show detail modal
async function showDetails(device) {
  selectedDevice.value = device
  showDetailModal.value = true
  await loadDeviceDetails(device.deviceId)
}

// Close modal
function closeModal() {
  showDetailModal.value = false
  selectedDevice.value = null
  deviceHistory.value = []
}

// Filter devices based on search query
const filteredDevices = computed(() => {
  if (!searchQuery.value.trim()) {
    return devices.value
  }
  const query = searchQuery.value.toLowerCase()
  return devices.value.filter(device => {
    const deviceIdStr = String(device.deviceId || '').toLowerCase()
    return deviceIdStr.includes(query)
  })
})

function handleSearch() {
  searchAttempted.value = true
  notFoundMessage.value = ''
  
  if (!searchQuery.value.trim()) {
    searchAttempted.value = false
    return
  }
  
  const query = searchQuery.value.toLowerCase()
  const found = devices.value.some(device => {
    const deviceIdStr = String(device.deviceId || '').toLowerCase()
    return deviceIdStr.includes(query)
  })
  
  if (!found) {
    notFoundMessage.value = `Device ID "${searchQuery.value}" does not exist`
    setTimeout(() => {
      notFoundMessage.value = ''
    }, 5000)
  }
}

function clearSearch() {
  searchQuery.value = ''
  searchAttempted.value = false
  notFoundMessage.value = ''
}

function formatValue(v, unit) {
  if (v === '—' || v === null || v === undefined) return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  return `${n.toFixed(1)} ${unit}`
}

onMounted(() => {
  loadLatest()
  timer = setInterval(loadLatest, 15_000) // Refresh every 15 seconds
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <AppShell
    :breadcrumbs="['Università della Calabria', 'TELECOMMUNICATION ENGINEERING: SMART SENSING, COMPUTING AND NETWORKING', 'IOT-Smart Park Project']"
    title="Load Weather Data and Monitor Dashboard"
    :tabs="tabs"
    :active-tab="activeTab"
    @update:active-tab="activeTab = $event"
  >
    <template #toolbar>
      <div class="d-flex flex-wrap gap-3 align-items-center">
        <div class="input-group" style="max-width: 520px;">
          <span class="input-group-text bg-black bg-opacity-25 border-secondary text-secondary">⌕</span>
          <input 
            v-model="searchQuery"
            @keyup.enter="handleSearch"
            class="form-control bg-black bg-opacity-25 border-secondary text-white"
            placeholder="Search based on device_ID..." 
          />
          <button 
            v-if="searchQuery"
            class="btn btn-outline-secondary"
            @click="clearSearch"
            title="Clear search"
          >
            <i class="bi bi-x-lg"></i>
          </button>
        </div>

        <div class="d-flex gap-2 flex-shrink-0">
          <button class="btn btn-outline-secondary fw-bold" @click="handleSearch">
            <i class="bi bi-search me-1"></i>
            Search
          </button>
          <button class="btn btn-outline-primary fw-bold" @click="loadLatest">
            <i class="bi bi-arrow-clockwise me-1"></i>
            Refresh All
          </button>
        </div>

        <div class="ms-auto text-secondary">
          <strong>{{ filteredDevices.length }}</strong> device{{ filteredDevices.length !== 1 ? 's' : '' }} 
          {{ searchQuery ? 'found' : 'total' }}
        </div>
      </div>
    </template>

    <!-- Device Not Found Alert -->
    <div v-if="notFoundMessage" class="alert alert-warning alert-dismissible fade show m-3" role="alert">
      <i class="bi bi-exclamation-triangle-fill me-2"></i>
      <strong>{{ notFoundMessage }}</strong>
      <p class="mb-0 mt-2 small">Available devices: {{ devices.map(d => d.deviceId).join(', ') || 'None' }}</p>
      <button type="button" class="btn-close" @click="notFoundMessage = ''" aria-label="Close"></button>
    </div>

    <!-- Loading State -->
    <div v-if="loading && devices.length === 0" class="text-center py-5">
      <div class="spinner-border text-secondary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="text-secondary mt-3">Loading device data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-danger m-3" role="alert">
      <i class="bi bi-exclamation-triangle me-2"></i>
      <strong>Error:</strong> {{ error }}
    </div>

    <!-- Empty State - No Data at All -->
    <div v-else-if="devices.length === 0" class="text-center py-5">
      <i class="bi bi-inbox fs-1 text-secondary"></i>
      <p class="text-secondary mt-3">No device data available</p>
      <button class="btn btn-primary mt-2" @click="loadLatest">
        <i class="bi bi-arrow-clockwise me-1"></i>
        Reload Data
      </button>
    </div>

    <!-- Search Result - No Matches -->
    <div v-else-if="searchAttempted && filteredDevices.length === 0" class="text-center py-5">
      <i class="bi bi-search fs-1 text-warning"></i>
      <p class="text-secondary mt-3 h5">No devices found matching "{{ searchQuery }}"</p>
      <p class="text-muted">Try searching for one of these available devices:</p>
      <div class="d-flex flex-wrap justify-content-center gap-2 mt-3">
        <button 
          v-for="device in devices" 
          :key="device.deviceId"
          class="btn btn-outline-primary btn-sm"
          @click="searchQuery = device.deviceId; handleSearch()"
        >
          {{ device.deviceId }}
        </button>
      </div>
      <button class="btn btn-secondary mt-4" @click="clearSearch">
        <i class="bi bi-x-circle me-1"></i>
        Clear Search & Show All
      </button>
    </div>

    <!-- Device Panels Grid -->
    <div v-else class="row g-3 p-3">
      <div 
        v-for="device in filteredDevices" 
        :key="device.deviceId"
        class="col-12 col-md-6 col-lg-4"
      >
        <SensorPanel
          :title="`Device: ${device.deviceId}`"
          :temperature="device.temperature"
          :humidity="device.humidity"
          :pressure="device.pressure"
          :light="device.light"
          :noise="device.noise"
          :tof="device.tof"
          :angle="device.angle"
          :accX="device.accX"
          :accY="device.accY"
          :accZ="device.accZ"
          :vibrAccX="device.vibrAccX"
          :vibrAccY="device.vibrAccY"
          :vibrAccZ="device.vibrAccZ"
          :cpu-temperature="device.cpuTemperature"
          :ram-usage="device.ramUsage"
          :storage-usage="device.storageUsage"
          :history="device.history"
          :device-id="device.deviceId"
          :observed-at="device.observedAt"
          :loading="loading"
          :error="error"
          :format-value="formatValue"
          @refresh="showDetails(device)"
          @click="showDetails(device)"
        />
      </div>
    </div>

    <!-- Refresh Indicator -->
    <div v-if="loading && devices.length > 0" class="position-fixed bottom-0 end-0 m-3" style="z-index: 1050;">
      <div class="bg-primary text-white px-3 py-2 rounded shadow">
        <div class="spinner-border spinner-border-sm me-2" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        Updating...
      </div>
    </div>

    <!-- RAG Chatbot Component -->
    <RagChatbot :deviceData="sensorRows" />


    <!-- Detail Modal -->
    <div 
      v-if="showDetailModal" 
      class="modal fade show d-block" 
      tabindex="-1" 
      style="background-color: rgba(0,0,0,0.5);"
      @click.self="closeModal"
    >
      <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable detail-modal-dialog">
        <div class="modal-content bg-dark text-white">
          <div class="modal-header border-secondary">
            <h5 class="modal-title">
              <i class="bi bi-info-circle me-2"></i>
              Device Details: {{ selectedDevice?.deviceId }}
            </h5>
            <button type="button" class="btn-close btn-close-white" @click="closeModal"></button>
          </div>
          <div class="modal-body">
            <!-- System Health Gauges -->
            <div class="card bg-black bg-opacity-25 border-secondary mb-4">
              <div class="card-header bg-black bg-opacity-50 border-secondary">
                <h6 class="mb-0">System Health Gauges</h6>
              </div>
              <div class="card-body">
                <div class="row g-3 system-gauge-grid">
                  <div v-for="gauge in systemGauges" :key="gauge.key" class="col-12 col-md-4">
                    <div class="system-gauge-card h-100" :style="{ '--gauge-color': gauge.color, '--gauge-fill': gauge.fillDegrees }">
                      <div class="system-gauge">
                        <div class="system-gauge-inner">
                          <i :class="['bi', gauge.icon, 'system-gauge-icon']"></i>
                          <strong>{{ gauge.displayValue }}</strong>
                        </div>
                      </div>
                      <div class="text-center mt-3">
                        <div class="fw-semibold text-white">{{ gauge.label }}</div>
                        <span class="badge mt-2" :style="{ backgroundColor: gauge.color }">{{ gauge.status }}</span>
                        <div class="text-secondary small mt-2">{{ gauge.detail }}</div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="mt-3 pt-3 border-top border-secondary">
                  <small class="text-secondary">Last Updated:</small>
                  <div class="text-white">{{ selectedDevice?.observedAt }}</div>
                </div>
              </div>
            </div>

            <!-- Historical Data -->
            <div class="card bg-black bg-opacity-25 border-secondary">
              <div class="card-header bg-black bg-opacity-50 border-secondary d-flex justify-content-between align-items-center">
                <h6 class="mb-0">Historical Data (Last 1 Hour) - Device ID: {{ selectedDevice?.deviceId }}</h6>
                <button 
                  class="btn btn-sm btn-outline-primary"
                  @click="loadDeviceDetails(selectedDevice?.deviceId)"
                  :disabled="detailLoading"
                >
                  <i class="bi bi-arrow-clockwise" :class="{ 'spinner-border spinner-border-sm': detailLoading }"></i>
                  {{ detailLoading ? '' : 'Refresh' }}
                </button>
              </div>
              <div class="card-body p-0">
                <div v-if="detailLoading" class="text-center py-4">
                  <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                  </div>
                  <p class="text-secondary mt-2">Loading history...</p>
                </div>
                
                <div v-else-if="deviceHistory.length === 0" class="text-center py-4 text-secondary">
                  <i class="bi bi-inbox fs-3"></i>
                  <p class="mt-2">No historical data available</p>
                </div>

                <div v-else class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                  <table class="table table-dark table-striped table-hover mb-0">
                    <thead class="sticky-top bg-dark">
                      <tr>
                        <th>Time</th>
                        <th>Temperature</th>
                        <th>Humidity</th>
                        <th>Pressure</th>
                        <th>Light</th>
                        <th>Noise</th>
                        <th>ToF</th>
                        <th>Angle</th>
                        <th>Weather</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(reading, index) in deviceHistory" :key="index">
                        <td class="text-secondary">{{ reading.time }}</td>
                        <td class="text-warning">{{ formatValue(reading.temperature, '°C') }}</td>
                        <td class="text-info">{{ formatValue(reading.humidity, '%') }}</td>
                        <td class="text-success">{{ formatValue(reading.pressure / 1000, 'kPa') }}</td>
                        <td class="text-warning">{{ formatValue(reading.light, 'lx') }}</td>
                        <td class="text-info">{{ formatValue(reading.noise, 'dB') }}</td>
                        <td class="text-success">{{ formatValue(reading.tof, 'cm') }}</td>
                        <td class="text-primary">{{ formatValue(reading.angle, 'deg') }}</td>
                        <td class="text-light">{{ reading.weather_prediction || '—' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer border-secondary">
            <button type="button" class="btn btn-secondary" @click="closeModal">Close</button>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.row {
  --bs-gutter-x: 1rem;
  --bs-gutter-y: 1rem;
}

.modal {
  display: block;
}

.modal-content {
  animation: modalZoom 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.detail-modal-dialog {
  max-width: min(calc(100vw - 2rem), calc(800px + 10cm));
}

.system-gauge-card {
  padding: 1rem;
  border: 1px solid color-mix(in srgb, var(--gauge-color), transparent 50%);
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.035);
}

.system-gauge {
  width: min(100%, 156px);
  aspect-ratio: 1;
  margin-inline: auto;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background:
    conic-gradient(var(--gauge-color) var(--gauge-fill), rgba(255, 255, 255, 0.12) 0deg),
    radial-gradient(circle, rgba(255, 255, 255, 0.08), transparent 66%);
  box-shadow: 0 0 24px color-mix(in srgb, var(--gauge-color), transparent 78%);
}

.system-gauge-inner {
  width: 72%;
  aspect-ratio: 1;
  border-radius: 50%;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 0.25rem;
  background: #15191f;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}

.system-gauge-inner strong {
  color: #fff;
  font-size: clamp(1.35rem, 4vw, 1.8rem);
  line-height: 1;
}

.system-gauge-icon {
  color: var(--gauge-color);
  font-size: 1.35rem;
  line-height: 1;
}

@keyframes modalZoom {
  from { transform: scale(0.8); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.table-responsive::-webkit-scrollbar {
  width: 8px;
}

.table-responsive::-webkit-scrollbar-track {
  background: #212529;
}

.table-responsive::-webkit-scrollbar-thumb {
  background: #495057;
  border-radius: 4px;
}

.table-responsive::-webkit-scrollbar-thumb:hover {
  background: #6c757d;
}
</style>
