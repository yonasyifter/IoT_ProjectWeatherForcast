/**
 * RCMS Open API client.
 *
 * Browser code calls the local FastAPI proxy. The backend signs Robustel RCMS
 * requests server-side, avoiding CORS failures and keeping the HMAC secret out
 * of the frontend bundle.
 */
import api from '@/utils/api.js'

async function rcmsRequest(method, path, { body = null, queryParams = {} } = {}) {
  return api.post('/api/rcms/request', {
    method: method.toUpperCase(),
    path,
    queryParams,
    body,
  })
}

function cleanDevicePayload(device) {
  const model = device.deviceModel?.trim()
  const payload = {
    deviceName: device.deviceName?.trim(),
    sn: device.sn?.trim(),
    imei: device.imei?.trim(),
    mac: device.mac?.trim(),
    deviceModel: model,
    deviceSeries: model,
    deviceDesc: device.deviceDesc?.trim(),
    area: device.area?.trim(),
    deviceSysType: Number(device.deviceSysType ?? 0),
    tagIds: Array.isArray(device.tagIds) ? device.tagIds : [],
  }
  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => value !== undefined && value !== null && value !== '')
  )
}

export const rcmsApi = {
  // DASHBOARD
  getDashboardDeviceTotal()   { return rcmsRequest('GET', '/api/link/dashboard/deviceTotal') },
  getDashboardNetworkTotal()  { return rcmsRequest('GET', '/api/link/dashboard/networkTotal') },

  // DEVICES
  getDevices(pageNum = 1, pageSize = 10) {
    return rcmsRequest('GET', '/api/link/device/devices', { queryParams: { pageNum, pageSize } })
  },
  getDevice(sn)               { return rcmsRequest('GET', `/api/link/device/devices/${encodeURIComponent(sn)}`) },
  getDeviceLocationInfo(sn)   { return rcmsRequest('GET', `/api/link/device/devices/${encodeURIComponent(sn)}/locationInfo`) },
  getDevicePowerStatus(sn)    { return rcmsRequest('GET', `/api/link/device/devices/${encodeURIComponent(sn)}/powerStatus`) },
  getDeviceStatusData(sn, p)  { return rcmsRequest('GET', `/api/link/device/devices/${encodeURIComponent(sn)}/statusData`, { queryParams: p }) },
  getDeviceTrafficUsage(sn, p){ return rcmsRequest('GET', `/api/link/device/devices/${encodeURIComponent(sn)}/trafficUsageData`, { queryParams: p }) },
  getDeviceSignalLog(sn, p)   { return rcmsRequest('GET', `/api/link/device/devices/${encodeURIComponent(sn)}/signalStrengthLog`, { queryParams: p }) },
  getDeviceRegularReport(sn, p){ return rcmsRequest('GET', `/api/link/device/devices/${encodeURIComponent(sn)}/regularReport`, { queryParams: p }) },
  getDeviceAlertLogs(sn, p)   { return rcmsRequest('GET', `/api/link/device/devices/${encodeURIComponent(sn)}/alertLogs`, { queryParams: p }) },
  getDeviceCallRecords(sn, p) { return rcmsRequest('GET', `/api/link/device/devices/${encodeURIComponent(sn)}/callRecords`, { queryParams: p }) },
  addDevice(device)           { return rcmsRequest('POST', '/api/gm/devices', { body: [cleanDevicePayload(device)] }) },
  deleteDevice(sn)            { return rcmsRequest('DELETE', `/api/gm/devices/${encodeURIComponent(sn)}`) },

  // GROUPS
  getGroups()                 { return rcmsRequest('GET', '/api/link/device/groups') },
  getGroupAlertLogs(gId, p)   { return rcmsRequest('GET', `/api/link/device/groups/${encodeURIComponent(gId)}/alertLogs`, { queryParams: p }) },

  // GPS
  getGpsReport(sn, p)         { return rcmsRequest('GET', '/api/link/device/gpsReport', { queryParams: { sn, ...p } }) },
  getDeviceGpsData(sn, p = {}) { return rcmsRequest('GET', `/api/link/device/devices/${encodeURIComponent(sn)}/gpsData`, { queryParams: p }) },

  // CONNECTION / LAN
  getConnectionHistory(sn, p) { return rcmsRequest('GET', '/api/link/device/connectionHistory', { queryParams: { sn, ...p } }) },
  getLanInfo(sn)              { return rcmsRequest('GET', '/api/link/device/lanInfo', { queryParams: { sn } }) },

  // DI REPORTS
  getDiReport(sn, p)          { return rcmsRequest('GET', '/api/link/device/diReport', { queryParams: { sn, ...p } }) },
  getDiCounterReport(sn, p)   { return rcmsRequest('GET', `/api/link/device/${encodeURIComponent(sn)}/diCounterReport`, { queryParams: p }) },
  getDiCounterDetail(sn, p)   { return rcmsRequest('GET', `/api/link/device/${encodeURIComponent(sn)}/diCounterDetail`, { queryParams: p }) },

  // SYSLOG
  getDeviceSyslog(sn, p)      { return rcmsRequest('GET', `/api/log/device/devices/${encodeURIComponent(sn)}/syslog`, { queryParams: p }) },

  // LICENSES / APPS / MODELS
  getDeviceLicenses(sn, p)    { return rcmsRequest('GET', '/api/link/device/licenses', { queryParams: { sn, ...p } }) },
  getDeviceApps(sn)           { return rcmsRequest('GET', `/api/link/devices/${encodeURIComponent(sn)}/apps`) },
  getModels()                 { return rcmsRequest('GET', '/api/gm/models') },

  // SETTINGS
  setDeviceGroup(sn, groupName)   { return rcmsRequest('PUT', `/api/link/devices/${encodeURIComponent(sn)}/group`, { body: { groupName } }) },
  setDeviceDescription(sn, desc)  { return rcmsRequest('PUT', `/api/link/devices/${encodeURIComponent(sn)}/description`, { body: { description: desc } }) },

  // COMMANDS
  rebootDevice(sn)            { return rcmsRequest('PUT', `/api/link/devices/${encodeURIComponent(sn)}`, { body: { commandType: 'Reboot' } }) },
  queryRebootStatus(id)       { return rcmsRequest('GET', `/api/link/command/${encodeURIComponent(id)}`, { queryParams: { commandType: 'Reboot' } }) },
  generateConfigFile(sn)      { return rcmsRequest('PUT', `/api/link/devices/${encodeURIComponent(sn)}`, { body: { commandType: 'GenerateConfigFile' } }) },
  queryConfigFileStatus(id)   { return rcmsRequest('GET', `/api/link/command/${encodeURIComponent(id)}`, { queryParams: { commandType: 'GenerateConfigFile' } }) },
  pushConfigFile(sn, config, name) { return rcmsRequest('PUT', `/api/link/devices/${encodeURIComponent(sn)}/configfile`, { body: { config, name } }) },
  queryCommandStatus(id, type){ return rcmsRequest('GET', `/api/link/command/${encodeURIComponent(id)}`, { queryParams: { commandType: type } }) },
}

export default rcmsApi
