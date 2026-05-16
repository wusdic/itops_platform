import request from './request'

export const auth = {
  login: (data) => request.post('/auth/login', data),
  logout: () => request.post('/auth/logout'),
  getUserInfo: () => request.get('/auth/userinfo'),
  register: (data) => request.post('/auth/register', data),
  changePassword: (data) => request.put('/auth/password', data),
  refreshToken: () => request.post('/auth/refresh')
}

export const user = {
  getList: (params) => request.get('/admin/users', { params }),
  getById: (id) => request.get(`/admin/users/${id}`),
  create: (data) => request.post('/admin/users', data),
  update: (id, data) => request.put(`/admin/users/${id}`, data),
  delete: (id) => request.delete(`/admin/users/${id}`),
  resetPassword: (id) => request.post(`/admin/users/${id}/reset-password`),
  changeStatus: (id, status) => request.put(`/admin/users/${id}/status`, { status })
}

export const role = {
  getList: (params) => request.get('/admin/roles', { params }),
  getById: (id) => request.get(`/admin/roles/${id}`),
  create: (data) => request.post('/admin/roles', data),
  update: (id, data) => request.put(`/admin/roles/${id}`, data),
  delete: (id) => request.delete(`/admin/roles/${id}`),
  getPermissions: (id) => request.get(`/admin/permissions`)
}

export const menu = {
  getList: () => request.get('/admin/menu'),
  getById: (id) => request.get(`/admin/menu/${id}`),
  create: (data) => request.post('/admin/menu', data),
  update: (id, data) => request.put(`/admin/menu/${id}`, data),
  delete: (id) => request.delete(`/admin/menu/${id}`)
}

export const dict = {
  getList: (params) => request.get('/admin/dict', { params }),
  getById: (id) => request.get(`/admin/dict/${id}`),
  create: (data) => request.post('/admin/dict', data),
  update: (id, data) => request.put(`/admin/dict/${id}`, data),
  delete: (id) => request.delete(`/admin/dict/${id}`),
  getItems: (type) => request.get(`/admin/dict/${type}/items`)
}

export const config = {
  getList: () => request.get('/admin/config'),
  getByKey: (key) => request.get(`/admin/config/${key}`),
  update: (key, data) => request.put(`/admin/config/${key}`, data)
}

export const system = {
  getInfo: () => request.get('/admin/info'),
  getMetrics: () => request.get('/admin/metrics'),
  getLogs: (params) => request.get('/admin/logs', { params }),
  getHealth: () => request.get('/admin/health'),
  clearCache: () => request.post('/admin/cache/clear'),
  getApiKeys: (params) => request.get('/admin/api-keys', { params }),
  createApiKey: (data) => request.post('/admin/api-keys', data),
  getApiKeyById: (id) => request.get(`/admin/api-keys/${id}`),
  updateApiKey: (id, data) => request.put(`/admin/api-keys/${id}`, data),
  deleteApiKey: (id) => request.delete(`/admin/api-keys/${id}`),
  revokeApiKey: (id) => request.post(`/admin/api-keys/${id}/revoke`),
  activateApiKey: (id) => request.post(`/admin/api-keys/${id}/activate`),
  rotateApiKey: (id) => request.post(`/admin/api-keys/${id}/rotate`)
}
