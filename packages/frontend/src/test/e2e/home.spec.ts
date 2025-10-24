import { test, expect } from '@playwright/test'

test.describe('Home Page', () => {
  test('should load successfully', async ({ page }) => {
    await page.goto('/')
    
    await expect(page).toHaveTitle(/TradingAgents/i)
  })

  test('should have main navigation', async ({ page }) => {
    await page.goto('/')
    
    const nav = page.locator('nav')
    await expect(nav).toBeVisible()
  })

  test('should be responsive', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/')
    
    await expect(page).toHaveTitle(/TradingAgents/i)
  })
})
