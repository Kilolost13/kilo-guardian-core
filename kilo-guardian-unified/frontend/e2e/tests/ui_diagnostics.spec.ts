import { expect, test } from '@playwright/test';

test.describe('Diagnostics UI', () => {
    test('shows green pip when system is healthy', async ({ page }) => {
        await page.route('**/api/diagnostics', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ status: 'GREEN', message: 'All Systems Nominal', cpu: 5.0, ram: 20.0, metrics_available: true, cpu_available: true, ram_available: true })
            });
        });
        await page.goto('/');
        // Wait for diagnostics status element to update
        await page.waitForSelector('#diag-status', { timeout: 5000 });
        const statusText = (await page.locator('#diag-status').textContent()) || '';
        await expect(statusText.trim()).toBe('GREEN');
    });

    test('shows yellow pip and message when metrics unavailable', async ({ page }) => {
        await page.route('**/api/diagnostics', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ status: 'YELLOW', message: 'Monitoring degraded - missing metrics: CPU', cpu: null, ram: null, metrics_available: false, cpu_available: false, ram_available: false })
            });
        });
        await page.goto('/');
        await page.waitForSelector('#diag-status', { timeout: 5000 });
        const statusText2 = (await page.locator('#diag-status').textContent()) || '';
        await expect(statusText2.trim()).toBe('YELLOW');
    });

    test('shows red pip when critical', async ({ page }) => {
        await page.route('**/api/diagnostics', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ status: 'RED', message: 'CRITICAL: CPU Overload - CPU: 99.0%', cpu: 99.0, ram: 30.0, metrics_available: true, cpu_available: true, ram_available: true })
            });
        });
        await page.goto('/');
        await page.waitForSelector('#diag-status', { timeout: 5000 });
        const statusText3 = (await page.locator('#diag-status').textContent()) || '';
        await expect(statusText3.trim()).toBe('RED');
    });
});
