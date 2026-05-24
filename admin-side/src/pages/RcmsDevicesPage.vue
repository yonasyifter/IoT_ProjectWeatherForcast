<script setup>
import { computed, ref, onMounted } from 'vue'
import AppShell from '../components/layout/AppShell.vue'
import { rcmsApi } from '../services/rcmsApi.js'

const loading  = ref(false)
const error    = ref('')
const devices  = ref([])
const models   = ref(['EG5120'])
const groups   = ref([])
const pageNum  = ref(1)
const pageSize = ref(20)
const search   = ref('')
const rcmsAreas = [
  { label: 'Europe', value: 'EUR' },
  { label: 'East Asia', value: 'EA' },
  { label: 'East Asia 2', value: 'EA2' },
  { label: 'North America', value: 'NA' },
  { label: 'South America', value: 'SA' },
  { label: 'Australia', value: 'AU' },
]
const deviceOsOptions = [
  { label: 'RobustOS', value: 0 },
  { label: 'RobustOS PRO', value: 2 },
  { label: 'NON RobustOS', value: 1 },
]

// Modals
const showAddModal    = ref(false)
const showDetailModal = ref(false)
const selectedDevice  = ref(null)
const deviceApps      = ref([])
const deviceLicenses  = ref([])
const detailTab       = ref('info')
const addLoading      = ref(false)
const addError        = ref('')

// New device form
const blankDevice = () => ({
  deviceName: '',
  sn: '',
  imei: '',
  mac: '',
  deviceModel: '',
  area: 'EUR',
  deviceSysType: 0,
  deviceDesc: '',
  tagIds: [],
})
const newDevice = ref(blankDevice())

async function loadDevices() {
  loading.value = true
  error.value   = ''
  try {
    const data = await rcmsApi.getDevices(pageNum.value, pageSize.value)
    devices.value = Array.isArray(data) ? data : (data?.list || data?.records || [])
  } catch(e) { error.value = e.message }
  finally { loading.value = false }
}

async function loadMeta() {
  try {
    const [g, m] = await Promise.all([
      rcmsApi.getGroups().catch(() => []),
      rcmsApi.getModels().catch(() => []),
    ])
    groups.value = Array.isArray(g) ? g : (g?.list || [])
    const modelList = Array.isArray(m) ? m : (m?.list || m?.records || [])
    const names = modelList
      .map(item => item.deviceModel || item.model || item.modelName || item.name || item)
      .filter(Boolean)
    if (names.length) models.value = [...new Set(names.map(String))].sort()
  } catch(e) {}
}

async function openDetail(device) {
  selectedDevice.value = device
  showDetailModal.value = true
  detailTab.value = 'info'
  deviceApps.value = []
  deviceLicenses.value = []
  try {
    const [apps, lics] = await Promise.all([
      rcmsApi.getDeviceApps(device.sn).catch(() => []),
      rcmsApi.getDeviceLicenses(device.sn, { pageNum: 1, pageSize: 20 }).catch(() => []),
    ])
    deviceApps.value     = Array.isArray(apps) ? apps : (apps?.list || [])
    deviceLicenses.value = Array.isArray(lics) ? lics : (lics?.list || [])
  } catch(e) {}
}

async function addDevice() {
  addError.value = ''
  const payload = {
    ...newDevice.value,
    deviceName: newDevice.value.deviceName.trim(),
    sn: newDevice.value.sn.trim(),
    imei: newDevice.value.imei.trim(),
    mac: newDevice.value.mac.trim(),
    deviceModel: newDevice.value.deviceModel.trim(),
    area: newDevice.value.area.trim(),
    deviceDesc: newDevice.value.deviceDesc.trim(),
    deviceSysType: Number(newDevice.value.deviceSysType ?? 0),
  }
  if (!payload.deviceName) { addError.value = 'Device name is required.'; return }
  if (!payload.sn) { addError.value = 'Serial Number is required.'; return }
  if (!/^[a-zA-Z0-9]{1,50}$/.test(payload.sn)) { addError.value = 'SN supports letters and numbers only.'; return }
  if (!payload.imei && !payload.mac) { addError.value = 'Enter at least one hardware identifier: IMEI or MAC.'; return }
  if (payload.imei && !/^\d{14,17}$/.test(payload.imei)) { addError.value = 'IMEI must be 14-17 digits.'; return }
  if (!payload.deviceModel) { addError.value = 'Device model is required.'; return }
  if (models.value.length && !models.value.includes(payload.deviceModel)) {
    addError.value = 'Select an exact model from the RCMS model list.'
    return
  }
  if (!rcmsAreas.some(area => area.value === payload.area)) {
    addError.value = 'Select a valid RCMS device area. RCMS submits area codes such as EUR, EA, NA, SA, and AU.'
    return
  }

  addLoading.value = true
  try {
    await rcmsApi.addDevice(payload)
    showAddModal.value = false
    newDevice.value = blankDevice()
    await loadDevices()
  } catch(e) { addError.value = e.message }
  finally { addLoading.value = false }
}

async function deleteDevice(sn) {
  if (!confirm(`Delete device ${sn}?`)) return
  try {
    await rcmsApi.deleteDevice(sn)
    await loadDevices()
  } catch(e) { alert('Error: ' + e.message) }
}

async function reboot(sn) {
  if (!confirm(`Reboot device ${sn}?`)) return
  try {
    await rcmsApi.rebootDevice(sn)
    alert('Reboot command sent!')
  } catch(e) { alert('Error: ' + e.message) }
}

const filteredDevices = computed(() => {
  if (!search.value.trim()) return devices.value
  const q = search.value.toLowerCase()
  return devices.value.filter(d =>
    String(d.sn||'').toLowerCase().includes(q) ||
    String(d.deviceName||'').toLowerCase().includes(q) ||
    String(d.deviceModel||'').toLowerCase().includes(q)
  )
})

function onlineStatus(device) {
  return Number(device?.deviceOnLineStatus ?? device?.onlineStatus ?? device?.status ?? -1)
}

function statusColor(device) {
  return onlineStatus(device) === 1 ? '#22c55e' : '#ef4444'
}

function statusLabel(device) {
  return onlineStatus(device) === 1 ? 'Online' : 'Offline'
}

onMounted(async () => { await Promise.all([loadDevices(), loadMeta()]) })
</script>

<template>
  <AppShell
    :breadcrumbs="['IOT-Smart Park', 'RCMS', 'Devices']"
    title="Device Management"
    :tabs="[]" active-tab=""
  >
    <template #toolbar>
      <div class="d-flex gap-2 align-items-center flex-wrap">
        <div class="input-group input-group-sm" style="width:240px">
          <span class="input-group-text bg-dark border-secondary text-secondary"><i class="bi bi-search"></i></span>
          <input v-model="search" class="form-control bg-dark border-secondary text-white" placeholder="Search SN / Name..."/>
        </div>
        <button class="btn btn-sm btn-success" @click="addError=''; showAddModal=true">
          <i class="bi bi-plus-circle me-1"></i>Add Device
        </button>
        <button class="btn btn-sm btn-outline-secondary" @click="loadDevices" :disabled="loading">
          <i class="bi bi-arrow-clockwise"></i>
        </button>
      </div>
    </template>

    <div v-if="error" class="alert alert-danger mx-3 mt-3">
      <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
    </div>

    <div class="p-3">
      <div class="card border-0 text-white" style="background: rgba(255,255,255,0.04); border-radius: 12px;">
        <div class="card-body p-0">
          <div v-if="loading" class="text-center py-5">
            <div class="spinner-border text-primary mb-2"></div>
            <p class="text-secondary">Loading devices...</p>
          </div>
          <div v-else-if="filteredDevices.length===0" class="text-center py-5 text-secondary">
            <i class="bi bi-hdd-network fs-1"></i>
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
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in filteredDevices" :key="d.sn" style="border-color: rgba(255,255,255,0.05)">
                  <td class="font-monospace text-info">{{ d.sn }}</td>
                  <td>{{ d.deviceName || '—' }}</td>
                  <td class="text-secondary">{{ d.deviceModel || '—' }}</td>
                  <td>
                    <span class="badge rounded-pill"
                          :style="`background:${statusColor(d)}22; color:${statusColor(d)}`">
                      {{ statusLabel(d) }}
                    </span>
                  </td>
                  <td class="text-secondary">{{ d.deviceGroup || d.groupName || '—' }}</td>
                  <td class="text-secondary small">{{ d.createTime ? new Date(d.createTime).toLocaleDateString() : '—' }}</td>
                  <td>
                    <div class="d-flex gap-1">
                      <button class="btn btn-xs btn-outline-info" title="Details" @click="openDetail(d)"
                              style="padding: 2px 8px; font-size: 12px;">
                        <i class="bi bi-info-circle"></i>
                      </button>
                      <button class="btn btn-xs btn-outline-warning" title="Reboot" @click="reboot(d.sn)"
                              style="padding: 2px 8px; font-size: 12px;">
                        <i class="bi bi-arrow-clockwise"></i>
                      </button>
                      <button class="btn btn-xs btn-outline-danger" title="Delete" @click="deleteDevice(d.sn)"
                              style="padding: 2px 8px; font-size: 12px;">
                        <i class="bi bi-trash"></i>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="card-footer border-0 d-flex justify-content-between align-items-center"
             style="background: rgba(255,255,255,0.03);">
          <button class="btn btn-sm btn-outline-secondary" :disabled="pageNum<=1" @click="pageNum--; loadDevices()">
            <i class="bi bi-chevron-left"></i> Prev
          </button>
          <span class="text-secondary small">Page {{ pageNum }} · {{ devices.length }} devices</span>
          <button class="btn btn-sm btn-outline-secondary" :disabled="devices.length < pageSize" @click="pageNum++; loadDevices()">
            Next <i class="bi bi-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Add Device Modal -->
    <div v-if="showAddModal" class="modal fade show d-block" style="background:rgba(0,0,0,0.6);" @click.self="showAddModal=false">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content bg-dark text-white border-secondary">
          <div class="modal-header border-secondary">
            <h5 class="modal-title"><i class="bi bi-plus-circle me-2 text-success"></i>Add Device</h5>
            <button class="btn-close btn-close-white" @click="showAddModal=false"></button>
          </div>
          <div class="modal-body">
            <div v-if="addError" class="alert alert-danger py-2 small">
              <i class="bi bi-exclamation-triangle me-1"></i>{{ addError }}
            </div>
            <div class="mb-3">
              <label class="form-label text-secondary small">Device Name</label>
              <input v-model="newDevice.deviceName" class="form-control bg-dark border-secondary text-white" placeholder="e.g. Sensor-01"/>
            </div>
            <div class="mb-3">
              <label class="form-label text-secondary small">Serial Number (SN)</label>
              <input v-model="newDevice.sn" class="form-control bg-dark border-secondary text-white font-monospace" placeholder="e.g. 20210204161501"/>
            </div>
            <div class="mb-3">
              <label class="form-label text-secondary small">IMEI</label>
              <input v-model="newDevice.imei" class="form-control bg-dark border-secondary text-white font-monospace" placeholder="15-digit IMEI"/>
            </div>
            <div class="mb-3">
              <label class="form-label text-secondary small">MAC</label>
              <input v-model="newDevice.mac" class="form-control bg-dark border-secondary text-white font-monospace" placeholder="Optional if IMEI is provided"/>
            </div>
            <div class="mb-3">
              <label class="form-label text-secondary small">Model</label>
              <select v-model="newDevice.deviceModel" class="form-select bg-dark border-secondary text-white">
                <option value="">Select model...</option>
                <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label text-secondary small">RCMS Device Area</label>
              <select v-model="newDevice.area" class="form-select bg-dark border-secondary text-white">
                <option v-for="area in rcmsAreas" :key="area.value" :value="area.value">
                  {{ area.label }}
                </option>
              </select>
            </div>
            <div class="mb-3">
              <label class="form-label text-secondary small">Device OS</label>
              <div class="btn-group w-100" role="group">
                <button
                  v-for="os in deviceOsOptions"
                  :key="os.value"
                  type="button"
                  :class="['btn btn-sm', Number(newDevice.deviceSysType) === os.value ? 'btn-primary' : 'btn-outline-secondary']"
                  @click="newDevice.deviceSysType = os.value"
                >
                  {{ os.label }}
                </button>
              </div>
            </div>
            <div class="mb-0">
              <label class="form-label text-secondary small">Description</label>
              <textarea v-model="newDevice.deviceDesc" class="form-control bg-dark border-secondary text-white" rows="2" maxlength="200" placeholder="Optional"></textarea>
            </div>
          </div>
          <div class="modal-footer border-secondary">
            <button class="btn btn-secondary" @click="showAddModal=false">Cancel</button>
            <button class="btn btn-success" @click="addDevice" :disabled="addLoading">
              <span v-if="addLoading" class="spinner-border spinner-border-sm me-1"></span>
              {{ addLoading ? 'Registering...' : 'Add Device' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Detail Modal -->
    <div v-if="showDetailModal" class="modal fade show d-block" style="background:rgba(0,0,0,0.6);" @click.self="showDetailModal=false">
      <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
        <div class="modal-content bg-dark text-white border-secondary">
          <div class="modal-header border-secondary">
            <h5 class="modal-title">
              <i class="bi bi-hdd me-2 text-info"></i>
              {{ selectedDevice?.deviceName || selectedDevice?.sn }}
            </h5>
            <button class="btn-close btn-close-white" @click="showDetailModal=false"></button>
          </div>
          <div class="modal-body">
            <!-- Tabs -->
            <ul class="nav nav-tabs border-secondary mb-3">
              <li class="nav-item" v-for="tab in ['info','apps','licenses']" :key="tab">
                <button :class="['nav-link text-capitalize', detailTab===tab ? 'active bg-primary border-primary text-white' : 'text-secondary']"
                        @click="detailTab=tab">{{ tab }}</button>
              </li>
            </ul>

            <!-- Info tab -->
            <div v-if="detailTab==='info'" class="row g-3">
              <div class="col-md-6" v-for="[label,val] in [
                ['Serial Number', selectedDevice?.sn],
                ['Device Name', selectedDevice?.deviceName],
                ['Model', selectedDevice?.deviceModel],
                ['Status', statusLabel(selectedDevice)],
                ['Group', selectedDevice?.deviceGroup || selectedDevice?.groupName],
                ['Firmware', selectedDevice?.deviceFirmWareVersion],
                ['Description', selectedDevice?.deviceDesc],
                ['Created', selectedDevice?.createTime ? new Date(selectedDevice.createTime).toLocaleString() : '—'],
              ]" :key="label">
                <div class="p-2 rounded" style="background: rgba(255,255,255,0.05)">
                  <div class="text-secondary small">{{ label }}</div>
                  <div class="text-white">{{ val || '—' }}</div>
                </div>
              </div>
            </div>

            <!-- Apps tab -->
            <div v-if="detailTab==='apps'">
              <div v-if="deviceApps.length===0" class="text-center text-secondary py-3">
                <i class="bi bi-app fs-2"></i><p class="mt-2">No apps installed</p>
              </div>
              <table v-else class="table table-dark table-sm">
                <thead><tr><th>App Name</th><th>Version</th><th>Status</th></tr></thead>
                <tbody>
                  <tr v-for="app in deviceApps" :key="app.appId||app.name">
                    <td>{{ app.appName||app.name }}</td>
                    <td class="text-secondary">{{ app.version || '—' }}</td>
                    <td><span class="badge" :class="app.status===1?'bg-success':'bg-secondary'">{{ app.status===1?'Running':'Stopped' }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Licenses tab -->
            <div v-if="detailTab==='licenses'">
              <div v-if="deviceLicenses.length===0" class="text-center text-secondary py-3">
                <i class="bi bi-key fs-2"></i><p class="mt-2">No licenses found</p>
              </div>
              <table v-else class="table table-dark table-sm">
                <thead><tr><th>License</th><th>Type</th><th>Expires</th></tr></thead>
                <tbody>
                  <tr v-for="lic in deviceLicenses" :key="lic.licenseId||lic.id">
                    <td class="font-monospace small">{{ lic.licenseKey||lic.license }}</td>
                    <td>{{ lic.licenseType||lic.type||'—' }}</td>
                    <td class="text-secondary">{{ lic.expireTime ? new Date(lic.expireTime).toLocaleDateString() : '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="modal-footer border-secondary">
            <button class="btn btn-outline-warning btn-sm" @click="reboot(selectedDevice?.sn)">
              <i class="bi bi-arrow-clockwise me-1"></i>Reboot
            </button>
            <button class="btn btn-secondary" @click="showDetailModal=false">Close</button>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>
