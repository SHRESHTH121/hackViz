// Renders every SVG in <svg-dir> to a 2x PNG in <png-dir> using the installed Google Chrome.
// Usage: node render_diagrams.mjs <svg-dir> <png-dir>
// Run 'npm install' in this folder first.
import puppeteer from 'puppeteer-core'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))

const [, , svgDir, outDir] = process.argv
fs.mkdirSync(outDir, { recursive: true })
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})
const page = await browser.newPage()
for (const f of fs.readdirSync(svgDir).filter((n) => n.endsWith('.svg'))) {
  const svg = fs.readFileSync(path.join(svgDir, f), 'utf8')
  const m = svg.match(/width="(\d+)" height="(\d+)"/)
  const w = Number(m[1])
  const h = Number(m[2])
  await page.setViewport({ width: w, height: h, deviceScaleFactor: 2 })
  await page.setContent(`<html><body style="margin:0;background:#fff">${svg}</body></html>`)
  await page.screenshot({ path: path.join(outDir, f.replace(/\.svg$/, '.png')), clip: { x: 0, y: 0, width: w, height: h } })
  console.log('rendered', f, `${w}x${h}`)
}
await browser.close()
