<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import api from '@/utils/api.js'
import DigitalTwinAlert from './digitalTwinAlert.vue'

const STORAGE_KEY = 'digitalTwinAlertStandards'
const measurement = 'Sensor_S6000U_data_GSP2'

const forecast = ref([])
const loading = ref(false)
const error = ref('')
const thresholdModalOpen = ref(false)
const currentTime = ref(Date.now())
let clockTimer = null

const defaultStandards = {
  temperatureWarningMin: 27,
  temperatureCriticalMin: 37,
  humidityWarningMin: 65,
  humidityCriticalMin: 80,
  pressureWarningMin: 101000,
  pressureCriticalMin: 103000,
  cpuWarningMin: 50,
  cpuCriticalMin: 61,
  storageWarningFreeGb: 4,
  storageCriticalFreeGb: 2,
  ramWarningFreeMb: 500,
  ramCriticalFreeMb: 250,
  noiseWarningConditions: 'noisy',
  noiseCriticalConditions: '',
  gpsWarningStatuses: 'Moving',
  gpsCriticalStatuses: '',
  monitoredDeviceIds: '101',
  deviceNoReportWarningMinutes: 10,
  deviceNoReportCriticalMinutes: 20,
}

const standards = ref(loadStandards())
const draftStandards = ref({ ...standards.value })

function loadStandards() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
    return { ...defaultStandards, ...saved }
  } catch {
    return { ...defaultStandards }
  }
}

const latestReadings = computed(() => {
  const latestByDevice = new Map()

  forecast.value.forEach((reading) => {
    if (!reading?.time) return
    const deviceId = String(reading.device_id || 'unknown')
    const current = latestByDevice.get(deviceId)

    if (!current || new Date(reading.time) > new Date(current.time)) {
      latestByDevice.set(deviceId, { ...reading, device_id: deviceId })
    }
  })

  return Array.from(latestByDevice.values()).sort((a, b) =>
    String(a.device_id).localeCompare(String(b.device_id), undefined, { numeric: true })
  )
})

const standardAlerts = computed(() => {
  return [
    ...buildDeviceConditionAlerts(),
    ...latestReadings.value.flatMap((reading) => buildAlertsForReading(reading)),
  ]
})

const alertTotals = computed(() => ({
  all: standardAlerts.value.length,
  critical: standardAlerts.value.filter(alert => alert.level === 'critical').length,
  warning: standardAlerts.value.filter(alert => alert.level === 'warning').length,
}))

async function fetchForecast() {
  loading.value = true
  error.value = ''

  try {
    const data = await api.get(`/api/weather/forecast/?minutes=60&measurement=${measurement}`)
    forecast.value = Array.isArray(data) ? data : []
  } catch (err) {
    error.value = err.message || 'Failed to load forecast data'
  } finally {
    loading.value = false
  }
}

function buildAlertsForReading(reading) {
  const alerts = []

  addHighRangeAlert(alerts, reading, 'temperature', 'Temperature', 'C',
    standards.value.temperatureWarningMin, standards.value.temperatureCriticalMin)
  addHighRangeAlert(alerts, reading, 'humidity', 'Humidity', '%',
    standards.value.humidityWarningMin, standards.value.humidityCriticalMin)
  addHighRangeAlert(alerts, reading, 'pressure', 'Pressure', 'Pa',
    standards.value.pressureWarningMin, standards.value.pressureCriticalMin)
  addHighRangeAlert(alerts, reading, 'EG5120_CPU_Temprature', 'CPU Temperature', 'C',
    standards.value.cpuWarningMin, standards.value.cpuCriticalMin)

  addLowAlert(alerts, reading, 'EG5120_Storage_free', 'Storage Free', 'GB',
    standards.value.storageWarningFreeGb, standards.value.storageCriticalFreeGb, parseStorageGb)
  addLowAlert(alerts, reading, 'EG5120_RAM_free_mb', 'RAM Free', 'MB',
    standards.value.ramWarningFreeMb, standards.value.ramCriticalFreeMb, toNumber)

  addStatusAlert(alerts, reading, 'noise_condition', 'Noise Condition',
    standards.value.noiseWarningConditions, standards.value.noiseCriticalConditions)
  addStatusAlert(alerts, reading, 'GPS_status', 'GPS Status',
    standards.value.gpsWarningStatuses, standards.value.gpsCriticalStatuses)

  return alerts
}

function buildDeviceConditionAlerts() {
  const monitoredDeviceIds = parseList(standards.value.monitoredDeviceIds)
  if (monitoredDeviceIds.length === 0) return []

  const latestByDevice = new Map(
    latestReadings.value.map((reading) => [String(reading.device_id).toLowerCase(), reading])
  )

  return monitoredDeviceIds
    .map((deviceId) => {
      const reading = latestByDevice.get(deviceId)

      if (!reading?.time) {
        return makeDeviceConditionAlert(deviceId, 'critical', null, 'no report found in fetched data')
      }

      const ageMinutes = (currentTime.value - new Date(reading.time).getTime()) / 60000
      if (!Number.isFinite(ageMinutes)) return null

      if (ageMinutes >= Number(standards.value.deviceNoReportCriticalMinutes)) {
        return makeDeviceConditionAlert(
          reading.device_id,
          'critical',
          ageMinutes,
          `not reporting for ${formatMinutes(ageMinutes)}, critical after ${standards.value.deviceNoReportCriticalMinutes} minutes`,
          reading.time
        )
      }

      if (ageMinutes >= Number(standards.value.deviceNoReportWarningMinutes)) {
        return makeDeviceConditionAlert(
          reading.device_id,
          'warning',
          ageMinutes,
          `not reporting for ${formatMinutes(ageMinutes)}, warning after ${standards.value.deviceNoReportWarningMinutes} minutes`,
          reading.time
        )
      }

      return null
    })
    .filter(Boolean)
}

function addHighRangeAlert(alerts, reading, field, label, unit, warningMin, criticalMin) {
  const value = toNumber(reading[field])
  if (value === null) return

  if (value > Number(criticalMin)) {
    alerts.push(makeAlert(reading, field, label, 'critical', value, unit, `above critical standard ${criticalMin}`))
  } else if (value > Number(warningMin) && value < Number(criticalMin)) {
    alerts.push(makeAlert(reading, field, label, 'warning', value, unit, `between warning ${warningMin} and critical ${criticalMin}`))
  }
}

function addLowAlert(alerts, reading, field, label, unit, warningMax, criticalMax, parser) {
  const value = parser(reading[field])
  if (value === null) return

  if (value < Number(criticalMax)) {
    alerts.push(makeAlert(reading, field, label, 'critical', value, unit, `below critical standard ${criticalMax}`))
  } else if (value < Number(warningMax)) {
    alerts.push(makeAlert(reading, field, label, 'warning', value, unit, `below warning standard ${warningMax}`))
  }
}

function addStatusAlert(alerts, reading, field, label, warningList, criticalList) {
  const value = reading[field]
  if (value === null || value === undefined || value === '') return

  const normalizedValue = String(value).trim().toLowerCase()
  const criticalValues = parseList(criticalList)
  const warningValues = parseList(warningList)

  if (criticalValues.includes(normalizedValue)) {
    alerts.push(makeAlert(reading, field, label, 'critical', value, '', 'matches a critical status'))
  } else if (warningValues.includes(normalizedValue)) {
    alerts.push(makeAlert(reading, field, label, 'warning', value, '', 'matches a warning status'))
  }
}

function makeAlert(reading, parameter, label, level, value, unit, reason) {
  return {
    id: `${reading.device_id}-${parameter}-${level}`,
    device_id: reading.device_id,
    time: reading.time,
    parameter,
    label,
    level,
    value,
    unit,
    reason,
  }
}

function makeDeviceConditionAlert(deviceId, level, ageMinutes, reason, time = null) {
  return {
    id: `${deviceId}-device_condition-${level}`,
    device_id: deviceId,
    time,
    parameter: 'device_condition',
    label: 'Device Condition',
    level,
    value: ageMinutes === null ? 'No data' : `${formatMinutes(ageMinutes)} silent`,
    unit: '',
    reason,
  }
}

function parseList(value) {
  return String(value || '')
    .split(',')
    .map(item => item.trim().toLowerCase())
    .filter(Boolean)
}

function parseStorageGb(value) {
  if (value === null || value === undefined || value === '') return null
  const raw = String(value).trim().toLowerCase()
  const numeric = Number.parseFloat(raw)
  if (Number.isNaN(numeric)) return null
  if (raw.endsWith('mb') || raw.endsWith('m')) return numeric / 1024
  return numeric
}

function toNumber(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isNaN(number) ? null : number
}

function formatValue(value, unit = '') {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'number') return `${Number(value.toFixed(2))}${unit ? ` ${unit}` : ''}`
  return `${value}${unit ? ` ${unit}` : ''}`
}

function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
}

function formatMinutes(value) {
  return `${Math.floor(value)} min`
}

function resetStandards() {
  draftStandards.value = { ...defaultStandards }
}

function openThresholdModal() {
  draftStandards.value = { ...standards.value }
  thresholdModalOpen.value = true
}

function closeThresholdModal() {
  thresholdModalOpen.value = false
}

function saveStandards() {
  standards.value = { ...draftStandards.value }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(standards.value))
  thresholdModalOpen.value = false
}

onMounted(() => {
  fetchForecast()
  clockTimer = setInterval(() => {
    currentTime.value = Date.now()
  }, 60000)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<template>
  <main class="alerts-page">
    <div class="container-fluid py-4">
      <div class="d-flex justify-content-between align-items-center gap-3 flex-wrap mb-4">
        <div>
          <h1 class="h4 mb-1">Weather Alert Center</h1>
          <p class="text-secondary mb-0">Admin standards, computed alerts, and digital twin announcements.</p>
        </div>

        <div class="d-flex align-items-center gap-2">
          <button
            class="btn btn-sm btn-outline-warning threshold-button"
            title="Alert thresholds"
            aria-label="Alert thresholds"
            @click="openThresholdModal"
          >
            <i class="bi bi-sliders"></i>
          </button>

          <button class="btn btn-sm btn-outline-light" :disabled="loading" @click="fetchForecast">
            <i class="bi bi-cloud-arrow-down me-1"></i>
            Refresh Data
          </button>
        </div>
      </div>

      <div v-if="error" class="alert alert-danger">
        <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
      </div>

      <div class="row g-3">
        <div class="col-xl-6">
          <section class="context-panel">
            <div class="d-flex justify-content-between align-items-center gap-2 flex-wrap mb-3">
              <div>
                <h2 class="h5 mb-1">Alerts From Admin Standards</h2>
                <p class="text-secondary small mb-0">Computed from the latest reading of each device.</p>
              </div>
              <span class="badge text-bg-secondary">{{ forecast.length }} readings</span>
            </div>

            <div class="d-flex gap-2 flex-wrap mb-3">
              <span class="alert-stat text-info">{{ alertTotals.all }} total</span>
              <span class="alert-stat alert-stat-critical">{{ alertTotals.critical }} critical</span>
              <span class="alert-stat alert-stat-warning">{{ alertTotals.warning }} warning</span>
            </div>

            <div v-if="loading && standardAlerts.length === 0" class="text-center py-5 text-secondary">
              <div class="spinner-border text-info mb-2"></div>
              <div>Evaluating device readings...</div>
            </div>

            <div v-else-if="standardAlerts.length === 0" class="empty-state text-center py-5">
              <i class="bi bi-check-circle fs-1"></i>
              <p class="mt-2 mb-0">No reading violates the current admin standards.</p>
            </div>

            <div v-else class="alert-list">
              <article
                v-for="alert in standardAlerts"
                :key="alert.id"
                class="alert-row"
                :class="`is-${alert.level}`"
              >
                <div class="alert-topline">
                  <span class="device-chip">
                    <i class="bi bi-hdd-network me-1"></i>
                    Device {{ alert.device_id }}
                  </span>
                  <span class="badge" :class="alert.level === 'critical' ? 'text-bg-danger' : 'text-bg-warning'">
                    {{ alert.level === 'critical' ? 'Critical' : 'Warning' }}
                  </span>
                  <span class="text-secondary small">{{ formatDate(alert.time) }}</span>
                </div>

                <div class="table-responsive">
                  <table class="table table-sm table-dark mb-0 align-middle">
                    <thead>
                      <tr>
                        <th>Parameter</th>
                        <th>Current Value</th>
                        <th>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td class="font-monospace text-info">{{ alert.parameter }}</td>
                        <td class="fw-semibold">{{ formatValue(alert.value, alert.unit) }}</td>
                        <td>{{ alert.reason }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </article>
            </div>
          </section>
        </div>

        <div class="col-xl-6">
          <DigitalTwinAlert />
        </div>
      </div>
    </div>

    <div
      v-if="thresholdModalOpen"
      class="threshold-modal-backdrop"
      role="presentation"
      @click.self="closeThresholdModal"
    >
      <form class="threshold-modal" role="dialog" aria-modal="true" @submit.prevent="saveStandards">
        <header class="threshold-modal-header">
          <div>
            <h2 class="h5 mb-1">Alert Thresholds</h2>
            <p class="text-secondary small mb-0">Set warning and critical standards for computed alerts.</p>
          </div>

          <button type="button" class="btn btn-sm btn-outline-light" aria-label="Close" @click="closeThresholdModal">
            <i class="bi bi-x-lg"></i>
          </button>
        </header>

        <div class="standards-grid threshold-modal-body">
          <label>
            <span>Temperature warning above</span>
            <input v-model.number="draftStandards.temperatureWarningMin" type="number" class="form-control form-control-sm" />
          </label>
          <label>
            <span>Temperature critical above</span>
            <input v-model.number="draftStandards.temperatureCriticalMin" type="number" class="form-control form-control-sm" />
          </label>
          <label>
            <span>Humidity warning above</span>
            <input v-model.number="draftStandards.humidityWarningMin" type="number" class="form-control form-control-sm" />
          </label>
          <label>
            <span>Humidity critical above</span>
            <input v-model.number="draftStandards.humidityCriticalMin" type="number" class="form-control form-control-sm" />
          </label>
          <label>
            <span>Pressure warning above</span>
            <input v-model.number="draftStandards.pressureWarningMin" type="number" class="form-control form-control-sm" />
          </label>
          <label>
            <span>Pressure critical above</span>
            <input v-model.number="draftStandards.pressureCriticalMin" type="number" class="form-control form-control-sm" />
          </label>
          <label>
            <span>CPU warning above</span>
            <input v-model.number="draftStandards.cpuWarningMin" type="number" class="form-control form-control-sm" />
          </label>
          <label>
            <span>CPU critical above</span>
            <input v-model.number="draftStandards.cpuCriticalMin" type="number" class="form-control form-control-sm" />
          </label>
          <label>
            <span>Storage warning below GB</span>
            <input v-model.number="draftStandards.storageWarningFreeGb" type="number" step="0.1" class="form-control form-control-sm" />
          </label>
          <label>
            <span>Storage critical below GB</span>
            <input v-model.number="draftStandards.storageCriticalFreeGb" type="number" step="0.1" class="form-control form-control-sm" />
          </label>
          <label>
            <span>RAM warning below MB</span>
            <input v-model.number="draftStandards.ramWarningFreeMb" type="number" class="form-control form-control-sm" />
          </label>
          <label>
            <span>RAM critical below MB</span>
            <input v-model.number="draftStandards.ramCriticalFreeMb" type="number" class="form-control form-control-sm" />
          </label>
          <label>
            <span>Noise warning statuses</span>
            <input v-model="draftStandards.noiseWarningConditions" class="form-control form-control-sm" placeholder="noisy" />
          </label>
          <label>
            <span>Noise critical statuses</span>
            <input v-model="draftStandards.noiseCriticalConditions" class="form-control form-control-sm" placeholder="very noisy" />
          </label>
          <label>
            <span>GPS warning statuses</span>
            <input v-model="draftStandards.gpsWarningStatuses" class="form-control form-control-sm" placeholder="Moving" />
          </label>
          <label>
            <span>GPS critical statuses</span>
            <input v-model="draftStandards.gpsCriticalStatuses" class="form-control form-control-sm" />
          </label>
          <label>
            <span>Monitored device IDs</span>
            <input v-model="draftStandards.monitoredDeviceIds" class="form-control form-control-sm" placeholder="101, 102" />
          </label>
          <label>
            <span>No report warning minutes</span>
            <input v-model.number="draftStandards.deviceNoReportWarningMinutes" type="number" min="1" class="form-control form-control-sm" />
          </label>
          <label>
            <span>No report critical minutes</span>
            <input v-model.number="draftStandards.deviceNoReportCriticalMinutes" type="number" min="1" class="form-control form-control-sm" />
          </label>
        </div>

        <footer class="threshold-modal-footer">
          <button type="button" class="btn btn-sm btn-outline-secondary" @click="resetStandards">
            <i class="bi bi-arrow-counterclockwise me-1"></i>
            Reset
          </button>
          <div class="d-flex gap-2">
            <button type="button" class="btn btn-sm btn-outline-light" @click="closeThresholdModal">Cancel</button>
            <button type="submit" class="btn btn-sm btn-warning">
              <i class="bi bi-check-lg me-1"></i>
              Save
            </button>
          </div>
        </footer>
      </form>
    </div>
  </main>
</template>

<style scoped>
.alerts-page {
  background: #0b1220;
  min-height: calc(100vh - 58px);
  color: #f8fafc;
}

.context-panel {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 8px;
  padding: 1rem;
}

.threshold-button {
  height: 32px;
  width: 36px;
}

.threshold-modal-backdrop {
  align-items: center;
  background: rgba(2, 6, 23, 0.72);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: 1rem;
  position: fixed;
  z-index: 2000;
}

.threshold-modal {
  background: #111827;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.45);
  color: #f8fafc;
  max-height: min(760px, calc(100vh - 2rem));
  max-width: 980px;
  overflow: hidden;
  width: min(980px, 100%);
}

.threshold-modal-header,
.threshold-modal-footer {
  align-items: center;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  padding: 1rem;
}

.threshold-modal-header {
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.threshold-modal-body {
  max-height: min(520px, calc(100vh - 190px));
  overflow-y: auto;
  padding: 1rem;
}

.threshold-modal-footer {
  border-top: 1px solid rgba(148, 163, 184, 0.16);
}

.standards-grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
}

.standards-grid label {
  display: grid;
  gap: 0.35rem;
}

.standards-grid span {
  color: #94a3b8;
  font-size: 0.76rem;
  font-weight: 600;
  text-transform: uppercase;
}

.standards-grid input {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.35);
  color: #f8fafc;
}

.alert-stat {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  font-size: 0.875rem;
  padding: 0.45rem 0.7rem;
}

.alert-stat-critical {
  background: rgba(220, 53, 69, 0.18);
  border-color: rgba(220, 53, 69, 0.45);
  color: #ff8b9a;
}

.alert-stat-warning {
  background: rgba(255, 193, 7, 0.2);
  border-color: rgba(255, 193, 7, 0.5);
  color: #ffd75e;
}

.empty-state {
  background: rgba(255, 255, 255, 0.04);
  border: 1px dashed rgba(255, 255, 255, 0.14);
  border-radius: 8px;
  color: #94a3b8;
}

.alert-list {
  display: grid;
  gap: 0.75rem;
}

.alert-row {
  background: rgba(15, 23, 42, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-left-width: 4px;
  border-radius: 8px;
  padding: 1rem;
}

.alert-row.is-critical {
  border-left-color: #dc3545;
}

.alert-row.is-warning {
  border-left-color: #ffc107;
}

.alert-topline {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-bottom: 0.65rem;
}

.device-chip {
  background: rgba(14, 165, 233, 0.16);
  border: 1px solid rgba(14, 165, 233, 0.42);
  border-radius: 999px;
  color: #7dd3fc;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.82rem;
  font-weight: 700;
  padding: 0.25rem 0.65rem;
}

th,
td {
  white-space: nowrap;
}
</style>
