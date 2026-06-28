import axios from 'axios';

// Create a connection to our Python server
export const api = axios.create({
  baseURL: 'http://localhost:8000',
});

// This magic function automatically attaches your VIP Token to every request!
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});