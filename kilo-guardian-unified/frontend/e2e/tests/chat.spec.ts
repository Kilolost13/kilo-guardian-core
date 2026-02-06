import { test, expect } from '@playwright/test';

test('chat UI smoke test', async ({ page }) => {
  // Open frontend UI
  await page.goto('http://127.0.0.1:4200/');

  // Wait for chat window to be present (initial greeting may be rendered client-side)
  await page.waitForSelector('#chat-window', { timeout: 30000 });

  // Debug: log the resolved URL and a snippet of the loaded HTML to aid CI debugging
  console.log('Page loaded URL:', await page.url());
  const snippet = (await page.content()).slice(0, 200);
  console.log('Page HTML snippet:', snippet.replace(/\n/g, ' '));

  // Locate the input and send button (current UI uses an input#user-input)
  const input = page.locator('#user-input');
  const send = page.locator('#send-button');
  await expect(input).toBeVisible({ timeout: 30000 });
  await expect(send).toBeVisible({ timeout: 30000 });

  // Send a short query
  await input.fill('smoke test from playwright');
  await send.click();

  // Wait for a Kilo response bubble (either the thinking indicator or final response)
  await page.waitForSelector('.chat-bubble-kilo', { timeout: 20000 });
  const kiloResponse = page.locator('.chat-bubble-kilo').last();
  await expect(kiloResponse).toContainText(/smoke|offline|Kilo|thinking/i, { timeout: 20000 });
});
