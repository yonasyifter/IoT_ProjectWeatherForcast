<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import api from '@/utils/api.js'

const alerts = ref([])
const loading = ref(false)
const deletingIds = ref(new Set())
const error = ref('')
const dismissedIds = ref(new Set(JSON.parse(localStorage.getItem('dismissedDigitalTwinAlerts') || '[]')))
let refreshTimer = null

const totals = computed(() => ({
  all: alerts.value.length,
  critical: alerts.value.filter(alert => alert.status === 'pending').length,
  warning: alerts.value.filter(alert => alert.status === 'updated').length,
}))

const pendingAlerts = computed(() => alerts.value.filter(alert => alert.status === 'pending'))

async function fetchAlerts() {
  loading.value = true
  error.value = ''

  try {
    const data = await api.get('/api/weather/digital-twin/alerts?limit=100')
    const digitalTwinAlerts = Array.isArray(data) ? data : []
    alerts.value = digitalTwinAlerts.filter(alert => !dismissedIds.value.has(alert.id))
  } catch (err) {
    error.value = err.message || 'Failed to load digital twin alerts'
  } finally {
    loading.value = false
  }
}

async function deleteAlert(alert) {
  if (!alert?.id) return
  deletingIds.value = new Set([...deletingIds.value, alert.id])
  error.value = ''

  try {
    const params = new URLSearchParams({
      time: alert.delete_time || alert.time,
      device_id: alert.device_id || '',
    })

    await api.delete(`/api/weather/digital-twin/alerts/${encodeURIComponent(alert.id)}?${params.toString()}`)
    dismissedIds.value = new Set([...dismissedIds.value, alert.id])
    localStorage.setItem('dismissedDigitalTwinAlerts', JSON.stringify([...dismissedIds.value]))
    alerts.value = alerts.value.filter(item => item.id !== alert.id)
    window.dispatchEvent(new CustomEvent('digital-alerts-updated'))
  } catch (err) {
    error.value = err.message || 'Failed to delete digital twin alert from InfluxDB'
  } finally {
    const nextDeletingIds = new Set(deletingIds.value)
    nextDeletingIds.delete(alert.id)
    deletingIds.value = nextDeletingIds
  }
}

function alertClass(type) {
  return type === 'critical' ? 'danger' : 'warning'
}

function alertLabel(alert) {
  if (alert.status === 'updated') return 'Gateway updated'
  if (alert.status === 'pending') return 'Awaiting gateway'
  return 'Digital twin'
}

function formatValue(value) {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
}

function desiredRows(alert) {
  const desired = alert.desired_properties || {}
  return [
    { label: 'Sampling rate', value: desired.sampling_rate_s, unit: 's' },
  ]
}

function ackSamplingRate(alert) {
  const measurement = alert.digital_twin_measurement || alert.acknowledgement || {}
  return alert.gateway_sampling_rate ?? measurement.sampling_rate_s ?? measurement.sampling_s ?? alert.change_for_alert?.[0]?.ack_value
}

function confirmationTime(alert) {
  return alert.gateway_measurement_time || alert.ack_time
}

function confirmationLabel(alert) {
  return 'Gateway measurement confirms the desired properties'
}

onMounted(() => {
  fetchAlerts()
  refreshTimer = setInterval(fetchAlerts, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<template>
  <section class="digital-alerts">
    <div class="d-flex justify-content-between align-items-center gap-3 flex-wrap mb-3">
      <div>
        <h2 class="h5 mb-1">Digital Twin Alerts</h2>
        <p class="text-secondary small mb-0">Live announcements sent by the digital twin.</p>
      </div>

      <button class="btn btn-sm btn-outline-light" :disabled="loading" @click="fetchAlerts">
        <i class="bi bi-arrow-clockwise me-1"></i>
        Refresh
      </button>
    </div>

    <div class="d-flex gap-2 flex-wrap mb-3">
      <span class="alert-stat text-info">{{ totals.all }} total</span>
      <span class="alert-stat alert-stat-critical">{{ totals.critical }} critical</span>
      <span class="alert-stat alert-stat-warning">{{ totals.warning }} warning</span>
    </div>

    <div v-if="error" class="alert alert-danger">
      <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
    </div>

    <div v-if="pendingAlerts.length" class="gateway-warning mb-3">
      <i class="bi bi-exclamation-triangle-fill"></i>
      <span>
        {{ pendingAlerts.length }} gateway update{{ pendingAlerts.length === 1 ? '' : 's' }} not reflected in gateway telemetry.
      </span>
    </div>

    <div v-if="loading && alerts.length === 0" class="text-center py-5 text-secondary">
      <div class="spinner-border text-info mb-2"></div>
      <div>Loading alerts...</div>
    </div>

    <div v-else-if="alerts.length === 0" class="empty-state text-center py-5">
      <i class="bi bi-bell-slash fs-1"></i>
      <p class="mt-2 mb-0">No digital twin alerts received yet.</p>
    </div>

    <div v-else class="alert-list">
      <article
        v-for="alert in alerts"
        :key="alert.id"
        class="alert-row"
        :class="`is-${alert.status === 'pending' ? 'danger' : alertClass(alert.alert_type)}`"
      >
        <button
          class="dismiss-btn"
          :disabled="deletingIds.has(alert.id)"
          @click="deleteAlert(alert)"
          title="Delete notification"
          aria-label="Delete notification"
        >
          <span v-if="deletingIds.has(alert.id)" class="spinner-border spinner-border-sm"></span>
          <i v-else class="bi bi-x-lg"></i>
        </button>

        <div class="alert-topline">
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <span class="device-chip">
              <i class="bi bi-hdd-network me-1"></i>
              Device {{ alert.device_id || 'unknown' }}
            </span>
            <span
              class="badge"
              :class="alert.status === 'pending' ? 'text-bg-danger' : `text-bg-${alertClass(alert.alert_type)}`"
            >
              {{ alertLabel(alert) }}
            </span>
            <span class="text-secondary small">{{ formatDate(alert.time || alert.created_at) }}</span>
          </div>

        </div>

        <p class="mb-2 pe-4">{{ alert.description || 'Significant device data change detected.' }}</p>

        <div class="digital-twin-body">
          <div class="desired-grid">
            <div v-for="row in desiredRows(alert)" :key="`${alert.id}-${row.label}`" class="desired-item">
              <span>{{ row.label }}</span>
              <strong>{{ formatValue(row.value) }}{{ row.unit ? ` ${row.unit}` : '' }}</strong>
            </div>
          </div>

          <div class="ack-card" :class="alert.status === 'updated' ? 'ack-ok' : 'ack-pending'">
            <i :class="alert.status === 'updated' ? 'bi bi-check-circle-fill' : 'bi bi-clock-history'"></i>
            <div>
              <strong>
                {{ alert.status === 'updated' ? confirmationLabel(alert) : 'Gateway measurement confirmation missing' }}
              </strong>
              <p class="mb-0">
                <template v-if="alert.status === 'updated'">
                  Gateway sampling updated to the new rate: {{ formatValue(ackSamplingRate(alert)) }} s on {{ formatDate(confirmationTime(alert)) }}.
                </template>
                <template v-else>
                  Gateway telemetry does not match the digital twin sampling value. The gateway may be out of reach or without internet.
                </template>
              </p>
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.digital-alerts {
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

.empty-state {
  background: rgba(255, 255, 255, 0.04);
  border: 1px dashed rgba(255, 255, 255, 0.14);
  border-radius: 8px;
  color: #94a3b8;
}

.gateway-warning {
  align-items: center;
  background: rgba(220, 53, 69, 0.16);
  border: 1px solid rgba(220, 53, 69, 0.45);
  border-radius: 8px;
  color: #ffb3bd;
  display: flex;
  gap: 0.65rem;
  padding: 0.75rem 0.9rem;
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
  position: relative;
}

.alert-row.is-danger {
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

.dismiss-btn {
  align-items: center;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(248, 113, 113, 0.5);
  border-radius: 50%;
  color: #fecdd3;
  display: inline-flex;
  height: 2rem;
  justify-content: center;
  position: absolute;
  right: 0.75rem;
  top: 0.75rem;
  width: 2rem;
}

.dismiss-btn:hover {
  background: rgba(220, 53, 69, 0.24);
  color: #ffffff;
}

.digital-twin-body {
  display: grid;
  gap: 0.75rem;
}

.desired-grid {
  display: grid;
  gap: 0.65rem;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.desired-item {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 8px;
  display: grid;
  gap: 0.25rem;
  min-height: 4.25rem;
  padding: 0.75rem;
}

.desired-item span {
  color: #94a3b8;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
}

.desired-item strong {
  color: #f8fafc;
  font-size: 1.05rem;
}

.ack-card {
  align-items: flex-start;
  border-radius: 8px;
  display: flex;
  gap: 0.7rem;
  padding: 0.8rem;
}

.ack-card strong {
  display: block;
  margin-bottom: 0.2rem;
}

.ack-card p {
  color: #cbd5e1;
}

.ack-ok {
  background: rgba(25, 135, 84, 0.16);
  border: 1px solid rgba(25, 135, 84, 0.45);
  color: #86efac;
}

.ack-pending {
  background: rgba(220, 53, 69, 0.14);
  border: 1px solid rgba(220, 53, 69, 0.45);
  color: #fca5a5;
}

th,
td {
  white-space: nowrap;
}
</style>
