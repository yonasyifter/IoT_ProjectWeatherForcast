// WeatherPage.vue
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const searchQuery = ref('')
const currentLocation = ref('Rende, Calabria, Italy')
const currentTime = ref('')
const loading = ref(false)
const error = ref('')

// Weather data
const weatherData = ref({
  temperature: '—',
  feelsLike: '—',
  condition: '—',
  description: '—',
  airQuality: '—',
  wind: { speed: '—', direction: '—' },
  humidity: '—',
  visibility: '—',
  pressure: '—',
  dewPoint: '— ',
  icon: '☀️'
})

const nearbyLocations = ref([
  { name: 'Robustel Device_id 101', temp: '—' },
  { name: 'Robustel Device_id 102', temp: '—' },
  { name: 'Robustel Device_id 103', temp: '—' },
 
])

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
let timer = null

// Update current time
function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  })
}

// Fetch weather data from API
async function fetchWeatherData() {
  try {
    loading.value = true
    error.value = ''
    
    const res = await fetch(`${API_BASE}/api/weather/forecast/?minutes=60`)
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    const data = await res.json()

    if (Array.isArray(data) && data.length > 0) {
      const latest = data[data.length - 1]
      weatherData.value.temperature = Math.round(latest.temperature * 9/5 + 32) // Convert C to F
      weatherData.value.humidity = latest.humidity
      weatherData.value.pressure = (latest.pressure / 33.864).toFixed(2) // Convert hPa to inHg
    }
  } catch (e) {
    error.value = String(e)
    console.error('Weather fetch error:', e)
  } finally {
    loading.value = false
  }
}

// Search location
function searchLocation() {
  if (searchQuery.value.trim()) {
    currentLocation.value = searchQuery.value.trim()
    searchQuery.value = ''
    fetchWeatherData()
  }
}

function getAirQualityLevel(value) {
  if (value <= 50) return { text: 'Good', color: 'success' }
  if (value <= 100) return { text: 'Moderate', color: 'warning' }
  if (value <= 150) return { text: 'Unhealthy', color: 'danger' }
  return { text: 'Very Unhealthy', color: 'danger' }
}

const airQualityInfo = computed(() => getAirQualityLevel(weatherData.value.airQuality))

onMounted(() => {
  updateTime()
  fetchWeatherData()
  timer = setInterval(() => {
    updateTime()
    fetchWeatherData()
  }, 300000) // Update every 5 minutes
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="min-vh-100" style="background: linear-gradient(to bottom, #f5e6d3 0%, #e8d5c4 100%);">
    <!-- Header -->
    <div class="bg-white border-bottom shadow-sm">
      <div class="container-fluid">
        <div class="row align-items-center py-2">
          <div class="col-md-5">
            <div class="input-group">
              <input 
                v-model="searchQuery"
                @keyup.enter="searchLocation"
                type="text" 
                placeholder="Search for location"
                class="form-control"
              />
              <button @click="searchLocation" class="btn btn-outline-secondary">
                <i class="bi bi-search"></i>
              </button>
            </div>
          </div>
          
          <div class="col-md-5">
            <span class="text-muted">{{ currentLocation }} ☀️ {{ weatherData.temperature }}°</span>
          </div>
          
          <div class="col-md-2 text-end">
            <button class="btn btn-link text-secondary">
              <i class="bi bi-three-dots-vertical fs-5"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Location Header -->
    <div class="container-fluid py-3">
      <div class="d-flex justify-content-between align-items-center">
        <h2 class="h4 mb-0">
          {{ currentLocation }}
          <i class="bi bi-chevron-down"></i>
        </h2>
        <button class="btn btn-light rounded-circle" style="width: 40px; height: 40px;">
          <i class="bi bi-geo-alt-fill"></i>
        </button>
      </div>
    </div>

    <!-- Main Content -->
    <div class="container-fluid">
      <div class="row g-3">
        <!-- Left Column - Weather Details -->
        <div class="col-lg-8">
          <div class="card shadow-sm">
            <div class="card-body">
              <!-- Header -->
              <div class="d-flex justify-content-between align-items-start mb-4">
                <div>
                  <h5 class="card-title mb-1">Current weather</h5>
                  <small class="text-muted">{{ currentTime }}</small>
                </div>
                <a href="#" class="text-decoration-none">
                  <i class="bi bi-chat-dots me-1"></i>
                  <small>Seeing different weather?</small>
                </a>
              </div>

              <!-- Main Temperature Display -->
              <div class="d-flex align-items-center mb-3">
                <span class="display-1 me-3">{{ weatherData.icon }}</span>
                <div class="d-flex align-items-baseline">
                  <span class="display-1 fw-light">{{ weatherData.temperature }}°F</span>
                  <div class="ms-3">
                    <p class="h5 mb-1">{{ weatherData.condition }}</p>
                    <p class="text-muted mb-0">Feels like {{ weatherData.feelsLike }}°</p>
                  </div>
                </div>
              </div>

              <p class="mb-4">{{ weatherData.description }}</p>

              <!-- Weather Details Grid -->
              <div class="border-top pt-3">
                <div class="row g-3">
                  <div class="col-md-4 col-sm-6">
                    <div class="d-flex flex-column">
                      <small class="text-muted mb-1">
                        Air quality <i class="bi bi-info-circle"></i>
                      </small>
                      <div class="d-flex align-items-center">
                        <span :class="`badge bg-${airQualityInfo.color} rounded-circle me-2`" style="width: 12px; height: 12px;"></span>
                        <strong>{{ weatherData.airQuality }}</strong>
                      </div>
                    </div>
                  </div>

                  <div class="col-md-4 col-sm-6">
                    <div class="d-flex flex-column">
                      <small class="text-muted mb-1">
                        Wind <i class="bi bi-info-circle"></i>
                      </small>
                      <strong>
                        {{ weatherData.wind.speed }} mph
                        <i class="bi bi-arrow-down ms-1" style="transform: rotate(-45deg);"></i>
                      </strong>
                    </div>
                  </div>

                  <div class="col-md-4 col-sm-6">
                    <div class="d-flex flex-column">
                      <small class="text-muted mb-1">
                        Humidity <i class="bi bi-info-circle"></i>
                      </small>
                      <strong>{{ weatherData.humidity }}%</strong>
                    </div>
                  </div>

                  <div class="col-md-4 col-sm-6">
                    <div class="d-flex flex-column">
                      <small class="text-muted mb-1">
                        Visibility <i class="bi bi-info-circle"></i>
                      </small>
                      <strong>{{ weatherData.visibility }} mi</strong>
                    </div>
                  </div>

                  <div class="col-md-4 col-sm-6">
                    <div class="d-flex flex-column">
                      <small class="text-muted mb-1">
                        Pressure <i class="bi bi-info-circle"></i>
                      </small>
                      <strong>{{ weatherData.pressure }} in</strong>
                    </div>
                  </div>

                  <div class="col-md-4 col-sm-6">
                    <div class="d-flex flex-column">
                      <small class="text-muted mb-1">
                        Dew point <i class="bi bi-info-circle"></i>
                      </small>
                      <strong>{{ weatherData.dewPoint }}°</strong>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Loading Spinner -->
              <div v-if="loading" class="text-center mt-3">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                  <span class="visually-hidden">Loading...</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column - Map -->
        <div class="col-lg-4">
          <!-- Map Controls -->
          <div class="card shadow-sm mb-3">
            <div class="card-body p-2">
              <div class="btn-group w-100" role="group">
                <button type="button" class="btn btn-warning">
                  <i class="bi bi-droplet-fill"></i>
                </button>
                <button type="button" class="btn btn-outline-secondary">
                  <i class="bi bi-thermometer-half"></i>
                </button>
                <button type="button" class="btn btn-outline-secondary">
                  <i class="bi bi-wind"></i>
                </button>
              </div>
            </div>
          </div>

          <!-- Map Container -->
          <div class="card shadow-sm overflow-hidden">
            <div class="position-relative" style="background: linear-gradient(to bottom, #a8d5f7 0%, #f0f0f0 100%); min-height: 450px;">
              <!-- Nearby Locations -->
              <div class="position-absolute top-0 end-0 m-3">
                <div 
                  v-for="loc in nearbyLocations" 
                  :key="loc.name"
                  class="card shadow-sm mb-2"
                  style="min-width: 140px;"
                >
                  <div class="card-body p-2 d-flex align-items-center">
                    <span class="fs-4 me-2">☀️</span>
                    <div class="flex-grow-1">
                      <small class="d-block fw-bold">{{ loc.name }}</small>
                      <small class="text-muted">{{ loc.temp }}°F</small>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Map Footer -->
            <div class="bg-dark text-white p-3 d-flex justify-content-between align-items-center">
              <small>No precipitation for at least 2 hours</small>
              <button class="btn btn-link btn-sm text-info text-decoration-none">
                Open Map
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error Toast -->
    <div v-if="error" class="position-fixed bottom-0 end-0 p-3" style="z-index: 11">
      <div class="toast show" role="alert">
        <div class="toast-header bg-danger text-white">
          <i class="bi bi-exclamation-triangle me-2"></i>
          <strong class="me-auto">Error</strong>
          <button type="button" class="btn-close btn-close-white" @click="error = ''" aria-label="Close"></button>
        </div>
        <div class="toast-body">
          {{ error }}
        </div>
      </div>
    </div>
  </div>
</template>

