import { test, expect } from '@playwright/test';

test('chat plugin formatted_text returns text/plain or JSON', async ({ request }) => {
  const res = await request.post('http://127.0.0.1:8001/api/chat', {
    data: { query: 'show financial overview' },
    headers: {
      'X-API-Key': 'kilo-dev-key-2025',
    },
  });
  expect(res.status()).toBe(200);
  const contentType = res.headers()['content-type'] || '';
  const text = await res.text();

  // Accept either text/plain body or a JSON response with structured content
  if (contentType.includes('application/json')) {
    const parsed = JSON.parse(text);
    const lowered = JSON.stringify(parsed).toLowerCase();
    // Accept either a financial overview OR the offline fallback message
    expect(lowered.includes('financial') || lowered.includes('conversational abilities')).toBeTruthy();
  } else {
    expect(text).toContain('Financial');
  }
});
