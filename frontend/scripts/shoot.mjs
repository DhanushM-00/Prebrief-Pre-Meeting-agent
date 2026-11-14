// Playwright may be local or global — resolve either.
async function loadPlaywright() {
  for (const spec of [
    'playwright',
    '/usr/local/lib/node_modules/playwright/index.js',
    '/usr/lib/node_modules/playwright/index.js',
  ]) {
    try {
      const mod = await import(spec)
      return (mod.default ?? mod).chromium
    } catch {
      /* try the next candidate */
    }
  }
  throw new Error('playwright not found — npm i -D playwright && npx playwright install chromium')
}
const chromium = await loadPlaywright()

const BASE = process.env.APP_URL || 'http://127.0.0.1:4173/'
const OUT = '/workspace/shots'

const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH || undefined,
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
})
const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()

const errors = []
page.on('console', (m) => {
  if (m.type() === 'error') errors.push(m.text())
})
page.on('pageerror', (e) => errors.push(`PAGEERROR: ${e.message}`))
const failedRequests = []
page.on('requestfailed', (r) => failedRequests.push(`${r.url()} :: ${r.failure()?.errorText}`))
page.on('response', (r) => {
  if (r.status() >= 400) failedRequests.push(`${r.url()} :: HTTP ${r.status()}`)
})

/* ---------------- home ---------------- */
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForTimeout(700)
await page.screenshot({ path: `${OUT}/01-home.png` })

/* ---------------- research ---------------- */
await page.fill('input[placeholder*="Company"]', 'Helio Grid')
await page.click('button:has-text("Research")')
await page.waitForTimeout(900)
await page.screenshot({ path: `${OUT}/02-progress.png` })
await page.waitForSelector('text=What actually happened', { timeout: 20000 })
await page.waitForTimeout(1000)
await page.screenshot({ path: `${OUT}/03-overview.png` })

/* deep link should now be in the address bar */
const hash = await page.evaluate(() => window.location.hash)
console.log('DEEP LINK HASH:', hash)

/* ---------------- tabs ---------------- */
await page.click('button:has-text("Coverage")')
await page.waitForTimeout(700)
await page.screenshot({ path: `${OUT}/04-coverage.png` })

await page.click('button:has-text("Signals")')
await page.waitForTimeout(900)
await page.screenshot({ path: `${OUT}/05-signals.png` })

await page.click('button:has-text("Prep")')
await page.waitForTimeout(700)
await page.screenshot({ path: `${OUT}/06-prep.png` })

await page.click('button:has-text("Sources")')
await page.waitForTimeout(600)
await page.screenshot({ path: `${OUT}/07-sources.png` })

/* ---------------- agent chat + Escape ---------------- */
await page.click('button:has-text("Ask agent")')
await page.waitForTimeout(500)
await page.click('text=What is the riskiest thing in the last 30 days?')
await page.waitForTimeout(1800)
await page.screenshot({ path: `${OUT}/08-agent.png` })
await page.keyboard.press('Escape')
await page.waitForTimeout(500)
// The drawer slides off-screen rather than unmounting, so check the transform.
const drawerBox = await page.locator('aside[aria-hidden]').boundingBox()
const closed = !drawerBox || drawerBox.x >= 1439
console.log('CHAT CLOSED BY ESCAPE:', closed, '| drawer x =', drawerBox?.x)

/* ---------------- export menu ---------------- */
await page.click('button:has-text("Export")')
await page.waitForTimeout(400)
await page.screenshot({ path: `${OUT}/09-export-menu.png` })
const menuItems = await page.locator('[role="button"], button').allTextContents()
console.log('EXPORT ITEMS:', menuItems.filter((t) => /cheat|link|Markdown|json|Print/i.test(t)).join(' | '))
await page.keyboard.press('Escape')
await page.click('body', { position: { x: 400, y: 700 } })

/* ---------------- settings panel ---------------- */
await page.click('button[aria-label="Settings"]')
await page.waitForTimeout(500)
await page.screenshot({ path: `${OUT}/10-settings.png` })
await page.click('button[aria-label="Close settings"]')
await page.waitForTimeout(300)

/* ---------------- print view ---------------- */
await page.emulateMedia({ media: 'print' })
await page.waitForTimeout(500)
await page.screenshot({ path: `${OUT}/11-print.png`, fullPage: true })
await page.pdf({ path: `${OUT}/11-brief.pdf`, format: 'A4', printBackground: false })
await page.emulateMedia({ media: 'screen' })

/* ---------------- deep link round-trip ---------------- */
await page.goto(`${BASE}#/brief/Northwind%20Robotics?d=14&t=company`, { waitUntil: 'networkidle' })
await page.waitForSelector('text=What actually happened', { timeout: 20000 })
await page.waitForTimeout(800)
const header = await page.locator('header h1').first().textContent()
const windowLabel = await page.locator('text=/last \\d+ days/').first().textContent()
console.log('DEEP LINK LOADED:', header?.trim(), '|', windowLabel?.trim())
await page.screenshot({ path: `${OUT}/12-deeplink.png` })

/* ---------------- light theme + history ---------------- */
await page.click('button[aria-label="Toggle theme"]')
await page.waitForTimeout(500)
await page.click('button:has-text("History")')
await page.waitForTimeout(600)
await page.screenshot({ path: `${OUT}/13-history-light.png` })

/* ---------------- mobile ---------------- */
const mob = await ctx.newPage()
await mob.setViewportSize({ width: 390, height: 844 })
await mob.goto(BASE, { waitUntil: 'networkidle' })
await mob.waitForTimeout(700)
await mob.screenshot({ path: `${OUT}/14-mobile.png` })

console.log('\nCONSOLE ERRORS:', errors.length ? JSON.stringify(errors.slice(0, 10), null, 2) : 'none')
console.log('FAILED REQUESTS:', failedRequests.length ? JSON.stringify(failedRequests.slice(0, 10), null, 2) : 'none')
await browser.close()
