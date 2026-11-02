import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

export const reviewsAPI = {
  // legacy
  scan: (payload) => api.post('/reviews/scan', payload),
  analyzed: (limit = 100) => api.get(`/reviews/analyzed?limit=${limit}`),
  stats: () => api.get('/reviews/stats'),
  // live scanner endpoints
  liveAlerts: (params = {}) => api.get('/reviews/live', { params }),
  liveSummary: () => api.get('/reviews/live/summary'),
  resolveAlert: (id) => api.patch(`/reviews/live/${id}/resolve`),
  scanOne: (reviewId) => api.post(`/reviews/scan/${reviewId}`),
}

export const returnsAPI = {
  evaluate: (payload) => api.post('/returns/evaluate', payload),
}

export const usersAPI = {
  riskScore: (payload) => api.post('/users/risk-score', payload),
  flagged: (limit = 50, minScore = 55) =>
    api.get(`/users/flagged?limit=${limit}&min_score=${minScore}`),
  full: (userId) => api.get(`/users/${userId}/full`),
}

export const paymentsAPI = {
  analyze: (payload) => api.post('/payments/analyze', payload),
}

export const dashboardAPI = {
  stats: () => api.get('/dashboard/stats'),
  suspiciousOrders: (limit = 50) => api.get(`/dashboard/orders/suspicious?limit=${limit}`),
  recentAlerts: (limit = 20) => api.get(`/dashboard/alerts/recent?limit=${limit}`),
}

export const alertsAPI = {
  get: (params = {}) => api.get('/alerts/', { params }),
  summary: () => api.get('/alerts/summary'),
  resolve: (id) => api.patch(`/alerts/${id}/resolve`),
}

export default api
