/**
 * Vue Router 路由配置
 * 包含路由守卫：未登录用户自动跳转登录页
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    // 登录页不需要布局组件，独立渲染
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', noAuth: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { title: '注册', noAuth: true },
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '仪表盘' },
  },
  {
    path: '/meetings',
    name: 'MeetingList',
    component: () => import('../views/MeetingList.vue'),
    meta: { title: '会议列表' },
  },
  {
    path: '/upload',
    name: 'MeetingUpload',
    component: () => import('../views/MeetingUpload.vue'),
    meta: { title: '上传会议' },
  },
  {
    path: '/meetings/:id',
    name: 'MeetingDetail',
    component: () => import('../views/MeetingDetail.vue'),
    meta: { title: '会议纪要详情' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ============================================================
// 全局路由守卫：检查登录状态
// 未登录用户访问需认证的页面时，重定向到登录页
// ============================================================
router.beforeEach((to, _from, next) => {
  // 设置页面标题
  document.title = to.meta.title
    ? `${to.meta.title} - 智能会议纪要助手`
    : '基于LangChain的智能会议纪要助手系统'

  // 检查 token 是否存在
  const token = localStorage.getItem('token')

  // 如果路由不需要认证，直接放行
  if (to.meta.noAuth) {
    // 如果已登录用户访问登录/注册页，跳转到首页
    if (token && (to.path === '/login' || to.path === '/register')) {
      next('/')
    } else {
      next()
    }
    return
  }

  // 需要认证但没有 token，跳转到登录页
  if (!token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  next()
})

export default router
