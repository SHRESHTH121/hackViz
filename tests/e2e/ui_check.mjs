// UI verification against the running dashboard: evidence-ID click opens the original record,
// all pages render without console errors. Saves screenshots to tests/e2e/screens/.
// Usage: node ui_check.mjs [EMPLOYEE_ID]
import puppeteer from 'puppeteer-core'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const SHOTS = path.join(HERE, 'screens'); fs.mkdirSync(SHOTS, { recursive: true })
const UI = process.env.HACKVIZ_UI || 'http://localhost:5173'
const API = process.env.HACKVIZ_API || 'http://localhost:8000'
const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
let failed = 0
const check = (name, ok, detail = '') => { if (!ok) failed++; console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`) }

const alerts = await fetch(`${API}/api/anomalies?only_anomalies=true`).then((r) => r.json())
const alert = alerts.find((a) => a.evidence_event_ids.length)
const emp = process.argv[2] || alert?.employee_id || 'EMP002'

const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--no-first-run'] })
const page = await browser.newPage()
const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
page.on('pageerror', (e) => errors.push(String(e)))
await page.setViewport({ width: 1500, height: 1000 })

for (const [name, hash] of [['dashboard', '#/'], ['alerts', '#/alerts'], ['activity', '#/activity'], ['monitoring', '#/monitoring'], ['profile', `#/employees/${emp}`]]) {
  await page.goto(`${UI}/${hash}`, { waitUntil: 'networkidle2', timeout: 30000 })
  await sleep(1500)
  await page.screenshot({ path: path.join(SHOTS, `ui_${name}.png`), fullPage: name !== 'activity' })
  check(`Page renders: ${name}`, (await page.$('.content')) !== null)
}

if (alert) {
  await page.goto(`${UI}/#/alerts`, { waitUntil: 'networkidle2' })
  await sleep(1000)
  const id = alert.evidence_event_ids[0]
  const clicked = await page.evaluate((id) => {
    const b = [...document.querySelectorAll('button.ev-chip')].find((x) => x.textContent === `#${id}`)
    if (b) b.click(); return !!b
  }, id)
  await sleep(1500)
  const modal = await page.$eval('.modal', (m) => m.innerText).catch(() => '')
  const rec = await fetch(`${API}/api/activity/${id}`).then((r) => r.json())
  check('Evidence chip opens original PostgreSQL record', clicked && modal.includes(`#${id}`) && modal.includes(rec.domain || rec.event_type), `#${id} → ${rec.event_type} ${rec.domain || ''}`)
  await page.screenshot({ path: path.join(SHOTS, 'ui_evidence_modal.png') })
  await page.keyboard.press('Escape')
  // expand the analyzed sequence + raw output
  await page.evaluate(() => [...document.querySelectorAll('button')].find((b) => b.textContent.includes('Activity sequence'))?.click())
  await sleep(1500)
  const txt = await page.evaluate(() => document.body.innerText)
  check('Alert detail shows indicators, sequence and raw model response', txt.includes('Raw model response') && txt.includes('supporting indicators'))
  await page.screenshot({ path: path.join(SHOTS, 'ui_alert_expanded.png'), fullPage: true })
} else check('An alert with evidence exists', false)

check('No browser console errors', errors.length === 0, errors.slice(0, 3).join(' | '))
await browser.close()
console.log(failed ? `${failed} check(s) failed` : 'all UI checks passed')
process.exit(failed ? 1 : 0)
