import { test, expect } from '@playwright/test';

test('camera preview shows a frame and modal opens with live frame', async ({ page, baseURL }) => {
  // Navigate to Admin page
  await page.goto(`${baseURL}/admin`);

  // Wait up to 20s for a preview frame to appear
  const smallImg = await page.waitForSelector('img[data-has-frame="true"]', { timeout: 20000 });
  expect(smallImg).not.toBeNull();

  // Click the small preview area (the compact preview has cursor-pointer on its wrapper)
  await page.click('div.cursor-pointer');

  // Wait for the modal title to be visible
  await page.waitForSelector('text=Camera Preview', { timeout: 10000 });

  // Assert modal contains a live image frame
  const modalImg = await page.waitForSelector('div.fixed.inset-0 img[data-has-frame="true"]', { timeout: 20000 });
  expect(modalImg).not.toBeNull();
});
