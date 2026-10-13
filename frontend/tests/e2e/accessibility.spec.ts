import { expect, test, type Page } from '@playwright/test'


async function installHealth(page: Page) {
  await page.route('http://api.classlens.test/health', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ status: 'ok', service: 'classlens-api' }),
  }))
}


test('workspace supports bypass navigation and moves focus after route changes', async ({ page }) => {
  await installHealth(page)
  await page.goto('/dashboard')

  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('main')).toBeFocused()

  const uploadStep = page.getByRole('button', { name: '02 Upload assessment' })
  await uploadStep.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Upload assessment' })).toBeVisible()
  await expect(page.getByRole('main')).toBeFocused()
})


test('workspace stays within narrow viewports and exposes practical control targets', async ({ page }) => {
  await installHealth(page)
  await page.setViewportSize({ width: 320, height: 844 })
  await page.goto('/upload')

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)

  const undersized = await page.locator('button:visible, select:visible, summary:visible').evaluateAll((elements) =>
    elements
      .map((element) => {
        const box = element.getBoundingClientRect()
        return { label: element.textContent?.trim() || element.getAttribute('aria-label'), width: box.width, height: box.height }
      })
      .filter(({ width, height }) => width < 44 || height < 44),
  )
  expect(undersized).toEqual([])
})
