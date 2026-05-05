import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 状态
  const alertCount = ref(0)
  const userInfo = ref(null)
  const token = ref(localStorage.getItem('token') || '')
  const sidebarCollapsed = ref(false)
  const loading = ref(false)

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  
  const username = computed(() => userInfo.value?.username || '未知用户')
  
  const userRole = computed(() => userInfo.value?.role || 'guest')

  // 方法
  const setAlertCount = (count) => {
    alertCount.value = count
  }

  const setUserInfo = (info) => {
    userInfo.value = info
    if (info) {
      localStorage.setItem('userInfo', JSON.stringify(info))
    } else {
      localStorage.removeItem('userInfo')
    }
  }

  const setToken = (newToken) => {
    token.value = newToken
    if (newToken) {
      localStorage.setItem('token', newToken)
    } else {
      localStorage.removeItem('token')
    }
  }

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  const setLoading = (value) => {
    loading.value = value
  }

  const logout = () => {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
  }

  // 初始化 - 从localStorage恢复状态
  const init = () => {
    const savedUserInfo = localStorage.getItem('userInfo')
    if (savedUserInfo) {
      try {
        userInfo.value = JSON.parse(savedUserInfo)
      } catch (e) {
        console.error('Failed to parse userInfo:', e)
      }
    }
  }

  // 初始化
  init()

  return {
    // 状态
    alertCount,
    userInfo,
    token,
    sidebarCollapsed,
    loading,
    // 计算属性
    isLoggedIn,
    username,
    userRole,
    // 方法
    setAlertCount,
    setUserInfo,
    setToken,
    toggleSidebar,
    setLoading,
    logout,
    init
  }
})
