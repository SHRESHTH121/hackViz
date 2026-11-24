// Builds contact sheets (grids of page thumbnails) from PNG pages, for layout review.
// Usage: node contact_sheet.mjs <png-dir> <out-prefix> [perSheet]
import puppeteer from 'puppeteer-core'
import fs from 'node:fs'
import path from 'node:path'

const [, , dir, outPrefix, per = '8'] = process.argv
const files = fs.readdirSync(dir).filter((n) => /^p-\d+\.png$/.test(n)).sort()
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})
const page = await browser.newPage()
const n = Number(per)
for (let k = 0; k < files.length; k += n) {
  const chunk = files.slice(k, k + n)
  const imgs = chunk
    .map((f) => {
      const b64 = fs.readFileSync(path.join(dir, f)).toString('base64')
      return `<div style="display:inline-block;margin:4px;text-align:center;font:12px sans-serif">
        <img src="data:image/png;base64,${b64}" style="width:330px;border:1px solid #999"><br>${f}</div>`
    })
    .join('')
  await page.setViewport({ width: 1380, height: 1000 })
  await page.setContent(`<html><body style="margin:0;background:#ccc">${imgs}</body></html>`)
  const out = `${outPrefix}${k / n}.png`
  await page.screenshot({ path: out, fullPage: true })
  console.log(out)
}
await browser.close()
