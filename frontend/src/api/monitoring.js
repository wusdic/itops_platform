import request from './request'

export const devices = {
  getList: (params) => request.get('/monitoring/device/list', { params }),
  getById: (id) => request.get(`/monitoring/device/${id}`),
  create: (data) => request.post('/monitoring/device', data),
  update: (id, data) => request.put(`/monitoring/device/${id}`, data),
  delete: (id) => request.delete(`/monitoring/device/${id}`),
  getMetrics: (id) => request.get(`/monitoring/device/${id}/metrics`),
  getStatus: () => request.get('/monitoring/device/status'),
  batchOperate: (ids, action) => request.post('/monitoring/device/batch', { ids, action })
}

export const alerts = {
  getList: (params) => request.get('/monitoring/alert/list', { params }),
  getById: (id) => request.get(`/monitoring/alert/${id}`),
  create: (data) => request.post('/monitoring/alert', data),
  update: (id, data) => request.put(`/monitoring/alert/${id}`, data),
  delete: (id) => request.delete(`/monitoring/alert/${id}`),
  handle: (id, data) => request.post(`/monitoring/alert/${id}/handle`, data),
  silence: (id, data) => request.post(`/monitoring/alert/${id}/silence`, data),
  getStatistics: () => request.get('/monitoring/alert/statistics')
}

export const performance = {
  getMetrics: (params) => request.get('/monitoring/performance/metrics', { params }),
  getHistory: (params) => request.get('/monitoring/performance/history', { params }),
  getTopN: (type) => request.get(`/monitoring/performance/top/${type}`)
}
