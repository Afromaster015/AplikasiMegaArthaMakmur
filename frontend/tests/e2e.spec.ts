import { test, expect } from '@playwright/test'

async function login(page:any) {
  await page.goto('http://127.0.0.1:8765')
  await page.getByLabel('Nama pengguna').fill('admin-smoke')
  await page.getByLabel('Password').fill('password-smoke')
  const setup = page.getByRole('button', { name: 'Buat Administrator' })
  if (await setup.isVisible()) await setup.click()
  else await page.getByRole('button', { name: 'Masuk ke Aplikasi' }).click()
  await expect(page.getByText('PAYROLL WORKSPACE')).toBeVisible()
}

test('dashboard, period alignment, and responsive navigation', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 })
  await login(page)
  await expect(page.getByText('Karyawan Aktif')).toBeVisible()
  await page.screenshot({ path: '../docs/screenshots/dashboard-desktop.png', fullPage: true })
  await page.getByRole('navigation').getByRole('button', { name: 'Periode Payroll' }).click()
  await page.getByRole('button', { name: 'Buat Periode' }).click()
  const fields = page.locator('.el-dialog .el-input__wrapper')
  await expect(fields).toHaveCount(2)
  const boxes = await fields.evaluateAll((nodes:any[]) => nodes.map(n => n.getBoundingClientRect()))
  expect(Math.abs(boxes[0].top - boxes[1].top)).toBeLessThanOrEqual(1)
  expect(Math.abs(boxes[0].height - boxes[1].height)).toBeLessThanOrEqual(1)
  const actions = page.locator('.el-dialog__footer .el-button')
  expect(await actions.count()).toBe(2)
  await page.screenshot({ path: '../docs/screenshots/periode-dialog-desktop.png', fullPage: true })

  await page.setViewportSize({ width: 768, height: 900 })
  await page.screenshot({ path: '../docs/screenshots/periode-tablet.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('.mobile-menu')).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBe(0)
  await page.screenshot({ path: '../docs/screenshots/periode-mobile.png', fullPage: true })
})
