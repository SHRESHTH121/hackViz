// Converts every PNG in <dir> to a JPEG (max 1400 px wide, white background) for fast pdfLaTeX embedding.
// Usage: node to_jpeg.mjs <dir>
import puppeteer from 'puppeteer-core'
import fs from 'node:fs'
import path from 'node:path'

const dir = process.argv[2]
const MAXW = 1400
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})
const page = await browser.newPage()
for (const f of fs.readdirSync(dir).filter((n) => n.endsWith('.png'))) {
  const buf = fs.readFileSync(path.join(dir, f))
  const w0 = buf.readUInt32BE(16)
  const h0 = buf.readUInt32BE(20)
  const w = Math.min(MAXW, w0)
  const h = Math.round((h0 * w) / w0)
  await page.setViewport({ width: w, height: h, deviceScaleFactor: 1 })
  await page.setContent(`<html><body style="margin:0;background:#fff"><img style="display:block;width:${w}px;height:${h}px" src="data:image/png;base64,${buf.toString('base64')}"></body></html>`)
  await page.waitForSelector('img')
  await page.evaluate(() => document.querySelector('img').decode())
  const out = path.join(dir, f.replace(/\.png$/, '.jpg'))
  await page.screenshot({ path: out, type: 'jpeg', quality: 88, clip: { x: 0, y: 0, width: w, height: h } })
  console.log(f, `${w0}x${h0} ->`, `${w}x${h}`, fs.statSync(out).size, 'bytes')
}
await browser.close()
