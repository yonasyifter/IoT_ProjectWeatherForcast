<script setup>
import { ref, onMounted } from 'vue'

const temperature = ref('—')
const humidity = ref('—')
const pressure = ref('—')
const deviceId = ref('—')
const observedAt = ref('')
const error = ref('')
const loading = ref(false)

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function loadLatest() {
  try {
    error.value = ''
    loading.value = true
    const res = await fetch(`${API_BASE}/api/weather/forecast/?minutes=60`)
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    const data = await res.json()
  console.log('Fetched data:', data)
    if (!Array.isArray(data) || data.length === 0) {
      temperature.value = '—'
      humidity.value = '—'
      pressure.value = '—'
      deviceId.value = '—'
      observedAt.value = 'No data'
      loading.value = false
      return
    }

    // API returns list sorted ascending by time; take last (most recent)
    const last = data[data.length - 1]
    temperature.value = last.temperature ?? '—'
    humidity.value = last.humidity ?? '—'
    pressure.value = last.pressure ?? '—'
    deviceId.value = last.device_id ?? '—'
    observedAt.value = last.time ? new Date(last.time).toLocaleString() : ''
    loading.value = false
  } catch (err) {
    error.value = String(err)
    loading.value = false
  }
}

onMounted(() => {
  loadLatest()
  // refresh periodically
  setInterval(loadLatest, 15_000)
})

function formatValue(v, unit) {
  if (v === '—' || v === null || v === undefined) return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  return `${n.toFixed(1)} ${unit}`
}
</script>

<template>
  <div class="min-vh-100 d-flex align-items-center">
    <div class="container bg-dark text-white p-8 rounded shadow-lg">
      <div class="row justify-content-center">
        <div class="col-12 col-sm-6 col-md-8 col-lg-12">
          <div class="text-center mb-8">
            <h1 class="display-6 fw-bold">Smart Park Project</h1>
            <p class="text-muted ">Real-time sensor dashboard</p>
          </div>

          <div class="card shadow-lg">
            <div class="card-body">
              <h2 class="card-title fw-bold">Current Sensor Readings</h2>

              <div class="row gy-2">
                <div class="col-6">Temperature</div>
                <div class="col-6 text-end">
                  <div class="display-6 fw-bold">{{ formatValue(temperature, '°C') }}</div>
                </div>

                <div class="col-6">Humidity</div>
                <div class="col-6 text-end">
                  <span class="badge bg-info text-dark fs-6">{{ formatValue(humidity, '%') }}</span>
                </div>

                <div class="col-6">Pressure</div>
                <div class="col-6 text-end">
                  <span class="badge bg-secondary fs-6">{{ formatValue(pressure, 'hPa') }}</span>
                </div>

                <div class="col-6">Device ID</div>
                <div class="col-6 text-end">
                  <span class="text-muted">{{ deviceId }}</span>
                </div>
              </div>

              <div class="mt-3 text-muted small">Observed: {{ observedAt }}</div>
              <div v-if="error" class="mt-2 text-danger small">Error: {{ error }}</div>

              <div class="d-flex justify-content-between align-items-center mt-3">
                <div>
                  <small class="text-muted">Updates every 15s</small>
                </div>
                <div>
                  <button class="btn btn-sm btn-outline-secondary me-2" @click="loadLatest">Refresh</button>
                  <button class="btn btn-sm btn-primary" @click="loadLatest">Reload</button>
                </div>
              </div>

              <div v-if="loading" class="text-center mt-3">
                <div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app {
  max-width: 720px;
  margin: 2rem auto;
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
}

header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.logo { display: block }

.card {
  padding: 1.25rem;
  border-radius: 8px;
  border: 1px solid #e6e6e6;
  background: #fff;
}

.label { color:#666 }
.value { font-weight:700 }
.meta { margin-top:0.75rem; color:#666; font-size:0.9rem }
.error { margin-top:0.5rem; color:#b00 }
</style>
