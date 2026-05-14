import request from './request'
import { devices, alerts, performance } from './monitoring'
import { auth, user, role, menu, dict, config } from './system'
import { assets } from './assets'
import { scheduler, reports } from './scheduler'

export const workorder = {
  getList: (params) => request.get('/workorders/', { params }),
  getById: (id) => request.get(`/workorders/${id}`),
  create: (data) => request.post('/workorders/', data),
  update: (id, data) => request.put(`/workorders/${id}`, data),
  delete: (id) => request.delete(`/workorders/${id}`),
  assign: (id, data) => request.post(`/workorders/${id}/assign`, data),
  close: (id, data) => request.post(`/workorders/${id}/close`, data),
  complete: (id, data) => request.post(`/workorders/${id}/resolve`, data),
  getMyList: (params) => request.get('/workorders/', { ...params, creator: 'admin' }),
  getStatistics: () => request.get('/workorders/stats/summary')
}

export const knowledge = {
  getList: (params) => request.get('/knowledge/fault-cases', { params }),
  getById: (id) => request.get(`/knowledge/fault-cases/${id}`),
  create: (data) => request.post('/knowledge/fault-cases', data),
  update: (id, data) => request.put(`/knowledge/fault-cases/${id}`, data),
  delete: (id) => request.delete(`/knowledge/fault-cases/${id}`),
  publish: (id) => request.post(`/knowledge/fault-cases/${id}/publish`),
  getCategory: () => request.get('/knowledge/fault-cases/category'),
  createCategory: (data) => request.post('/knowledge/fault-cases/category', data),
  updateCategory: (id, data) => request.put(`/knowledge/fault-cases/category/${id}`, data),
  deleteCategory: (id) => request.delete(`/knowledge/fault-cases/category/${id}`)
}

export const ai = {
  chat: (data) => request.post('/ai/chat', data),
  analyze: (alertId, type) => request.post(`/ai/analyze/${alertId}/${type}`, {}),
  getHistory: (params) => request.get('/ai/conversations', { params }),
  clearHistory: () => request.delete('/ai/conversations')
}

export const automation = {
  getScripts: (params) => request.get('/automation/scripts', { params }),
  getScriptById: (id) => request.get(`/automation/scripts/${id}`),
  createScript: (data) => request.post('/automation/scripts', data),
  updateScript: (id, data) => request.put(`/automation/scripts/${id}`, data),
  deleteScript: (id) => request.delete(`/automation/scripts/${id}`),
  executeScript: (id, params) => request.post(`/automation/scripts/${id}/execute`, params),
  getTasks: (params) => request.get('/automation/trigger-rules', { params }),
  createTask: (data) => request.post('/automation/trigger-rules', data),
  updateTask: (id, data) => request.put(`/automation/trigger-rules/${id}`, data),
  deleteTask: (id) => request.delete(`/automation/trigger-rules/${id}`),
  toggleTask: (id, enabled) => request.put(`/automation/trigger-rules/${id}`, { enabled }),
  getExecutions: (params) => request.get('/automation/executions', { params }),
  getExecutionLog: (id) => request.get(`/automation/executions/${id}`)
}

export const backup = {
  getList: (params) => request.get('/admin/backups', { params }),
  create: (data) => request.post('/admin/backups', data),
  delete: (id) => request.delete(`/admin/backups/${id}`),
  restore: (id) => request.post(`/admin/backups/${id}/restore`),
  getRestoreHistory: (id) => request.get(`/admin/restores`)
}

export const notification = {
  getList: (params) => request.get('/notifications/messages', { params }),
  getUnreadCount: () => request.get('/notifications/messages/unread-count'),
  markAsRead: (id) => request.post(`/notifications/messages/${id}/read`),
  markAllAsRead: () => request.post('/notifications/messages/read-all'),
  delete: (id) => request.delete(`/notifications/messages/${id}`),
  getConfig: () => request.get('/notifications/channels'),
  updateConfig: (data) => request.post('/notifications/channels', data)
}

export { devices, alerts, performance, auth, user, role, menu, dict, config, assets, scheduler, reports }

