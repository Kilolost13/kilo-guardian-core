import { expect, test } from '@playwright/test';

test('Security banner shows critical on RED health', async ({ page }) => {
    await page.route('**/api/diagnostics', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ status: 'RED', message: 'CRITICAL: CPU Overload - CPU: 99.0%', cpu: 99.0, ram: 30.0, metrics_available: true, cpu_available: true, ram_available: true })
        });
    });
    await page.goto('/');
    await page.waitForSelector('#diag-status', { timeout: 5000 });
    const statusText = (await page.locator('#diag-status').textContent()) || '';
    await expect(statusText.trim()).toBe('RED');
});
