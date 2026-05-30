const EMERGENCY_API_URL = '/api/emergency'

function firstValue(item, keys) {
  for (const key of keys) {
    const value = item?.[key]
    if (value !== undefined && value !== null && value !== '') return value
  }
  return null
}

function toNumber(value) {
  if (value === undefined || value === null || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function parseLocationCoordinates(location) {
  if (typeof location !== 'string') return { latitude: null, longitude: null }

  const match = location.match(/Lat:\s*(-?\d+(?:\.\d+)?)\s*,\s*Lng:\s*(-?\d+(?:\.\d+)?)/i)
  if (!match) return { latitude: null, longitude: null }

  return {
    latitude: toNumber(match[1]),
    longitude: toNumber(match[2]),
  }
}

function unwrapEmergencyList(payload) {
  if (typeof payload === 'string') {
    try {
      return unwrapEmergencyList(JSON.parse(payload))
    } catch (_) {
      return []
    }
  }

  if (Array.isArray(payload)) return payload

  const possibleLists = [
    payload?.items,
    payload?.emergencies,
    payload?.emergency,
    payload?.requests,
    payload?.data,
    payload?.body,
  ]

  for (const value of possibleLists) {
    if (Array.isArray(value)) return value
    if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value)
        if (Array.isArray(parsed)) return parsed
        if (Array.isArray(parsed?.items)) return parsed.items
        if (Array.isArray(parsed?.data)) return parsed.data
      } catch (_) {}
    }
  }

  return []
}

function normalizeEmergencyRequest(item, index) {
  const coordinates = parseLocationCoordinates(item?.location)
  const requestId = firstValue(item, [
    'request_id',
    'requestId',
    'emergency_id',
    'emergencyId',
    'id',
    'pk',
  ]) || [item?.userID, item?.timestamp].filter(Boolean).join('-') || `emergency-${index}`

  return {
    ...item,
    request_id: String(requestId),
    visitor_id: firstValue(item, ['visitor_id', 'visitorId', 'user_id', 'userId', 'userID', 'uid']),
    visitor_name: firstValue(item, ['visitor_name', 'visitorName', 'name', 'display_name', 'displayName']),
    phone: firstValue(item, ['phone', 'phone_number', 'phoneNumber', 'mobile']),
    message: firstValue(item, ['message', 'description', 'note', 'emergency_message', 'emergencyMessage']),
    latitude: toNumber(firstValue(item, ['latitude', 'lat', 'visitor_latitude', 'current_latitude'])) ?? coordinates.latitude,
    longitude: toNumber(firstValue(item, ['longitude', 'lng', 'lon', 'visitor_longitude', 'current_longitude'])) ?? coordinates.longitude,
    status: firstValue(item, ['status', 'state']) || 'active',
    created_at: firstValue(item, ['created_at', 'createdAt', 'timestamp', 'time']),
    updated_at: firstValue(item, ['updated_at', 'updatedAt', 'last_seen', 'lastSeen']),
  }
}

async function parseResponse(response) {
  const text = await response.text()
  let data = null

  if (text) {
    try {
      data = JSON.parse(text)
    } catch (_) {
      data = text
    }
  }

  if (!response.ok) {
    const detail = data?.detail
    const message = typeof data === 'string'
      ? data
      : typeof detail === 'string'
        ? detail
        : detail?.message || data?.message || `Emergency API error: ${response.status}`
    throw new Error(message)
  }

  return data
}

export async function fetchEmergencyRequests() {
  const response = await fetch(EMERGENCY_API_URL, { method: 'GET' })
  const payload = await parseResponse(response)

  return unwrapEmergencyList(payload).map(normalizeEmergencyRequest)
}

export async function resolveEmergencyRequest(request) {
  const response = await fetch(`${EMERGENCY_API_URL}/resolve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      userID: request.userID || request.visitor_id,
      timestamp: request.timestamp || request.created_at,
    }),
  })

  return parseResponse(response)
}
