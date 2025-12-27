// SensorDashboardPage.vue - Updated for Multiple Devices
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import SensorPanel from '../components/sensors/SensorPanel.vue'

const devices = ref([]) // Array to store all device readings
const error = ref('')
const loading = ref(false)
const searchQuery = ref('')

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
let timer = null

async function loadLatest() {
  try {
    error.value = ''
    loading.value = true

    const res = await fetch(`${API_BASE}/api/weather/forecast/?minutes=60`)
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    const data = await res.json()

    if (!Array.isArray(data) || data.length === 0) {
      devices.value = []
      return
    }

    // Group readings by device_id and get the latest reading for each device
    const deviceMap = new Map()
    
    data.forEach(reading => {
      const deviceId = reading.device_id || 'unknown'
      const existingReading = deviceMap.get(deviceId)
      
      // Keep the reading with the most recent timestamp
      if (!existingReading || new Date(reading.time) > new Date(existingReading.time)) {
        deviceMap.set(deviceId, {
          deviceId: deviceId,
          temperature: reading.temperature ?? '—',
          humidity: reading.humidity ?? '—',
          pressure: reading.pressure ?? '—',
          observedAt: reading.time ? new Date(reading.time).toLocaleString() : '—',
          timestamp: reading.time
        })
      }
    })

    // Convert map to array and sort by device_id
    devices.value = Array.from(deviceMap.values()).sort((a, b) => {
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

// Filter devices based on search query
const filteredDevices = computed(() => {
  if (!searchQuery.value.trim()) {
    return devices.value
  }
  const query = searchQuery.value.toLowerCase()
  return devices.value.filter(device => 
    device.deviceId.toLowerCase().includes(query)
  )
})

function handleSearch() {
  // Search is handled by computed property
  console.log('Searching for:', searchQuery.value)
}

function formatValue(v, unit) {
  if (v === '—' || v === null || v === undefined) return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  return `${n.toFixed(1)} ${unit}`
}

onMounted(() => {
  loadLatest()
  timer = setInterval(loadLatest, 15_000)
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
    v-model="activeTab"
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
        </div>

        <div class="d-flex gap-2 flex-shrink-0">
          <button class="btn btn-outline-secondary fw-bold" @click="handleSearch">
            Search
          </button>
          <button class="btn btn-outline-primary fw-bold" @click="loadLatest">
            <i class="bi bi-arrow-clockwise me-1"></i>
            Refresh All
          </button>
        </div>

        <div class="ms-auto text-secondary">
          <strong>{{ filteredDevices.length }}</strong> device{{ filteredDevices.length !== 1 ? 's' : '' }} found
        </div>
      </div>
    </template>

    <!-- Loading State -->
    <div v-if="loading && devices.length === 0" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="text-secondary mt-3">Loading device data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-danger m-3" role="alert">
      <i class="bi bi-exclamation-triangle me-2"></i>
      <strong>Error:</strong> {{ error }}
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredDevices.length === 0" class="text-center py-5">
      <i class="bi bi-inbox fs-1 text-secondary"></i>
      <p class="text-secondary mt-3">
        {{ searchQuery ? 'No devices found matching your search' : 'No device data available' }}
      </p>
      <button class="btn btn-primary mt-2" @click="loadLatest">
        <i class="bi bi-arrow-clockwise me-1"></i>
        Reload Data
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
          :device-id="device.deviceId"
          :observed-at="device.observedAt"
          :loading="loading"
          :error="error"
          :format-value="formatValue"
          @refresh="loadLatest"
        />
      </div>
    </div>

    <!-- Refresh Indicator -->
    <div v-if="loading && devices.length > 0" class="position-fixed bottom-0 end-0 m-3">
      <div class="bg-primary text-white px-3 py-2 rounded shadow">
        <div class="spinner-border spinner-border-sm me-2" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        Updating...
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.row {
  --bs-gutter-x: 1rem;
  --bs-gutter-y: 1rem;
}
</style>