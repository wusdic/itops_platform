import request from './request'
import { devices, alerts, performance } from './monitoring'
import { auth, user, role, menu, dict, config } from './system'
import { assets } from './assets'
import { scheduler, reports } from './scheduler'

export const workorder = {
  getList: (params) => request.get('/workorder/list', { params }),
  getById: (id) => request.get(`/workorder/${id}`),
  create: (data) => request.post('/workorder', data),
  update: (id, data) => request.put(`/workorder/${id}`, data),
  delete: (id) => request.delete(`/workorder/${id}`),
  assign: (id, data) => request.post(`/workorder/${id}/assign`, data),
  close: (id, data) => request.post(`/workorder/${id}/close`, data),
  complete: (id, data) => request.post(`/workorder/${id}/complete`, data),
  getMyList: (params) => request.get('/workorder/my', { params }),
  getStatistics: () => request.get('/workorder/statistics')
}

export const knowledge = {
  getList: (params) => request.get('/knowledge/list', { params }),
  getById: (id) => request.get(`/knowledge/${id}`),
  create: (data) => request.post('/knowledge', data),
  update: (id, data) => request.put(`/knowledge/${id}`, data),
  delete: (id) => request.delete(`/knowledge/${id}`),
  publish: (id) => request.post(`/knowledge/${id}/publish`),
  getCategory: () => request.get('/knowledge/category'),
  createCategory: (data) => request.post('/knowledge/category', data),
  updateCategory: (id, data) => request.put(`/knowledge/category/${id}`, data),
  deleteCategory: (id) => request.delete(`/knowledge/category/${id}`)
}

export const ai = {
  chat: (data) => request.post('/ai/chat', data),
  analyze: (data) => request.post('/ai/analyze', data),
  getHistory: (params) => request.get('/ai/history', { params }),
  clearHistory: () => request.delete('/ai/history')
}

export const automation = {
  getScripts: (params) => request.get('/automation/script/list', { params }),
  getScriptById: (id) => request.get(`/automation/script/${id}`),
  createScript: (data) => request.post('/automation/script', data),
  updateScript: (id, data) => request.put(`/automation/script/${id}`, data),
  deleteScript: (id) => request.delete(`/automation/script/${id}`),
  executeScript: (id, params) => request.post(`/automation/script/${id}/execute`, params),
  getTasks: (params) => request.get('/automation/task/list', { params }),
  createTask: (data) => request.post('/automation/task', data),
  updateTask: (id, data) => request.put(`/automation/task/${id}`, data),
  deleteTask: (id) => request.delete(`/automation/task/${id}`),
  toggleTask: (id, enabled) => request.put(`/automation/task/${id}/toggle`, { enabled }),
  getExecutions: (params) => request.get('/automation/execution/list', { params }),
  getExecutionLog: (id) => request.get(`/automation/execution/${id}/log`)
}

export const backup = {
  getList: (params) => request.get('/backup/list', { params }),
  create: (data) => request.post('/backup', data),
  delete: (id) => request.delete(`/backup/${id}`),
  restore: (id) => request.post(`/backup/${id}/restore`),
  getRestoreHistory: (id) => request.get(`/backup/${id}/restore/history`)
}

export const notification = {
  getList: (params) => request.get('/notification/list', { params }),
  getUnreadCount: () => request.get('/notification/unread/count'),
  markAsRead: (id) => request.post(`/notification/${id}/read`),
  markAllAsRead: () => request.post('/notification/read/all'),
  delete: (id) => request.delete(`/notification/${id}`),
  getConfig: () => request.get('/notification/config'),
  updateConfig: (data) => request.put('/notification/config', data)
}

export { devices, alerts, performance, auth, user, role, menu, dict, config, assets, scheduler, reports }

