<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import { rcmsApi } from '../services/rcmsApi.js'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const loading     = ref(false)
const error       = ref('')
const deviceTotal = ref(null)
const networkTotal= ref(null)
const devices     = ref([])
const pageNum     = ref(1)
const pageSize    = ref(10)

let timer = null

async function loadAll() {
  loading.value = true
  error.value   = ''
  try {
    const [dt, nt, devList] = await Promise.all([
      rcmsApi.getDashboardDeviceTotal(),
      rcmsApi.getDashboardNetworkTotal().catch(() => null),
      rcmsApi.getDevices(pageNum.value, pageSize.value),
    ])
    deviceTotal.value  = dt
    networkTotal.value = nt
    devices.value      = Array.isArray(devList) ? devList
                       : (devList?.list || devList?.records || [])
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function reboot(sn) {
  if (!confirm(t('rcms_dashboard.reboot_confirm', { sn }))) return
  try {
    await rcmsApi.rebootDevice(sn)
    alert(t('rcms_dashboard.reboot_success', { sn }))
  } catch (e) { alert(t('rcms_dashboard.reboot_error', { message: e.message })) }
}

onMounted(() => { loadAll(); timer = setInterval(loadAll, 30_000) })
onUnmounted(() => clearInterval(timer))

function statusColor(online) {
  return online === 1 ? '#22c55e' : '#ef4444'
}
</script>

<template>
  <AppShell
    :breadcrumbs="['IOT-Smart Park', 'RCMS', 'Device Dashboard']"
    title="RCMS Device Dashboard"
    :tabs="[]"
    active-tab=""
  >
    <template #toolbar>
      <button class="btn btn-outline-primary btn-sm" @click="loadAll" :disabled="loading">
        <i class="bi bi-arrow-clockwise me-1"></i>{{ t('common.refresh') }}
      </button>
    </template>

    <!-- Error -->
    <div v-if="error" class="alert alert-danger m-3">
      <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
    </div>

    <!-- Summary Cards -->
    <div class="row g-3 p-3 pb-0">
      <div class="col-6 col-md-3" v-for="card in [
        { label: t('rcms_dashboard.total_devices'),    val: deviceTotal?.deviceTotal,        color: '#60a5fa', icon: 'bi-hdd-network' },
        { label: t('rcms_dashboard.online'),           val: deviceTotal?.onlineTotal,         color: '#22c55e', icon: 'bi-wifi' },
        { label: t('rcms_dashboard.offline'),          val: deviceTotal?.offlineTotal,        color: '#ef4444', icon: 'bi-wifi-off' },
        { label: t('rcms_dashboard.registered'),       val: deviceTotal?.registeredTotal,     color: '#a78bfa', icon: 'bi-patch-check' },
        { label: t('rcms_dashboard.unregistered'),     val: deviceTotal?.unRegisteredTotal,   color: '#f59e0b', icon: 'bi-patch-question' },
        { label: t('rcms_dashboard.users'),            val: deviceTotal?.userTotal,           color: '#34d399', icon: 'bi-people' },
      ]" :key="card.label">
        <div class="card h-100 border-0 text-white"
             style="background: rgba(255,255,255,0.05); border-radius: 12px;">
          <div class="card-body d-flex align-items-center gap-3 py-3">
            <div class="rounded-3 d-flex align-items-center justify-content-center"
                 :style="`background:${card.color}22; width:46px; height:46px; flex-shrink:0`">
              <i :class="['bi', card.icon, 'fs-4']" :style="`color:${card.color}`"></i>
            </div>
            <div>
              <div class="small text-secondary">{{ card.label }}</div>
              <div class="fs-3 fw-bold" :style="`color:${card.color}`">
                <span v-if="loading && deviceTotal === null">—</span>
                <span v-else>{{ card.val ?? '—' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Device Table -->
    <div class="p-3">
      <div class="card border-0 text-white" style="background: rgba(255,255,255,0.04); border-radius: 12px;">
        <div class="card-header d-flex justify-content-between align-items-center border-0"
             style="background: rgba(255,255,255,0.05); border-radius: 12px 12px 0 0;">
          <span class="fw-semibold"><i class="bi bi-hdd-network me-2 text-primary"></i>Device List</span>
          <div class="d-flex gap-2 align-items-center">
            <select v-model="pageSize" @change="loadAll" class="form-select form-select-sm bg-dark text-white border-secondary" style="width:auto">
              <option :value="10">10 / page</option>
              <option :value="20">20 / page</option>
              <option :value="50">50 / page</option>
            </select>
          </div>
        </div>
        <div class="card-body p-0">
          <!-- Loading skeleton -->
          <div v-if="loading && devices.length === 0" class="text-center py-5 text-secondary">
            <div class="spinner-border text-primary mb-3"></div>
            <p>Loading devices...</p>
          </div>

          <div v-else-if="devices.length === 0 && !loading" class="text-center py-5 text-secondary">
            <i class="bi bi-inbox fs-1"></i>
            <p class="mt-2">No devices found</p>
          </div>

          <div v-else class="table-responsive">
            <table class="table table-dark table-hover mb-0">
              <thead>
                <tr style="border-color: rgba(255,255,255,0.08)">
                  <th>Serial Number</th>
                  <th>Name</th>
                  <th>Model</th>
                  <th>Status</th>
                  <th>Group</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in devices" :key="d.sn" style="border-color: rgba(255,255,255,0.05)">
                  <td class="font-monospace text-info">{{ d.sn }}</td>
                  <td>{{ d.deviceName || '—' }}</td>
                  <td class="text-secondary">{{ d.deviceModel || '—' }}</td>
                  <td>
                    <span class="badge rounded-pill"
                          :style="`background:${statusColor(d.deviceOnLineStatus)}22; color:${statusColor(d.deviceOnLineStatus)}`">
                      <i :class="['bi me-1', d.deviceOnLineStatus===1 ? 'bi-circle-fill' : 'bi-circle']"
                         style="font-size:8px; vertical-align: middle;"></i>
                      {{ d.deviceOnLineStatus === 1 ? 'Online' : 'Offline' }}
                    </span>
                  </td>
                  <td class="text-secondary">{{ d.deviceGroup || '—' }}</td>
                  <td>
                    <button class="btn btn-sm btn-outline-warning" @click="reboot(d.sn)" title="Reboot">
                      <i class="bi bi-arrow-clockwise"></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <!-- Pagination -->
        <div class="card-footer border-0 d-flex justify-content-between align-items-center"
             style="background: rgba(255,255,255,0.03);">
          <button class="btn btn-sm btn-outline-secondary" :disabled="pageNum <= 1" @click="pageNum--; loadAll()">
            <i class="bi bi-chevron-left"></i> Prev
          </button>
          <span class="text-secondary small">Page {{ pageNum }}</span>
          <button class="btn btn-sm btn-outline-secondary" :disabled="devices.length < pageSize" @click="pageNum++; loadAll()">
            Next <i class="bi bi-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>
  </AppShell>
</template>
