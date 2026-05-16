import api from './request'

export const getCaptcha = () => api.get('/auth/captcha')
export const login = data => api.post('/auth/login', data)
export const logout = () => api.post('/auth/logout')
export const register = data => api.post('/auth/register', data)
export const getUserInfo = () => api.get('/auth/userinfo')
export const refreshToken = () => api.post('/auth/refresh')
export const changePassword = data => api.put('/auth/password', data)
