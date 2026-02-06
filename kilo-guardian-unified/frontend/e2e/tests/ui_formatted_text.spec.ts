import { expect, test } from '@playwright/test';

test('UI chat renders formatted_text as plain text', async ({ page }) => {
    // Mock backend chat response so test is deterministic
    await page.route('**/api/chat', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ answer: '=== Financial Overview\n- Revenue: $1234\n- Expenses: $567' })
        });
    });

    await page.goto('/');
    const textarea = page.locator('#user-input');
    const sendButton = page.locator('#send-button');
    await expect(textarea).toBeVisible({ timeout: 10000 });
    await textarea.fill('show financial overview');
    await sendButton.click();

    // Wait for the mocked response bubble to appear and assert content
    const response = page.locator('.chat-bubble-kilo').last();
    await expect(response).toContainText('Financial', { timeout: 15000 });
    const text = await response.textContent();
    await expect(text || '').not.toContain('{"type":');
});
