import request from './request'

export const assets = {
  getList: (params) => request.get('/assets/list', { params }),
  getById: (id) => request.get(`/assets/${id}`),
  create: (data) => request.post('/assets', data),
  update: (id, data) => request.put(`/assets/${id}`, data),
  delete: (id) => request.delete(`/assets/${id}`)
}
