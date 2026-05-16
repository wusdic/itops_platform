import api from './request'

// Channels
export const getChannels = () => api.get('/notification/channels')
export const getChannel = id => api.get(`/notification/channels/${id}`)
export const createChannel = data => api.post('/notification/channels', data)
export const updateChannel = (id, data) => api.put(`/notification/channels/${id}`, data)
export const deleteChannel = id => api.delete(`/notification/channels/${id}`)
export const testChannel = id => api.post(`/notification/test/${id}`)

// Send
export const sendNotification = data => api.post('/notification/send', data)
export const sendAlert = data => api.post('/notification/alert', data)

// Types & History
export const getNotificationTypes = () => api.get('/notification/types')
export const getNotificationHistory = params => api.get('/notification/history', { params })

// Target rules
export const getTargetRules = params => api.get('/notification/target-rules', { params })
export const createTargetRule = data => api.post('/notification/target-rules', data)
export const getTargetRule = id => api.get(`/notification/target-rules/${id}`)
export const updateTargetRule = (id, data) => api.put(`/notification/target-rules/${id}`, data)
export const deleteTargetRule = id => api.delete(`/notification/target-rules/${id}`)
export const toggleTargetRule = id => api.post(`/notification/target-rules/${id}/toggle`)
export const matchTargetRules = params => api.get('/notification/target-rules/match', { params })

// Targets
export const getTargets = params => api.get('/notification/targets', { params })
export const createTarget = data => api.post('/notification/targets', data)
export const getTarget = id => api.get(`/notification/targets/${id}`)
export const deleteTarget = id => api.delete(`/notification/targets/${id}`)
