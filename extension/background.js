/* hackViz Activity Monitor - MV3 service worker.
 *
 * Collects ONLY browser metadata for a paired, verified employee:
 *   - top-level navigations (URL without query string/fragment, domain, time, tab id, transition type)
 *   - completed downloads (source URL without query, domain, file *name* only, size, MIME type)
 * Never collects page content, titles, form data, keystrokes, cookies, credentials or tokens.
 * Events are queued in chrome.storage.local and sent to the hackViz backend in the background,
 * so browsing is never blocked - and the backend never runs LLM inference inside the request.
 */
const DEFAULT_BACKEND = 'http://localhost:8000'
const MAX_QUEUE = 500
const BATCH = 50
const DEDUPE_MS = 4000
const VERSION = chrome.runtime.getManifest().version

// ---------------------------------------------------------------- storage (serialised)
let chain = Promise.resolve()
const withStore = (fn) => (chain = chain.then(async () => {
  const s = await chrome.storage.local.get(null)
  const patch = await fn(s)
  if (patch) await chrome.storage.local.set(patch)
  return { ...s, ...(patch || {}) }
}).catch((e) => { console.error('[hackViz] storage error', e) }))

const getState = () => chrome.storage.local.get(null)
const backendUrl = (s) => (s.backendUrl || DEFAULT_BACKEND).replace(/\/+$/, '')

// ---------------------------------------------------------------- helpers
function sanitizeUrl(raw) {
  try {
    const u = new URL(raw)
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return null
    // Strip credentials, query string and fragment: they can carry tokens or personal data.
    return { url: `${u.protocol}//${u.host.toLowerCase()}${u.pathname || '/'}`, domain: u.hostname.toLowerCase() }
  } catch { return null }
}

function isOwnBackend(s, domainUrl) {
  try {
    const b = new URL(backendUrl(s))
    const u = new URL(domainUrl)
    return u.host === b.host || ((u.hostname === 'localhost' || u.hostname === '127.0.0.1') && u.port === '5173')
  } catch { return false }
}

const baseName = (p) => (p || '').split(/[\\/]/).pop().slice(0, 255)
const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`)
const recent = new Map() // tabId -> {url, t}

// ---------------------------------------------------------------- queue + transmit
async function enqueue(ev) {
  const s = await getState()
  const p = s.pairing
  if (!p || !p.session_token || p.invalid) return // no valid employee paired: collect nothing
  if (isOwnBackend(s, ev.url)) return // don't record the monitoring dashboard itself
  const full = {
    client_event_id: uuid(),
    employee_id: p.employee_id,
    session_token: p.session_token,
    source: 'chrome_extension',
    timestamp: new Date().toISOString(),
    ...ev,
  }
  await withStore((st) => {
    const q = Array.isArray(st.queue) ? st.queue : []
    q.push(full)
    const dropped = Math.max(0, q.length - MAX_QUEUE)
    return { queue: q.slice(-MAX_QUEUE), droppedEvents: (st.droppedEvents || 0) + dropped }
  })
  flush()
}

let flushing = false
async function flush() {
  if (flushing) return
  flushing = true
  try {
    for (let round = 0; round < 10; round++) {
      const s = await getState()
      const q = Array.isArray(s.queue) ? s.queue : []
      if (!q.length || !s.pairing || s.pairing.invalid) break
      const batch = q.slice(0, BATCH)
      let res
      try {
        res = await fetch(`${backendUrl(s)}/api/activity/batch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ events: batch }),
        })
      } catch (e) {
        await withStore(() => ({ backendOk: false, lastError: 'Backend unavailable - events kept in local queue', lastErrorAt: new Date().toISOString() }))
        break
      }
      if (res.status === 422 || res.status === 400) {
        // Whole batch malformed: drop it rather than retry forever, but record why.
        const body = await res.text()
        await withStore((st) => ({ queue: (st.queue || []).slice(batch.length), lastError: `Rejected by backend: ${body.slice(0, 200)}`, lastErrorAt: new Date().toISOString(), backendOk: true }))
        continue
      }
      if (!res.ok) {
        await withStore(() => ({ backendOk: false, lastError: `Backend error HTTP ${res.status}`, lastErrorAt: new Date().toISOString() }))
        break
      }
      const data = await res.json()
      const results = data.results || []
      const authFail = results.find((r) => r.status === 401 || r.status === 403 || r.status === 404)
      const accepted = results.filter((r) => r.id != null && !r.duplicate).length
      const done = new Set(results.filter((r) => r.id != null || (r.status && r.status < 500)).map((r) => r.client_event_id))
      await withStore((st) => {
        const patch = {
          queue: (st.queue || []).filter((e) => !done.has(e.client_event_id)),
          backendOk: true,
          eventsSent: (st.eventsSent || 0) + accepted,
        }
        if (accepted) patch.lastSuccessAt = new Date().toISOString()
        if (authFail) {
          patch.pairing = { ...(st.pairing || {}), invalid: true }
          patch.lastError = `Pairing rejected: ${authFail.error}. Pair again.`
          patch.lastErrorAt = new Date().toISOString()
          patch.queue = []
        } else if (accepted) patch.lastError = null
        return patch
      })
      if (authFail) break
    }
  } finally {
    flushing = false
    updateBadge()
  }
}

async function heartbeat() {
  const s = await getState()
  if (!s.pairing || s.pairing.invalid) return
  try {
    const r = await fetch(`${backendUrl(s)}/api/extension/heartbeat`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_token: s.pairing.session_token }),
    })
    if (r.status === 401) {
      await withStore((st) => ({ pairing: { ...(st.pairing || {}), invalid: true }, lastError: 'Pairing no longer valid on the backend - pair again', lastErrorAt: new Date().toISOString(), backendOk: true }))
    } else await withStore(() => (r.ok ? { backendOk: true, lastHeartbeatAt: new Date().toISOString() } : { backendOk: false }))
  } catch {
    await withStore(() => ({ backendOk: false }))
  }
  updateBadge()
}

async function updateBadge() {
  const s = await getState()
  const on = s.pairing && !s.pairing.invalid
  await chrome.action.setBadgeText({ text: on ? (s.backendOk === false ? '!' : 'ON') : '' })
  await chrome.action.setBadgeBackgroundColor({ color: on ? (s.backendOk === false ? '#f0a830' : '#2fbf71') : '#7d8aa0' })
}

// ---------------------------------------------------------------- collectors
function onNav(details, kind) {
  if (details.frameId !== 0) return // top-level only
  const clean = sanitizeUrl(details.url)
  if (!clean) return
  const prev = recent.get(details.tabId)
  const now = Date.now()
  if (prev && prev.url === clean.url && now - prev.t < DEDUPE_MS) return
  recent.set(details.tabId, { url: clean.url, t: now })
  enqueue({
    event_type: 'navigation',
    url: clean.url,
    domain: clean.domain,
    metadata: {
      tab_id: details.tabId,
      transition: details.transitionType || (kind === 'spa' ? 'in_page' : undefined),
      qualifiers: details.transitionQualifiers || [],
      navigation_kind: kind,
    },
  })
}

chrome.webNavigation.onCommitted.addListener((d) => onNav(d, 'commit'))
chrome.webNavigation.onHistoryStateUpdated.addListener((d) => onNav(d, 'spa'))
chrome.tabs?.onRemoved?.addListener((tabId) => recent.delete(tabId))

chrome.downloads.onChanged.addListener(async (delta) => {
  if (!delta.state || delta.state.current !== 'complete') return
  const [item] = await chrome.downloads.search({ id: delta.id })
  if (!item) return
  let clean = sanitizeUrl(item.finalUrl || item.url)
  let via = 'direct'
  if (!clean && item.referrer) { clean = sanitizeUrl(item.referrer); via = 'referrer' } // blob:/data: downloads
  if (!clean) return
  enqueue({
    event_type: 'download',
    url: clean.url,
    domain: clean.domain,
    filename: baseName(item.filename), // file name only - never the local directory path
    metadata: {
      file_size_kb: item.fileSize > 0 ? Math.round(item.fileSize / 1024) : null,
      mime: (item.mime || '').slice(0, 80),
      url_source: via,
      danger: item.danger || 'safe',
    },
  })
})

// ---------------------------------------------------------------- popup API
async function api(path, body) {
  const s = await getState()
  const r = await fetch(`${backendUrl(s)}${path}`, {
    method: body ? 'POST' : 'GET', headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const text = await r.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = { detail: text } }
  return { ok: r.ok, status: r.status, data }
}

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  (async () => {
    try {
      if (msg.type === 'status') {
        const s = await getState()
        let health = null
        try { health = (await api('/api/health')).data } catch { health = null }
        await withStore(() => ({ backendOk: !!health }))
        const st = await getState()
        const { queue, ...rest } = st
        reply({ ok: true, state: { ...rest, queueLength: (queue || []).length, backendUrl: backendUrl(s), health } })
      } else if (msg.type === 'pair') {
        const s = await getState()
        if (s.pairing && s.pairing.session_token && !s.pairing.invalid) {
          try { await api('/api/extension/unpair', { session_token: s.pairing.session_token }) } catch { /* best effort */ }
        }
        let r
        try { r = await api('/api/extension/pair', { employee_id: msg.employeeId, extension_version: VERSION }) }
        catch { return reply({ ok: false, error: `Backend not reachable at ${backendUrl(s)}` }) }
        if (!r.ok) return reply({ ok: false, error: r.data?.detail || `Pairing failed (HTTP ${r.status})` })
        const p = r.data
        await withStore(() => ({
          pairing: { employee_id: p.employee_id, employee_name: p.employee_name, role: p.role, department: p.department, session_token: p.session_token, paired_at: p.paired_at },
          queue: [], eventsSent: 0, lastSuccessAt: null, lastError: null, consent: true, backendOk: true,
        }))
        updateBadge()
        reply({ ok: true, pairing: p })
      } else if (msg.type === 'unpair') {
        const s = await getState()
        if (s.pairing?.session_token) {
          try { await api('/api/extension/unpair', { session_token: s.pairing.session_token }) } catch { /* offline: local unpair still applies */ }
        }
        await withStore(() => ({ pairing: null, queue: [] }))
        updateBadge()
        reply({ ok: true })
      } else if (msg.type === 'setBackend') {
        const u = String(msg.url || '').trim()
        if (!/^http:\/\/(localhost|127\.0\.0\.1):\d+$/.test(u)) return reply({ ok: false, error: 'Use http://localhost:PORT or http://127.0.0.1:PORT' })
        await withStore(() => ({ backendUrl: u }))
        reply({ ok: true })
      } else if (msg.type === 'flush') {
        await flush(); await heartbeat()
        reply({ ok: true })
      } else reply({ ok: false, error: 'unknown message' })
    } catch (e) {
      reply({ ok: false, error: String(e && e.message || e) })
    }
  })()
  return true // async reply
})

// ---------------------------------------------------------------- lifecycle
chrome.alarms.create('hackviz-tick', { periodInMinutes: 0.5 })
chrome.alarms.onAlarm.addListener((a) => { if (a.name === 'hackviz-tick') { flush(); heartbeat() } })
chrome.runtime.onStartup.addListener(() => { flush(); heartbeat() })
chrome.runtime.onInstalled.addListener(() => updateBadge())
