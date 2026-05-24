<script setup>
import { ref, onMounted } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import { rcmsApi } from '../services/rcmsApi.js'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const loading   = ref(false)
const error     = ref('')
const alerts    = ref([])
const groups    = ref([])
const devices   = ref([])
const loaded     = ref(false)

// Filters
const mode        = ref('device')   // 'device' | 'group'
const selectedSn  = ref('')
const selectedGid = ref('')
const pageNum     = ref(1)
const pageSize    = ref(20)

// Default last 7 days
const now = Date.now()
const beginTime = ref(now - 7 * 24 * 60 * 60 * 1000)
const endTime   = ref(now)

async function init() {
  try {
    const [grps, devs] = await Promise.all([
      rcmsApi.getGroups().catch(() => []),
      rcmsApi.getDevices(1, 50).catch(() => []),
    ])
    const apiGroups = Array.isArray(grps) ? grps : (grps?.list || grps?.records || [])
    const devArr  = Array.isArray(devs) ? devs : (devs?.list || devs?.records || [])
    devices.value = devArr
    if (devArr.length) selectedSn.value = devArr[0].sn
    const deviceGroups = devArr
      .map(d => ({
        groupId: d.groupId || d.deviceGroupId,
        groupName: d.groupName || d.deviceGroup,
      }))
      .filter(g => g.groupId)
    const mergedGroups = [...apiGroups, ...deviceGroups]
    groups.value = Array.from(
      new Map(mergedGroups.map(g => [g.groupId || g.id, g])).values()
    )
    if (groups.value.length) selectedGid.value = groups.value[0].groupId || groups.value[0].id
  } catch(e) { error.value = e.message }
}

function unwrapAlerts(data) {
  return Array.isArray(data) ? data : (data?.list || data?.records || data?.data || [])
}

function normalizeAlert(alert, fallbackSn = '') {
  return {
    ...alert,
    sn: alert.sn || alert.deviceSn || alert.deviceSN || fallbackSn,
    time: alert.time || alert.alertTime || alert.createTime || alert.timestamp || alert.updateTime,
    type: alert.alertType || alert.type || alert.alertName || alert.name || alert.eventType,
    level: alert.level || alert.alertLevel || alert.severity || alert.alarmLevel,
    message: alert.alertMsg || alert.message || alert.content || alert.details || alert.description || alert.alarmContent,
    status: alert.status ?? alert.alertStatus ?? alert.state,
  }
}

async function loadAlerts() {
  loading.value = true
  error.value   = ''
  alerts.value  = []
  loaded.value   = false
  try {
    const params = { pageNum: pageNum.value, pageSize: pageSize.value, beginTime: beginTime.value, endTime: endTime.value }
    let data
    if (mode.value === 'device' && selectedSn.value) {
      data = await rcmsApi.getDeviceAlertLogs(selectedSn.value, params)
      alerts.value = unwrapAlerts(data).map(a => normalizeAlert(a, selectedSn.value))
    } else if (mode.value === 'group' && selectedGid.value) {
      data = await rcmsApi.getGroupAlertLogs(selectedGid.value, params)
      alerts.value = unwrapAlerts(data).map(a => normalizeAlert(a))
    } else if (mode.value === 'device' && devices.value.length) {
      const results = await Promise.all(
        devices.value.map(d => rcmsApi.getDeviceAlertLogs(d.sn, params).catch(() => []))
      )
      alerts.value = results.flatMap((result, index) =>
        unwrapAlerts(result).map(a => normalizeAlert(a, devices.value[index]?.sn))
      )
    }
  } catch(e) {
    error.value = e.message
  } finally {
    loaded.value = true
    loading.value = false
  }
}

function severityColor(level) {
  if (!level) return '#6b7280'
  const l = level.toLowerCase()
  if (l.includes('critical') || l.includes('high')) return '#ef4444'
  if (l.includes('warn') || l.includes('medium'))   return '#f59e0b'
  if (l.includes('info') || l.includes('low'))       return '#60a5fa'
  return '#6b7280'
}

function severityLabel(alert) {
  return alert.level || 'Info'
}

function alertStatusLabel(alert) {
  const status = String(alert.status ?? '').toLowerCase()
  if (status === '1' || status.includes('resolv') || status.includes('clear')) return 'Resolved'
  if (status === '0' || status === '-1' || status.includes('active')) return 'Active'
  return alert.status || 'Active'
}

function alertStatusClass(alert) {
  return alertStatusLabel(alert) === 'Resolved' ? 'bg-success' : 'bg-warning text-dark'
}

function formatTs(ts) {
  if (!ts) return '—'
  const date = typeof ts === 'number' || /^\d+$/.test(String(ts))
    ? new Date(Number(ts))
    : new Date(ts)
  return Number.isNaN(date.getTime()) ? String(ts) : date.toLocaleString()
}

onMounted(async () => { await init(); await loadAlerts() })
</script>

<template>
  <AppShell
    :breadcrumbs="['IOT-Smart Park', 'RCMS', t('rcms_alerts.breadcrumb')]"
    :title="t('rcms_alerts.title')"
    :tabs="[]" active-tab=""
  >
    <template #toolbar>
      <div class="d-flex flex-wrap gap-2 align-items-center">
        <!-- Mode toggle -->
        <div class="btn-group btn-group-sm">
          <button :class="['btn', mode==='device' ? 'btn-primary' : 'btn-outline-secondary']"
                  @click="mode='device'">{{ t('rcms_alerts.by_device') }}</button>
          <button :class="['btn', mode==='group'  ? 'btn-primary' : 'btn-outline-secondary']"
                  @click="mode='group'">{{ t('rcms_alerts.by_group') }}</button>
        </div>

        <!-- Device selector -->
        <select v-if="mode==='device'" v-model="selectedSn"
                class="form-select form-select-sm bg-dark text-white border-secondary" style="width:200px">
          <option v-for="d in devices" :key="d.sn" :value="d.sn">{{ d.sn }}</option>
        </select>

        <!-- Group selector -->
        <select v-if="mode==='group'" v-model="selectedGid"
                class="form-select form-select-sm bg-dark text-white border-secondary" style="width:200px">
          <option v-for="g in groups" :key="g.groupId||g.id" :value="g.groupId||g.id">
            {{ g.groupName || g.name || g.groupId || g.id }}
          </option>
        </select>

        <button class="btn btn-sm btn-primary" @click="pageNum=1; loadAlerts()" :disabled="loading">
          <i class="bi bi-search me-1"></i>{{ t('rcms_alerts.load_alerts') }}
        </button>
      </div>
    </template>

    <!-- Error -->
    <div v-if="error" class="alert alert-danger m-3">
      <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
    </div>

    <!-- Summary strip -->
    <div class="d-flex gap-3 px-3 pt-3 pb-1 flex-wrap">
      <div v-for="badge in [
        { label: t('rcms_alerts.total'),    val: alerts.length,                                        color: '#60a5fa' },
        { label: t('rcms_alerts.critical'), val: alerts.filter(a=>String(a.level||a.alertLevel||'').toLowerCase().includes('critical')).length, color: '#ef4444' },
        { label: t('rcms_alerts.warning'),  val: alerts.filter(a=>String(a.level||a.alertLevel||'').toLowerCase().includes('warn')).length,    color: '#f59e0b' },
        { label: t('rcms_alerts.info'),     val: alerts.filter(a=>String(a.level||a.alertLevel||'').toLowerCase().includes('info')).length,    color: '#34d399' },
      ]" :key="badge.label"
         class="rounded-3 px-3 py-2 d-flex align-items-center gap-2"
         style="background: rgba(255,255,255,0.05);">
        <span class="fw-bold fs-5" :style="`color:${badge.color}`">{{ badge.val }}</span>
        <span class="text-secondary small">{{ badge.label }}</span>
      </div>
    </div>

    <!-- Table -->
    <div class="p-3">
      <div class="card border-0 text-white" style="background: rgba(255,255,255,0.04); border-radius: 12px;">
        <div class="card-body p-0">
          <div v-if="loading" class="text-center py-5">
            <div class="spinner-border text-warning mb-2"></div>
            <p class="text-secondary">Loading alerts...</p>
          </div>
          <div v-else-if="loaded && alerts.length === 0" class="text-center py-5 text-secondary">
            <i class="bi bi-bell-slash fs-1"></i>
            <p class="mt-2">No alerts found for selected period</p>
            <p class="small mb-0">RCMS returned 0 alert records for the selected device/group.</p>
          </div>
          <div v-else class="table-responsive">
            <table class="table table-dark table-hover mb-0">
              <thead>
                <tr style="border-color: rgba(255,255,255,0.08)">
                  <th>Time</th>
                  <th>Device SN</th>
                  <th>Alert Type</th>
                  <th>Level</th>
                  <th>Message</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(a, i) in alerts" :key="i" style="border-color: rgba(255,255,255,0.05)">
                  <td class="text-secondary small text-nowrap">{{ formatTs(a.time) }}</td>
                  <td class="font-monospace text-info small">{{ a.sn || '—' }}</td>
                  <td>{{ a.type || '—' }}</td>
                  <td>
                    <span class="badge rounded-pill px-2"
                          :style="`background:${severityColor(a.level)}22; color:${severityColor(a.level)}`">
                      {{ severityLabel(a) }}
                    </span>
                  </td>
                  <td class="small" style="max-width:300px; white-space: normal;">
                    {{ a.message || '—' }}
                  </td>
                  <td>
                    <span class="badge" :class="alertStatusClass(a)">
                      {{ alertStatusLabel(a) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <!-- Pagination -->
        <div class="card-footer border-0 d-flex justify-content-between align-items-center"
             style="background: rgba(255,255,255,0.03);">
          <button class="btn btn-sm btn-outline-secondary" :disabled="pageNum<=1" @click="pageNum--; loadAlerts()">
            <i class="bi bi-chevron-left"></i> Prev
          </button>
          <span class="text-secondary small">Page {{ pageNum }}</span>
          <button class="btn btn-sm btn-outline-secondary" :disabled="alerts.length < pageSize" @click="pageNum++; loadAlerts()">
            Next <i class="bi bi-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>
  </AppShell>
</template>
