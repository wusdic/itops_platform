import api from './request'

export const getTasks = params => api.get('/scheduler/tasks', { params })
export const createTask = data => api.post('/scheduler/tasks', data)
export const getTask = id => api.get(`/scheduler/tasks/${id}`)
export const updateTask = (id, data) => api.put(`/scheduler/tasks/${id}`, data)
export const deleteTask = id => api.delete(`/scheduler/tasks/${id}`)
export const toggleTask = id => api.post(`/scheduler/tasks/${id}/toggle`)
export const executeTask = id => api.post(`/scheduler/tasks/${id}/execute`)
export const getTaskLogs = params => api.get('/scheduler/logs', { params })
