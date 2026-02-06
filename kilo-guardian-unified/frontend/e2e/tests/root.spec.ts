import { test, expect } from '@playwright/test';

test('root page contains Kilo Guardian AI title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Kilo Guardian AI/);
});
