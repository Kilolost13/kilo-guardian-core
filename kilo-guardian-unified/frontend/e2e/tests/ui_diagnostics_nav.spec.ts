import { expect, test } from '@playwright/test';

test('open diagnostics via nav sidebar and show charts', async ({ page }) => {
    await page.route('**/api/system/metrics', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ samples: Array.from({ length: 30 }).map((_, i) => ({ ts: Date.now() / 1000 - i, cpu: 10 + i % 5, ram: 30 + i % 10 })), count: 30 })
        });
    });
    await page.goto('/');
    // Click diagnostics via visible text if available
    const diagBtn = page.locator('text=Diagnostics').first();
    await expect(diagBtn).toBeVisible();
    await diagBtn.click();
    // Ensure the diagnostics area is visible
    await expect(page.locator('#diag-content')).toBeVisible();
    // Ensure content contains expected diagnostic headings
    await expect(page.locator('#diag-content')).toContainText('Status');
    await expect(page.locator('#diag-content')).toContainText('OS');
});
