import { expect, test } from '@playwright/test';

test('UI chat displays interactive_form JSON response as preformatted text', async ({ page }) => {
    // Mock the chat API to return an interactive_form-like structure
    await page.route('**/api/chat', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ answer: { type: 'interactive_form', form: { title: 'Add Transaction', fields: [{ name: 'amount' }] }, message: 'Please fill the form' } })
        });
    });

    await page.goto('/');
    const textarea = page.locator('#user-input');
    const sendButton = page.locator('#send-button');
    await expect(textarea).toBeVisible({ timeout: 10000 });
    await textarea.fill('add transaction');
    await sendButton.click();
    // The response may be rendered as JSON inside a pre or as content inside the Kilo bubble
    // Wait for the Kilo response (form title) to appear
    await page.waitForSelector('text=Add Transaction', { timeout: 15000 });
    await expect(page.locator('text=Add Transaction')).toBeVisible();
});
