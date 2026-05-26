<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import api from '@/utils/api.js'

const alerts = ref([])
const loading = ref(false)
const deletingIds = ref(new Set())
const error = ref('')
let refreshTimer = null

const totals = computed(() => ({
  all: alerts.value.length,
  critical: alerts.value.filter(alert => alert.alert_type === 'critical').length,
  warning: alerts.value.filter(alert => alert.alert_type === 'warning').length,
}))

async function fetchAlerts() {
  loading.value = true
  error.value = ''

  try {
    const data = await api.get('/api/weather/alert?limit=100')
    alerts.value = Array.isArray(data) ? data : []
  } catch (err) {
    error.value = err.message || 'Failed to load digital twin alerts'
  } finally {
    loading.value = false
  }
}

async function deleteAlert(alert) {
  if (!alert?.id) return
  const confirmed = window.confirm('Delete this digital twin alert?')
  if (!confirmed) return

  deletingIds.value = new Set([...deletingIds.value, alert.id])
  error.value = ''

  try {
    await api.delete(`/api/weather/alert/${alert.id}`)
    alerts.value = alerts.value.filter(item => item.id !== alert.id)
    window.dispatchEvent(new CustomEvent('digital-alerts-updated'))
  } catch (err) {
    error.value = err.message || 'Failed to delete alert'
  } finally {
    const nextDeletingIds = new Set(deletingIds.value)
    nextDeletingIds.delete(alert.id)
    deletingIds.value = nextDeletingIds
  }
}

function alertClass(type) {
  return type === 'critical' ? 'danger' : 'warning'
}

function alertLabel(type) {
  return type === 'critical' ? 'Critical' : 'Warning'
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
        :class="`is-${alertClass(alert.alert_type)}`"
      >
        <div class="alert-topline">
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <span class="device-chip">
              <i class="bi bi-hdd-network me-1"></i>
              Device {{ alert.device_id || 'unknown' }}
            </span>
            <span class="badge" :class="`text-bg-${alertClass(alert.alert_type)}`">
              {{ alertLabel(alert.alert_type) }}
            </span>
            <span class="text-secondary small">{{ formatDate(alert.time || alert.created_at) }}</span>
          </div>

          <button
            class="btn btn-sm btn-outline-danger ms-auto"
            :disabled="deletingIds.has(alert.id)"
            @click="deleteAlert(alert)"
            title="Delete alert"
          >
            <span v-if="deletingIds.has(alert.id)" class="spinner-border spinner-border-sm me-1"></span>
            <i v-else class="bi bi-trash me-1"></i>
            Delete
          </button>
        </div>

        <p class="mb-2">{{ alert.description || 'Significant device data change detected.' }}</p>

        <div class="table-responsive">
          <table class="table table-sm table-dark mb-0 align-middle">
            <thead>
              <tr>
                <th>Parameter</th>
                <th>Previous</th>
                <th>Current</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="change in alert.change_for_alert" :key="`${alert.id}-${change.parameter}`">
                <td class="font-monospace text-info">{{ change.parameter }}</td>
                <td>{{ formatValue(change.previous_value) }}</td>
                <td class="fw-semibold">{{ formatValue(change.current_value) }}</td>
              </tr>
            </tbody>
          </table>
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

th,
td {
  white-space: nowrap;
}
</style>
