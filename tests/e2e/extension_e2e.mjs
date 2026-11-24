// hackViz end-to-end test.
// Drives the locally installed Google Chrome with the unpacked hackViz extension loaded,
// performs REAL browsing (navigations + downloads), and verifies the whole pipeline:
// extension -> FastAPI -> PostgreSQL -> Ollama analysis -> React dashboard.
//
// Prerequisites: backend on :8000, frontend on :5173, Ollama with qwen2.5:3b.
// Usage (from tests/e2e):  node extension_e2e.mjs
import puppeteer from 'puppeteer-core'
import http from 'node:http'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const EXT = path.resolve(HERE, '../../extension')
const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const API = process.env.HACKVIZ_API || 'http://localhost:8000'
const UI = process.env.HACKVIZ_UI || 'http://localhost:5173'
const EMP = process.env.E2E_EMPLOYEE || 'EMP011'
const HEADLESS = process.env.E2E_HEADED ? false : true
const SHOTS = path.join(HERE, 'screens')
fs.mkdirSync(SHOTS, { recursive: true })

const results = []
const t0 = Date.now()
const log = (step, ok, detail = '') => {
  results.push({ step, ok, detail, at_s: Math.round((Date.now() - t0) / 1000) })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${step}${detail ? '  — ' + detail : ''}`)
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
async function api(p, opts = {}) {
  const r = await fetch(API + p, { headers: { 'Content-Type': 'application/json' }, ...opts })
  const text = await r.text()
  let data; try { data = JSON.parse(text) } catch { data = text }
  return { status: r.status, data }
}
async function waitFor(fn, timeoutMs, everyMs = 1500) {
  const end = Date.now() + timeoutMs
  while (Date.now() < end) { const v = await fn(); if (v) return v; await sleep(everyMs) }
  return null
}

// A tiny local file server so a download can always be tested even if the internet is flaky.
function startFileServer() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      if (req.url.startsWith('/files/sample_report.csv')) {
        res.writeHead(200, { 'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename="sample_report.csv"' })
        res.end('col_a,col_b\n1,2\n3,4\n')
      } else { res.writeHead(200, { 'Content-Type': 'text/html' }); res.end('<h1>local test page</h1>') }
    })
    srv.listen(8765, '127.0.0.1', () => resolve(srv))
  })
}

async function main() {
  // ---------------------------------------------------------------- backend + employee
  const h = await api('/api/health')
  log('Backend health', h.status === 200 && h.data.database === 'ok', JSON.stringify(h.data.database_info))
  const st = await api('/api/status')
  log('Ollama model available', !!st.data.ollama?.model_available, st.data.ollama?.model)
  const emps = await api('/api/employees')
  log('Initial employees present', emps.data.filter((e) => /^EMP0(0[1-9]|10)$/.test(e.employee_id)).length === 10, `${emps.data.length} employees in directory`)
  const created = await api('/api/employees', { method: 'POST', body: JSON.stringify({ employee_id: EMP, name: 'Sara Iyer', role: 'Finance Analyst', department: 'Finance', email: 'sara.iyer@corvane.example' }) })
  log(`Add employee ${EMP} (Finance Analyst)`, created.status === 201 || created.status === 409, `HTTP ${created.status}`)

  const fileSrv = await startFileServer()
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'hackviz-e2e-'))
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: HEADLESS, pipe: true, enableExtensions: [EXT], userDataDir: profile,
    args: ['--no-first-run', '--no-default-browser-check', '--disable-features=DownloadBubble'],
  })
  try {
    // ---------------------------------------------------------------- extension loads
    const sw = await browser.waitForTarget((t) => t.type() === 'service_worker' && t.url().endsWith('/background.js'), { timeout: 20000 })
    const extId = new URL(sw.url()).host
    log('Extension loads in Chrome (MV3 service worker running)', !!extId, `id ${extId}`)
    const dlDir = path.join(HERE, 'downloads'); fs.mkdirSync(dlDir, { recursive: true })
    const cdp = await browser.target().createCDPSession()
    await cdp.send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: dlDir, eventsEnabled: true })

    // ---------------------------------------------------------------- pairing via popup UI
    const popup = await browser.newPage()
    await popup.goto(`chrome-extension://${extId}/popup.html`)
    await popup.waitForSelector('#backendText')
    await waitFor(async () => (await popup.$eval('#backendText', (e) => e.textContent)).startsWith('Connected'), 10000, 500)
    log('Popup shows backend connectivity', (await popup.$eval('#backendText', (e) => e.textContent)).startsWith('Connected'))

    await popup.type('#empId', 'EMP999')
    await popup.click('#pairBtn')
    let m = await waitFor(async () => { const t = await popup.$eval('#pairMsg', (e) => e.textContent); return /confirm/i.test(t) && t }, 5000, 300)
    log('Pairing blocked until monitoring notice is confirmed', !!m, m || '')
    await popup.click('#consent')
    await popup.click('#pairBtn')
    m = await waitFor(async () => { const t = await popup.$eval('#pairMsg', (e) => e.textContent); return /does not exist/i.test(t) && t }, 8000, 300)
    log('Invalid employee ID rejected', !!m, m || '')

    await popup.click('#empId', { clickCount: 3 }); await popup.keyboard.press('Backspace')
    await popup.type('#empId', EMP.toLowerCase())
    await popup.click('#pairBtn')
    const pname = await waitFor(async () => { const t = await popup.$eval('#pName', (e) => e.textContent); return t && t !== EMP ? t : null }, 10000, 300)
    const prole = await popup.$eval('#pRole', (e) => e.textContent)
    log('Valid employee paired; name and role retrieved from PostgreSQL', pname === 'Sara Iyer' && prole.includes('Finance Analyst'), `${pname} — ${prole}`)
    await popup.screenshot({ path: path.join(SHOTS, '01_extension_paired.png') })

    // ---------------------------------------------------------------- real browsing
    const before = (await api(`/api/activity?employee_id=${EMP}&source=chrome_extension&limit=1`)).data.total
    const tab = await browser.newPage()
    const urls = [
      'https://example.com/',
      'https://www.wikipedia.org/',
      'https://www.python.org/',
      'https://github.com/',
      'https://developer.mozilla.org/en-US/',
      'https://wetransfer.com/',
      `http://127.0.0.1:8765/report-viewer?token=SECRET123`,
    ]
    const visited = []
    for (const u of urls) {
      try { await tab.goto(u, { waitUntil: 'domcontentloaded', timeout: 30000 }); visited.push(u) }
      catch (e) { console.log(`   (navigation to ${u} failed: ${e.message.split('\n')[0]})`) }
      await sleep(1200)
    }
    log('Real top-level navigations performed in Chrome', visited.length >= 4, `${visited.length}/${urls.length} pages loaded`)

    // downloads: one from the internet, one from a local server
    const downloads = []
    for (const u of ['https://github.com/octocat/Hello-World/archive/refs/heads/master.zip', 'http://127.0.0.1:8765/files/sample_report.csv']) {
      try { await tab.goto(u, { timeout: 30000 }) } catch { /* navigation to a download aborts by design */ }
      downloads.push(u)
      await sleep(4000)
    }
    const files = fs.readdirSync(dlDir)
    log('Real file downloads completed by Chrome', files.length >= 1, files.join(', '))

    // ---------------------------------------------------------------- events reach backend + PostgreSQL
    const got = await waitFor(async () => {
      const r = (await api(`/api/activity?employee_id=${EMP}&source=chrome_extension&limit=200`)).data
      const nav = r.items.filter((e) => e.event_type === 'navigation').length
      const dl = r.items.filter((e) => e.event_type === 'download').length
      return nav >= visited.length && dl >= 1 ? r : null
    }, 60000)
    const items = got ? got.items : (await api(`/api/activity?employee_id=${EMP}&source=chrome_extension&limit=200`)).data.items
    const navs = items.filter((e) => e.event_type === 'navigation')
    const dls = items.filter((e) => e.event_type === 'download')
    log('Navigation events stored in PostgreSQL', navs.length >= visited.length, `${navs.length} navigation events (${before} before test)`)
    log('Download events stored with filename', dls.length >= 1 && dls.every((d) => d.filename), dls.map((d) => `${d.domain}:${d.filename}`).join(', '))
    const tokenLeak = items.some((e) => (e.url || '').includes('SECRET123') || (e.url || '').includes('?'))
    log('Query strings / tokens stripped from URLs', !tokenLeak)
    const one = await api(`/api/activity/${items[0].id}`)
    log('Event retrievable by ID from PostgreSQL', one.status === 200 && one.data.source === 'chrome_extension', `#${items[0].id} ${one.data.domain}`)
    const status = await api('/api/status')
    const pe = status.data.monitoring.paired_extensions.find((p) => p.employee_id === EMP)
    log('Monitoring status: paired AND transmitting', !!pe && pe.transmitting && pe.events_received >= navs.length, pe ? `events_received=${pe.events_received}, connection=${pe.connection}` : 'not found')
    const sent = await popup.$eval('#sent', (e) => Number(e.textContent))
    log('Popup reports last successful transmission', sent >= navs.length, `events sent ${sent}, last send ${await popup.$eval('#lastSend', (e) => e.textContent)}`)

    // ---------------------------------------------------------------- real Ollama analysis
    const t1 = Date.now()
    const an = await api(`/api/analyze/${EMP}?wait=true&timeout=900`, { method: 'POST' })
    const job = an.data.job
    log('Ollama analysis job completed', an.status === 200 && job?.state === 'done', `${job?.state} ${job?.error || ''} in ${Math.round((Date.now() - t1) / 1000)}s (mode ${job?.mode})`)
    const list = (await api(`/api/employees/${EMP}/anomalies`)).data
    const latest = list[0]
    log('Assessment saved in PostgreSQL', !!latest, latest ? `alert #${latest.id}: is_anomaly=${latest.is_anomaly} risk=${latest.risk_level} conf=${latest.confidence}` : '')
    if (latest) {
      const det = (await api(`/api/anomalies/${latest.id}`)).data
      const liveIds = new Set(items.map((e) => e.id))
      const covered = det.analyzed_event_ids.filter((i) => liveIds.has(i)).length
      log('Analysis covered the live browser events', covered >= Math.min(items.length, 5), `${covered} live events in analyzed batch of ${det.analyzed_event_ids.length}`)
      let evOk = det.evidence_event_ids.every((i) => det.analyzed_event_ids.includes(i))
      for (const id of det.evidence_event_ids) {
        const r = await api(`/api/activity/${id}`)
        evOk = evOk && r.status === 200 && r.data.employee_id === EMP
      }
      log('Evidence IDs reference real supplied records of this employee', evOk, `evidence [${det.evidence_event_ids.join(', ')}]`)
      console.log(`\n   MODEL REASON: ${det.reason}\n   RECOMMENDED: ${det.recommended_action}\n   INDICATORS: ${det.indicators.map((i) => i.code).join(', ') || 'none'}\n`)
      results.push({ step: 'assessment_detail', ok: true, detail: { id: det.id, risk: det.risk_level, is_anomaly: det.is_anomaly, confidence: det.confidence, reason: det.reason, recommended_action: det.recommended_action, evidence: det.evidence_event_ids, indicators: det.indicators.map((i) => i.code), duration_ms: det.duration_ms } })

      // ---------------------------------------------------------------- frontend shows it
      const ui = await browser.newPage()
      await ui.setViewport({ width: 1500, height: 1000 })
      await ui.goto(`${UI}/#/`, { waitUntil: 'networkidle2', timeout: 30000 })
      const dirOk = await waitFor(async () => (await ui.content()).includes(EMP) && (await ui.content()).includes('Rohan Sharma'), 15000, 800)
      log('Dashboard lists employees incl. new employee', !!dirOk)
      await ui.screenshot({ path: path.join(SHOTS, '02_dashboard.png'), fullPage: true })
      await ui.goto(`${UI}/#/alerts`, { waitUntil: 'networkidle2' })
      await ui.select('select.select', 'false')
      const alertShown = await waitFor(async () => (await ui.content()).includes(`Alert #${latest.id}`), 15000, 800)
      log('Alert visible in the Anomaly Alerts page', !!alertShown, `Alert #${latest.id}`)
      await ui.screenshot({ path: path.join(SHOTS, '03_alerts.png'), fullPage: true })
      await ui.goto(`${UI}/#/employees/${EMP}`, { waitUntil: 'networkidle2' })
      await waitFor(async () => (await ui.content()).includes('Current risk assessment'), 10000, 500)
      const chip = det.evidence_event_ids[0]
      if (chip) {
        const clicked = await ui.evaluate((id) => {
          const b = [...document.querySelectorAll('button.ev-chip')].find((x) => x.textContent === `#${id}`)
          if (b) b.click(); return !!b
        }, chip)
        const modal = clicked && await waitFor(async () => (await ui.content()).includes(`Activity record`), 8000, 400)
        log('Clicking an evidence ID opens the original record', !!modal, `#${chip}`)
      }
      await ui.screenshot({ path: path.join(SHOTS, '04_employee_profile.png'), fullPage: true })
      await ui.goto(`${UI}/#/activity`, { waitUntil: 'networkidle2' })
      const feedOk = await waitFor(async () => (await ui.content()).includes(String(items[0].id)), 10000, 800)
      log('Live activity feed shows extension events', !!feedOk)
      await ui.screenshot({ path: path.join(SHOTS, '05_live_feed.png') })
      await ui.goto(`${UI}/#/monitoring`, { waitUntil: 'networkidle2' })
      await sleep(1500)
      await ui.screenshot({ path: path.join(SHOTS, '06_monitoring.png') })
    }

    // ---------------------------------------------------------------- CSV export
    const csv = await fetch(`${API}/api/export/activity.csv?employee_id=${EMP}`).then((r) => r.text())
    const csvRows = csv.trim().split('\n').length - 1
    const total = (await api(`/api/activity?employee_id=${EMP}&limit=1`)).data.total
    log('CSV export for employee matches stored activity', csvRows === total, `${csvRows} rows`)

    // ---------------------------------------------------------------- disconnect stops collection
    await popup.bringToFront()
    await popup.click('#unpairBtn')
    await sleep(1500)
    const afterUnpair = (await api(`/api/activity?employee_id=${EMP}&source=chrome_extension&limit=1`)).data.total
    try { await tab.goto('https://example.com/?after=unpair', { waitUntil: 'domcontentloaded', timeout: 20000 }) } catch { /* ignore */ }
    await sleep(5000)
    const afterNav = (await api(`/api/activity?employee_id=${EMP}&source=chrome_extension&limit=1`)).data.total
    log('No activity collected after disconnecting', afterNav === afterUnpair, `${afterUnpair} -> ${afterNav}`)
  } catch (e) {
    log('Unexpected error', false, e.stack)
  } finally {
    await browser.close()
    fileSrv.close()
    fs.rmSync(profile, { recursive: true, force: true })
  }
  const passed = results.filter((r) => r.ok).length
  const failed = results.filter((r) => !r.ok).length
  fs.writeFileSync(path.join(HERE, 'e2e_results.json'), JSON.stringify({ run_at: new Date().toISOString(), passed, failed, results }, null, 2))
  console.log(`\n${passed} passed, ${failed} failed  (results: tests/e2e/e2e_results.json, screenshots: tests/e2e/screens/)`)
  process.exit(failed ? 1 : 0)
}

main()
