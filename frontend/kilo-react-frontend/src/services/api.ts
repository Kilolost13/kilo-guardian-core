import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) {
    config.headers['X-Admin-Token'] = token;
  }
  return config;
});

export default api;
