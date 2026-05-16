import axios from 'axios'
import { useMessage } from 'naive-ui'
import router from '../router'

const message = useMessage()

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    const res = response.data
    // 兼容 access_token 和 token 两种字段名
    if (res.access_token && !res.token) {
      res.token = res.access_token
    }
    // 兼容无 code 字段的响应（如登录 API 直接返回 token）
    if (res.access_token || res.token) {
      return res
    }
    // 兼容直接返回 {items, total} 格式（如 /assets/device）
    // 和 {code, data} 包装格式
    if (res.code === 200 || res.code === 0) {
      return res.data || res
    }
    // 如果既无 code 也无 access_token，但有 items 字段（列表 API 格式），直接返回
    if (res.items !== undefined && res.total !== undefined) {
      return res
    }
    // 如果是数组（某些列表接口直接返回数组）
    if (Array.isArray(res)) {
      return { items: res, total: res.length }
    }
    // 有 msg 或 detail 字段通常是后端错误响应
    if (res.msg) {
      message.error(res.msg || '请求失败')
      return Promise.reject(new Error(res.msg || '请求失败'))
    }
    // 兜底：直接返回原始数据
    return res
  },
  error => {
    if (error.response) {
      const data = error.response.data
      if (error.response.status === 401) {
        message.error('登录已过期，请重新登录')
        localStorage.removeItem('token')
        router.push('/login')
      } else if (error.response.status === 403) {
        message.error('没有权限访问')
      } else if (error.response.status === 404 && data?.detail?.includes('无指标数据')) {
        // 设备指标暂无数据，是正常状态，不弹错误提示，静默返回空数据
        return Promise.reject(new Error('NO_DATA'))
      } else if (data?.msg || data?.detail) {
        message.error(data.msg || data.detail)
        return Promise.reject(new Error(data.msg || data.detail))
      } else {
        message.error('请求失败')
      }
    } else {
      message.error('网络错误')
    }
    return Promise.reject(error)
  }
)

export default request
