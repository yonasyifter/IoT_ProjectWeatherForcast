/**
 * RCMS Open API Service — Robustel RCMS v2.0
 * Auth: HmacSHA256 signature (NOT OAuth)
 *
 * NOTE: crypto-js is bundled inline to avoid npm install requirement.
 * If you prefer: npm install crypto-js  and use: import CryptoJS from 'crypto-js'
 */

// ─── CONFIG ────────────────────────────────────────────────────────────────
const RCMS_BASE   = 'https://rcms-cloud.robustel.net'
const CLIENT_ID   = '230c0f5b40354b4eb3f9d0eb5a9199cf'
const CLIENT_SECRET = '61243G66VJ1d17824615299a9ih64240153O7B4L6Sy5Ag2ydZt9003r15661P8297031N79B3G608p17a29526a621w4L5N230c0f5b40354b4eb3f9d0eb5a9199cf'

// ─── MINIMAL HmacSHA256 via SubtleCrypto (browser built-in, no npm needed) ─
async function hmacSHA256hex(message, key) {
  const enc = new TextEncoder()
  const cryptoKey = await window.crypto.subtle.importKey(
    'raw', enc.encode(key),
    { name: 'HMAC', hash: 'SHA-256' },
    false, ['sign']
  )
  const sig = await window.crypto.subtle.sign('HMAC', cryptoKey, enc.encode(message))
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('')
}

function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
  })
}

async function rcmsRequest(method, path, { body = null, queryParams = {} } = {}) {
  const timestamp  = Date.now().toString()
  const uniqueCode = generateUUID()

  const cleanParams = Object.fromEntries(
    Object.entries(queryParams).filter(([, v]) => v !== undefined && v !== null)
  )

  const publicParams = {
    apiVersion: '1.0',
    clientId: CLIENT_ID,
    signatureVersion: '1.0',
    timestamp,
    uniqueCode,
    ...cleanParams,
  }

  // Step 1: Alphabetically sorted canonical string
  const canonicalized = Object.keys(publicParams)
    .sort()
    .map(k => `${k}=${publicParams[k]}`)
    .join('&')

  // Step 2: StringToSign
  let stringToSign = `${method.toUpperCase()}${path}${canonicalized}`
  if (body) stringToSign += `&${JSON.stringify(body)}`
  stringToSign += CLIENT_SECRET

  // Step 3: HmacSHA256(StringToSign, clientId + uniqueCode)
  const signature = await hmacSHA256hex(stringToSign, CLIENT_ID + uniqueCode)

  const headers = {
    'clientId': CLIENT_ID,
    'signatureVersion': '1.0',
    'apiVersion': '1.0',
    'timestamp': timestamp,
    'uniqueCode': uniqueCode,
    'signature': signature,
    'Content-Type': 'application/json',
  }

  const queryString = Object.keys(cleanParams).length
    ? '?' + new URLSearchParams(cleanParams).toString()
    : ''

  const response = await fetch(`${RCMS_BASE}${path}${queryString}`, {
    method: method.toUpperCase(),
    headers,
    body: body ? JSON.stringify(body) : null,
  })

  if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  const data = await response.json()
  if (data.code !== 0) throw new Error(`RCMS ${data.code}: ${data.msg}`)
  return data.data
}

// ─── ALL ENDPOINTS ─────────────────────────────────────────────────────────
export const rcmsApi = {

  // DASHBOARD
  getDashboardDeviceTotal()   { return rcmsRequest('GET', '/api/link/dashboard/deviceTotal') },
  getDashboardNetworkTotal()  { return rcmsRequest('GET', '/api/link/dashboard/networkTotal') },

  // DEVICES
  getDevices(pageNum = 1, pageSize = 10) {
    return rcmsRequest('GET', '/api/link/device/devices', { queryParams: { pageNum, pageSize } })
  },
  getDevice(sn)               { return rcmsRequest('GET', `/api/link/device/devices/${sn}`) },
  getDeviceLocationInfo(sn)   { return rcmsRequest('GET', `/api/link/device/devices/${sn}/locationInfo`) },
  getDevicePowerStatus(sn)    { return rcmsRequest('GET', `/api/link/device/devices/${sn}/powerStatus`) },
  getDeviceStatusData(sn, p)  { return rcmsRequest('GET', `/api/link/device/devices/${sn}/statusData`, { queryParams: p }) },
  getDeviceTrafficUsage(sn, p){ return rcmsRequest('GET', `/api/link/device/devices/${sn}/trafficUsageData`, { queryParams: p }) },
  getDeviceSignalLog(sn, p)   { return rcmsRequest('GET', `/api/link/device/devices/${sn}/signalStrengthLog`, { queryParams: p }) },
  getDeviceRegularReport(sn, p){ return rcmsRequest('GET', `/api/link/device/devices/${sn}/regularReport`, { queryParams: p }) },
  getDeviceAlertLogs(sn, p)   { return rcmsRequest('GET', `/api/link/device/devices/${sn}/alertLogs`, { queryParams: p }) },
  getDeviceCallRecords(sn, p) { return rcmsRequest('GET', `/api/link/device/devices/${sn}/callRecords`, { queryParams: p }) },
  addDevice(d)                { return rcmsRequest('POST', '/api/gm/devices', { body: [d] }) },
  deleteDevice(sn)            { return rcmsRequest('DELETE', `/api/gm/devices/${sn}`) },

  // GROUPS
  getGroups()                 { return rcmsRequest('GET', '/api/link/device/groups') },
  getGroupAlertLogs(gId, p)   { return rcmsRequest('GET', `/api/link/device/groups/${gId}/alertLogs`, { queryParams: p }) },

  // GPS
  getGpsReport(sn, p)         { return rcmsRequest('GET', '/api/link/device/gpsReport', { queryParams: { sn, ...p } }) },
  getDeviceGpsData(sn)        { return rcmsRequest('GET', `/api/link/device/devices/${sn}/gpsData`) },

  // CONNECTION / LAN
  getConnectionHistory(sn, p) { return rcmsRequest('GET', '/api/link/device/connectionHistory', { queryParams: { sn, ...p } }) },
  getLanInfo(sn)              { return rcmsRequest('GET', '/api/link/device/lanInfo', { queryParams: { sn } }) },

  // DI REPORTS
  getDiReport(sn, p)          { return rcmsRequest('GET', '/api/link/device/diReport', { queryParams: { sn, ...p } }) },
  getDiCounterReport(sn, p)   { return rcmsRequest('GET', `/api/link/device/${sn}/diCounterReport`, { queryParams: p }) },
  getDiCounterDetail(sn, p)   { return rcmsRequest('GET', `/api/link/device/${sn}/diCounterDetail`, { queryParams: p }) },

  // SYSLOG
  getDeviceSyslog(sn, p)      { return rcmsRequest('GET', `/api/log/device/devices/${sn}/syslog`, { queryParams: p }) },

  // LICENSES / APPS / MODELS
  getDeviceLicenses(sn, p)    { return rcmsRequest('GET', '/api/link/device/licenses', { queryParams: { sn, ...p } }) },
  getDeviceApps(sn)           { return rcmsRequest('GET', `/api/link/devices/${sn}/apps`) },
  getModels()                 { return rcmsRequest('GET', '/api/gm/models') },

  // SETTINGS
  setDeviceGroup(sn, groupName)   { return rcmsRequest('PUT', `/api/link/devices/${sn}/group`, { body: { groupName } }) },
  setDeviceDescription(sn, desc)  { return rcmsRequest('PUT', `/api/link/devices/${sn}/description`, { body: { description: desc } }) },

  // COMMANDS
  rebootDevice(sn)            { return rcmsRequest('PUT', `/api/link/devices/${sn}`, { body: { commandType: 'Reboot' } }) },
  queryRebootStatus(id)       { return rcmsRequest('GET', `/api/link/command/${id}`, { queryParams: { commandType: 'Reboot' } }) },
  generateConfigFile(sn)      { return rcmsRequest('PUT', `/api/link/devices/${sn}`, { body: { commandType: 'GenerateConfigFile' } }) },
  queryConfigFileStatus(id)   { return rcmsRequest('GET', `/api/link/command/${id}`, { queryParams: { commandType: 'GenerateConfigFile' } }) },
  pushConfigFile(sn, config, name) { return rcmsRequest('PUT', `/api/link/devices/${sn}/configfile`, { body: { config, name } }) },
  queryCommandStatus(id, type){ return rcmsRequest('GET', `/api/link/command/${id}`, { queryParams: { commandType: type } }) },
}

export default rcmsApi
