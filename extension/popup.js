const $ = (id) => document.getElementById(id)
const send = (msg) => new Promise((res) => chrome.runtime.sendMessage(msg, (r) => res(r || { ok: false, error: chrome.runtime.lastError?.message })))
let switching = false

const ago = (iso) => {
  if (!iso) return 'never'
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${Math.floor(s)}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  return new Date(iso).toLocaleString()
}

function msg(el, text, kind) {
  el.textContent = text || ''
  el.className = `msg ${text ? kind : ''}`
}

async function refresh() {
  const r = await send({ type: 'status' })
  if (!r.ok) return msg($('lastErr'), r.error, 'err')
  const s = r.state
  const p = s.pairing
  const online = !!s.health
  $('backendDot').className = `dot ${online ? 'ok' : 'bad'}`
  $('backendText').textContent = online ? `Connected (${s.backendUrl.replace('http://', '')})` : `Unreachable (${s.backendUrl.replace('http://', '')})`
  $('lastSend').textContent = ago(s.lastSuccessAt)
  $('sent').textContent = s.eventsSent || 0
  $('queued').textContent = s.queueLength || 0
  if (document.activeElement !== $('backendUrl')) $('backendUrl').value = s.backendUrl

  const paired = p && !p.invalid
  if (!p) $('monText').textContent = 'Not monitoring (no employee paired)'
  else if (p.invalid) $('monText').textContent = 'Stopped — pairing invalid'
  else if (!online) $('monText').textContent = 'Paired — backend offline, queuing'
  else $('monText').textContent = s.lastSuccessAt ? 'Active — transmitting' : 'Active — waiting for first event'
  $('monText').style.color = paired ? (online ? 'var(--green)' : 'var(--amber)') : 'var(--muted)'
  msg($('lastErr'), s.lastError ? `${s.lastError} (${ago(s.lastErrorAt)})` : '', 'err')

  $('pairedBox').classList.toggle('hidden', !p)
  $('pairBox').classList.toggle('hidden', !!p && !switching)
  $('cancelSwitch').classList.toggle('hidden', !switching)
  if (p) {
    $('pName').textContent = p.employee_name || p.employee_id
    $('pId').textContent = p.employee_id
    $('pRole').textContent = `${p.role || ''}${p.department ? ' · ' + p.department : ''}`
    $('pSince').textContent = `Paired ${ago(p.paired_at)}`
  }
  if (s.consent) $('consent').checked = true
}

$('pairBtn').addEventListener('click', async () => {
  const id = $('empId').value.trim().toUpperCase()
  if (!/^[A-Z0-9][A-Z0-9_-]{1,31}$/.test(id)) return msg($('pairMsg'), 'Enter a valid employee ID (e.g. EMP002).', 'err')
  if (!$('consent').checked) return msg($('pairMsg'), 'Please confirm the monitoring notice first.', 'err')
  $('pairBtn').disabled = true
  msg($('pairMsg'), 'Verifying employee with the backend…', 'ok')
  const r = await send({ type: 'pair', employeeId: id })
  $('pairBtn').disabled = false
  if (!r.ok) return msg($('pairMsg'), r.error, 'err')
  switching = false
  $('empId').value = ''
  msg($('pairMsg'), `Paired with ${r.pairing.employee_name} (${r.pairing.employee_id}). Monitoring started.`, 'ok')
  refresh()
})
$('empId').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('pairBtn').click() })
$('switchBtn').addEventListener('click', () => { switching = true; msg($('pairMsg'), '', ''); refresh(); $('empId').focus() })
$('cancelSwitch').addEventListener('click', () => { switching = false; refresh() })
$('unpairBtn').addEventListener('click', async () => {
  await send({ type: 'unpair' })
  switching = false
  msg($('pairMsg'), 'Disconnected. No activity is being collected.', 'ok')
  refresh()
})
$('saveBackend').addEventListener('click', async () => {
  const r = await send({ type: 'setBackend', url: $('backendUrl').value })
  if (!r.ok) msg($('lastErr'), r.error, 'err')
  refresh()
})
$('flushBtn').addEventListener('click', async () => { await send({ type: 'flush' }); refresh() })

refresh()
setInterval(refresh, 3000)
