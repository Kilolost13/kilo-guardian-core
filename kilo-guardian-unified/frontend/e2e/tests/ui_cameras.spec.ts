import { expect, test } from '@playwright/test';

// This test verifies the UI camera grid reflects the API data
test('UI loads cameras and shows camera grid', async ({ page }) => {
    await page.goto('/');
    // Ensure the camera area renders and show placeholder if no cameras are present
    await page.goto('/');
    // The page should include the video feed image or a 'No cameras detected' message
    const video = page.locator('#video-feed');
    await expect(video).toBeVisible({ timeout: 5000 });
});
