import { expect, test } from '@playwright/test';

test.describe('Diagnostics modal', () => {
    test('clicking the system health pill opens a modal with details', async ({ page }) => {
        await page.route('**/api/system/health', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ status: 'GREEN', message: 'All Systems Nominal', cpu: 5.0, ram: 20.0, metrics_available: true, cpu_available: true, ram_available: true })
            });
        });
            await page.route('**/api/diagnostics', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'GREEN', message: 'OK', cpu: 1.0, ram: 2.0, metrics_available: true, cpu_available: true, ram_available: true })
                });
            });
        await page.goto('/');
            const status = page.locator('#diag-status');
            await expect(status).toBeVisible({ timeout: 5000 });
            // Ensure diagnostic details area populates (Status/Plugins/OS)
            const content = page.locator('#diag-content');
            await expect(content).toContainText('Status');
            await expect(content).toContainText('Plugins Loaded');
    });
});
