/**
 * Vue 应用入口文件
 * 基于LangChain的智能会议纪要助手系统 - 前端
 */
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

import App from './App.vue'
import router from './router'
import './styles/global.css'

// 创建 Vue 应用实例
const app = createApp(App)

// 使用 Element Plus 组件库（中文语言包）
app.use(ElementPlus, { locale: zhCn })

// 使用 Vue Router 路由
app.use(router)

// 全局注册 Element Plus 图标组件，可在模板中直接使用
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
