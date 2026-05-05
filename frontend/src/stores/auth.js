import { defineStore } from 'pinia'
import { ref } from 'vue'
import { auth as authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const userInfo = ref(null)
  const token = ref(localStorage.getItem('token') || '')
  const loading = ref(false)

  // 登录
  const login = async (credentials) => {
    loading.value = true
    try {
      const res = await authApi.login(credentials)
      token.value = res.token
      userInfo.value = res.user
      localStorage.setItem('token', res.token)
      localStorage.setItem('userInfo', JSON.stringify(res.user))
      return res
    } finally {
      loading.value = false
    }
  }

  // 登出
  const logout = async () => {
    try {
      await authApi.logout()
    } catch (e) {
      console.error('Logout error:', e)
    } finally {
      token.value = ''
      userInfo.value = null
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    }
  }

  // 注册
  const register = async (data) => {
    loading.value = true
    try {
      return await authApi.register(data)
    } finally {
      loading.value = false
    }
  }

  // 获取用户信息
  const fetchUserInfo = async () => {
    if (!token.value) return null
    try {
      const res = await authApi.getUserInfo()
      userInfo.value = res
      return res
    } catch (e) {
      console.error('Failed to fetch user info:', e)
      return null
    }
  }

  // 刷新Token
  const refreshToken = async () => {
    try {
      const res = await authApi.refreshToken()
      token.value = res.token
      localStorage.setItem('token', res.token)
      return res.token
    } catch (e) {
      console.error('Failed to refresh token:', e)
      return null
    }
  }

  return {
    userInfo,
    token,
    loading,
    login,
    logout,
    register,
    fetchUserInfo,
    refreshToken
  }
})
