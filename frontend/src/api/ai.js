import api from './request'

// Chat
export const chat = data => api.post('/ai/chat', data)
export const chatDebug = data => api.post('/ai/chat/_debug', data)
export const getConversation = id => api.get(`/ai/conversation/${id}`)
export const getConversations = params => api.get('/ai/conversations', { params })
export const deleteConversation = id => api.delete(`/ai/conversation/${id}`)
export const pinConversation = id => api.put(`/ai/conversation/${id}/pin`)
export const saveMessage = (id, data) => api.post(`/ai/conversation/${id}/messages`, data)

// Troubleshoot
export const troubleshoot = data => api.post('/ai/troubleshoot', data)
export const troubleshootAuto = data => api.post('/ai/troubleshoot/auto', data)

// Analysis
export const suggest = data => api.post('/ai/suggest', data)
export const interpretReport = data => api.post('/ai/interpret/report', data)
export const analyzeLogs = data => api.post('/ai/analyze/logs', data)
export const questionAnswer = data => api.post('/ai/qa', data)

// Stats
export const getAiStats = () => api.get('/ai/stats')

// Root cause & remediation
export const analyzeRootCause = data => api.post('/ai/root-cause', data)
export const getRemediation = data => api.post('/ai/remediation', data)
