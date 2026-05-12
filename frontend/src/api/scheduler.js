import request from './request'

export const scheduler = {
  getList: (params) => request.get('/scheduler/task/list', { params }),
  getById: (id) => request.get(`/scheduler/task/${id}`),
  create: (data) => request.post('/scheduler/task', data),
  update: (id, data) => request.put(`/scheduler/task/${id}`, data),
  delete: (id) => request.delete(`/scheduler/task/${id}`),
  toggle: (id, enabled) => request.put(`/scheduler/task/${id}/toggle`, { enabled }),
  execute: (id) => request.post(`/scheduler/task/${id}/execute`),
  getLogs: (id, params) => request.get(`/scheduler/task/${id}/logs`, { params })
}

export const reports = {
  getList: (params) => request.get('/report/list', { params }),
  getById: (id) => request.get(`/report/${id}`),
  create: (data) => request.post('/report', data),
  update: (id, data) => request.put(`/report/${id}`, data),
  delete: (id) => request.delete(`/report/${id}`),
  download: (id) => request.get(`/report/${id}/download`),
  generate: (data) => request.post('/report/generate', data)
}
