// Thin wrapper around the hackViz FastAPI backend (proxied by Vite at /api).
const BASE = import.meta.env.VITE_API_BASE || ''

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message)
    this.status = status
    this.body = body
  }
}

async function request(path, { method = 'GET', body, signal } = {}) {
  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      signal,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new ApiError('Backend unreachable - is FastAPI running on port 8000?', 0)
  }
  const text = await res.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!res.ok) {
    const msg = (data && (data.detail || data.error)) || `HTTP ${res.status}`
    throw new ApiError(typeof msg === 'string' ? msg : JSON.stringify(msg), res.status, data)
  }
  return data
}

const qs = (params = {}) => {
  const p = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  return p.length ? '?' + new URLSearchParams(p).toString() : ''
}

export const api = {
  health: () => request('/api/health'),
  status: () => request('/api/status'),
  stats: () => request('/api/stats'),
  employees: () => request('/api/employees'),
  employee: (id) => request(`/api/employees/${encodeURIComponent(id)}`),
  createEmployee: (body) => request('/api/employees', { method: 'POST', body }),
  employeeActivity: (id, params) => request(`/api/employees/${encodeURIComponent(id)}/activity${qs(params)}`),
  employeeAnomalies: (id) => request(`/api/employees/${encodeURIComponent(id)}/anomalies`),
  employeeTimeline: (id) => request(`/api/employees/${encodeURIComponent(id)}/timeline`),
  activity: (params) => request(`/api/activity${qs(params)}`),
  event: (id) => request(`/api/activity/${id}`),
  anomalies: (params) => request(`/api/anomalies${qs(params)}`),
  anomaly: (id) => request(`/api/anomalies/${id}`),
  analyze: (id, force = false) => request(`/api/analyze/${encodeURIComponent(id)}${qs({ force: force || undefined })}`, { method: 'POST' }),
  analysisStatus: () => request('/api/analysis/status'),
  exportUrl: (employeeId) => `${BASE}/api/export/activity.csv${qs({ employee_id: employeeId })}`,
}
