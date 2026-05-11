import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  const alertCount = ref(0)
  const userInfo = ref(null)
  const token = ref(localStorage.getItem('token') || '')
  const sidebarCollapsed = ref(false)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => userInfo.value?.username || '管理员')
  const userRole = computed(() => userInfo.value?.role || 'guest')

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

  init()

  return {
    alertCount,
    userInfo,
    token,
    sidebarCollapsed,
    loading,
    isLoggedIn,
    username,
    userRole,
    setAlertCount,
    setUserInfo,
    setToken,
    toggleSidebar,
    setLoading,
    logout,
    init
  }
})
