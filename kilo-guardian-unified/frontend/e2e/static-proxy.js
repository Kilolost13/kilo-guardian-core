const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const PORT = process.env.PORT || 4200;
const API_TARGET = process.env.API_TARGET || 'http://127.0.0.1:8001';

const app = express();

// Proxy /api requests to backend
app.use('/api', createProxyMiddleware({ target: API_TARGET, changeOrigin: true, secure: false }));

// Proxy video feed path as well
app.use('/api/video_feed', createProxyMiddleware({ target: API_TARGET, changeOrigin: true, secure: false }));

// Serve static files from public
app.use(express.static(path.join(__dirname, '..', 'public')));

// Fallback to index.html for single-page app
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Static proxy server listening on http://127.0.0.1:${PORT}, proxying /api -> ${API_TARGET}`);
});
