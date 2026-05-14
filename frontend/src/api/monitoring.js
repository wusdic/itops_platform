import request from './request'

export const devices = {
  getList: (params) => request.get('/assets/device', { params }),
  getById: (id) => request.get(`/assets/device/${id}`),
  create: (data) => request.post('/assets/device', data),
  update: (id, data) => request.put(`/assets/device/${id}`, data),
  delete: (id) => request.delete(`/assets/device/${id}`),
  getMetrics: (id) => request.get(`/devices/${id}/metrics`),
  getStatus: () => request.get('/assets/stats'),
  batchOperate: (ids, action) => request.post('/assets/device/batch', { ids, action }),
  // 批量导入相关
  getImportTemplate: (format = 'xlsx') => request.get('/devices/import/template', { params: { format }, responseType: 'blob' }),
  validateImport: (rows) => request.post('/devices/import/validate', rows),
  importDevices: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/devices/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  importDevicesSimple: (rows) => request.post('/devices/import/simple', rows)
}

export const alerts = {
  getList: (params) => request.get('/monitoring/alerts', { params }),
  getById: (id) => request.get(`/monitoring/alerts/${id}`),
  create: (data) => request.post('/monitoring/alerts', data),
  update: (id, data) => request.put(`/monitoring/alerts/${id}`, data),
  delete: (id) => request.delete(`/monitoring/alerts/${id}`),
  handle: (id, data) => request.post(`/monitoring/alerts/${id}/handle`, data),
  silence: (id, data) => request.post(`/monitoring/alerts/${id}/silence`, data),
  getStatistics: () => request.get('/monitoring/alerts/statistics')
}

export const performance = {
  getMetrics: (params) => request.get('/monitoring/metrics', { params }),
  getHistory: (params) => request.get('/monitoring/metrics/history', { params }),
  getTopN: (type) => request.get(`/monitoring/metrics/top/${type}`)
}
