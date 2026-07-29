/**
 * Axios 实例和拦截器配置
 * 统一管理 HTTP 请求：自动附带 Token、统一错误处理
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 Axios 实例，配置后端 API 基础地址
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 300000, // 5分钟超时（上传大文件需要较长时间）
})

// ============================================================
// 请求拦截器：自动附带 JWT Token
// ============================================================
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// ============================================================
// 响应拦截器：统一错误处理
// ============================================================
api.interceptors.response.use(
  (response) => {
    // 成功响应，直接返回数据
    return response.data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      switch (status) {
        case 401:
          // Token 过期或无效，清除登录状态，跳转登录页
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          ElMessage.error('登录已过期，请重新登录')
          // 使用 window.location 避免在不同上下文中的 router 引用问题
          window.location.href = '/login'
          break
        case 403:
          ElMessage.error('没有权限操作')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 413:
          ElMessage.error('文件大小超过限制')
          break
        case 500:
          ElMessage.error(data.detail || '服务器内部错误')
          break
        default:
          ElMessage.error(data.detail || `请求失败 (${status})`)
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应（网络错误）
      ElMessage.error('网络错误，请检查服务器是否启动')
    } else {
      ElMessage.error('请求配置错误')
    }
    return Promise.reject(error)
  }
)

export default api
