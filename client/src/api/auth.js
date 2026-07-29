/**
 * 认证相关 API 接口
 * 包含注册、登录、获取当前用户信息
 */
import api from './index'

/**
 * 用户注册
 * @param {Object} data - { username, password, email }
 * @returns {Promise} { access_token, token_type, user }
 */
export function register(data) {
  return api.post('/auth/register', data)
}

/**
 * 用户登录
 * @param {Object} data - { username, password }
 * @returns {Promise} { access_token, token_type, user }
 */
export function login(data) {
  return api.post('/auth/login', data)
}

/**
 * 获取当前登录用户信息
 * @returns {Promise} 用户信息对象
 */
export function getCurrentUser() {
  return api.get('/auth/me')
}
