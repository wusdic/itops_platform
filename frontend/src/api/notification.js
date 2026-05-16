import request from './request'

export const notification = {
  // 通知渠道管理
  getChannels: () => request.get('/notifications/channels'),
  getChannel: (id) => request.get(`/notifications/channels/${id}`),
  createChannel: (data) => request.post('/notifications/channels', data),
  updateChannel: (id, data) => request.put(`/notifications/channels/${id}`, data),
  deleteChannel: (id) => request.delete(`/notifications/channels/${id}`),
  testChannel: (id) => request.post(`/notifications/test/${id}`),

  // 通知历史
  getHistory: (params) => request.get('/notifications/history', { params }),
  deleteHistory: (id) => request.delete(`/notifications/history/${id}`),

  // 通知类型
  getTypes: () => request.get('/notifications/types'),

  // 通知目标规则
  getTargetRules: (params) => request.get('/notifications/target-rules', { params }),
  createTargetRule: (data) => request.post('/notifications/target-rules', data),
  getTargetRule: (id) => request.get(`/notifications/target-rules/${id}`),
  updateTargetRule: (id, data) => request.put(`/notifications/target-rules/${id}`, data),
  deleteTargetRule: (id) => request.delete(`/notifications/target-rules/${id}`),
  toggleTargetRule: (id) => request.post(`/notifications/target-rules/${id}/toggle`),

  // 通知对象
  getTargets: (params) => request.get('/notifications/targets', { params }),
  createTarget: (data) => request.post('/notifications/targets', data),
  getTarget: (id) => request.get(`/notifications/targets/${id}`),
  deleteTarget: (id) => request.delete(`/notifications/targets/${id}`),

  // 发送通知
  send: (data) => request.post('/notifications/send', data),
  sendAlert: (data) => request.post('/notifications/alert', data)
}
