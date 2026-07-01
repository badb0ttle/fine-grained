/**
 * main.tsx - 应用入口文件
 * 
 * 功能：挂载 React 根组件到 DOM，配置全局 Provider 层级
 * 
 * Provider 层级（外→内）：
 *   1. StrictMode       — React 开发模式严格检查
 *   2. BrowserRouter    — react-router-dom 路由（HashRouter 不适用，因需要 SPA 404 回退支持）
 *   3. LocaleProvider   — 中英双语 Context（同步 URL 前缀 /en）
 *   4. App              — 根组件（路由 + 布局 + 主题）
 * 
 * 入口 CSS：./index.css（Tailwind CSS v4 + 全局样式 + CSS 变量）
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { LocaleProvider } from './lib/LocaleContext'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <LocaleProvider>
        <App />
      </LocaleProvider>
    </BrowserRouter>
  </StrictMode>,
)
