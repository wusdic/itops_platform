import request from './request'

export const auth = {
  login: (data) => request.post('/auth/login', data),
  logout: () => request.post('/auth/logout'),
  getUserInfo: () => request.get('/auth/userinfo')
}

export const user = {
  getList: (params) => request.get('/system/user/list', { params }),
  getById: (id) => request.get(`/system/user/${id}`),
  create: (data) => request.post('/system/user', data),
  update: (id, data) => request.put(`/system/user/${id}`, data),
  delete: (id) => request.delete(`/system/user/${id}`),
  resetPassword: (id) => request.post(`/system/user/${id}/reset-password`),
  changeStatus: (id, status) => request.put(`/system/user/${id}/status`, { status })
}

export const role = {
  getList: (params) => request.get('/system/role/list', { params }),
  getById: (id) => request.get(`/system/role/${id}`),
  create: (data) => request.post('/system/role', data),
  update: (id, data) => request.put(`/system/role/${id}`, data),
  delete: (id) => request.delete(`/system/role/${id}`),
  getPermissions: (id) => request.get(`/system/role/${id}/permissions`),
  assignPermissions: (id, data) => request.post(`/system/role/${id}/permissions`, data)
}

export const menu = {
  getList: () => request.get('/system/menu/list'),
  getById: (id) => request.get(`/system/menu/${id}`),
  create: (data) => request.post('/system/menu', data),
  update: (id, data) => request.put(`/system/menu/${id}`, data),
  delete: (id) => request.delete(`/system/menu/${id}`)
}

export const dict = {
  getList: (params) => request.get('/system/dict/list', { params }),
  getById: (id) => request.get(`/system/dict/${id}`),
  create: (data) => request.post('/system/dict', data),
  update: (id, data) => request.put(`/system/dict/${id}`, data),
  delete: (id) => request.delete(`/system/dict/${id}`),
  getItems: (type) => request.get(`/system/dict/${type}/items`)
}

export const config = {
  getList: (params) => request.get('/system/config/list', { params }),
  getByKey: (key) => request.get(`/system/config/${key}`),
  update: (key, data) => request.put(`/system/config/${key}`, data)
}
