/**
 * App - 根组件，全局路由与布局配置
 * 
 * 功能概述：
 *   - 定义整个 SPA 的路由树（支持中/英双语路径：/ 和 /en/ 前缀）
 *   - 页面级代码分割（React.lazy + Suspense）
 *   - 页面切换动画（framer-motion AnimatePresence + PageTransition）
 *   - SPA 重定向支持（从 404.html 回来的 sessionStorage redirect）
 *   - 全局 Provider 层级：ThemeProvider → ToastProvider → 粒子背景 → 布局
 * 
 * 组件层级：
 *   ThemeProvider（暗色/亮色主题）
 *    └─ ToastProvider（全局通知）
 *       └─ ParticleBackground（Canvas 粒子动画背景）
 *       └─ ReadingProgress（阅读进度条）
 *       └─ Header（导航栏 + 语言/主题切换）
 *       └─ main（页面内容区）
 *       └─ Footer（页脚）
 *       └─ BackToTop（回到顶部浮动按钮）
 * 
 * 路由表：
 *   /                    → HomePage（首页）
 *   /dashboard           → AdminGate → DashboardPage（管理仪表盘，密码保护）
 *   /leaderboard         → LeaderboardPage（模型排行榜）
 *   /timeline            → TimelinePage（时间线）
 *   /clusters            → ClustersPage（话题聚类）
 *   /weekly              → WeeklyPage（周报列表）
 *   /weekly/:date        → WeeklyDetailPage（周报详情）
 *   /category/:name      → CategoryPage（按分类浏览）
 *   /about               → AboutPage（关于页）
 *   /en/*                → 同上（英文路径，LocaleContext 自动切换语言）
 */

import { lazy, Suspense, useEffect } from 'react'
import { useNavigate, useLocation, useRoutes } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Header, Footer } from './components/Layout'
import { PageTransition } from './components/Animations'
import { ReadingProgress } from './components/ReadingProgress'
import { BackToTop } from './components/BackToTop'
import { ToastProvider } from './components/Toast'
import { AdminGate } from './components/AdminGate'
import ParticleBackground from './components/ParticleBackground'
import { ThemeProvider } from './components/ThemeToggle'

// ── 页面级代码分割（React.lazy + dynamic import）──
// 所有页面组件均按需加载，减小首屏 bundle 体积
const HomePage         = lazy(() => import('./pages/HomePage').then(m => ({ default: m.HomePage })) as any)
const DashboardPage    = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })) as any)
const LeaderboardPage  = lazy(() => import('./pages/LeaderboardPage').then(m => ({ default: m.LeaderboardPage })) as any)
const TimelinePage     = lazy(() => import('./pages/TimelinePage').then(m => ({ default: m.TimelinePage })) as any)
const ClustersPage     = lazy(() => import('./pages/ClustersPage').then(m => ({ default: m.ClustersPage })) as any)
const WeeklyPage       = lazy(() => import('./pages/WeeklyPage').then(m => ({ default: m.WeeklyPage })) as any)
const WeeklyDetailPage = lazy(() => import('./pages/WeeklyDetailPage').then(m => ({ default: m.WeeklyDetailPage })) as any)
const CategoryPage     = lazy(() => import('./pages/CategoryPage').then(m => ({ default: m.CategoryPage })) as any)
const AboutPage        = lazy(() => import('./pages/AboutPage').then(m => ({ default: m.AboutPage })) as any)

/**
 * PageFallback - 页面 Suspense 加载中状态
 * 显示居中的旋转加载动画（Tailwind animate-spin）
 */
function PageFallback() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

/**
 * SpaRedirect - SPA 重定向组件
 * 
 * 背景：GitHub Pages SPA 部署中，404 页面（404.html）会保存当前 URL 到
 *       sessionStorage.redirect，然后重定向到根路径。
 *       此组件检查 sessionStorage 中的 redirect 值并执行导航
 */
function SpaRedirect() {
  const navigate = useNavigate()
  useEffect(() => {
    const redirect = sessionStorage.getItem('redirect')
    if (redirect) {
      sessionStorage.removeItem('redirect')
      navigate(redirect, { replace: true })
    }
  }, [navigate])
  return null
}

/**
 * buildRoutes - 构建给定前缀的路由树
 * 
 * 支持两组路由：空前缀（中文路径 /xxx）和 /en 前缀（英文路径 /en/xxx）
 * 两组路由共享相同的页面组件，通过 LocaleContext 自动切换语言
 * /dashboard 路由额外包裹 <AdminGate> 进行密码验证
 */
function buildRoutes(prefix = '') {
  return [
    { path: `${prefix}/`, element: <HomePage /> },
    { path: `${prefix}/dashboard`, element: <AdminGate><DashboardPage /></AdminGate> },
    { path: `${prefix}/leaderboard`, element: <LeaderboardPage /> },
    { path: `${prefix}/timeline`, element: <TimelinePage /> },
    { path: `${prefix}/clusters`, element: <ClustersPage /> },
    { path: `${prefix}/weekly`, element: <WeeklyPage /> },
    { path: `${prefix}/weekly/:date`, element: <WeeklyDetailPage /> },
    { path: `${prefix}/category/:name`, element: <CategoryPage /> },
    { path: `${prefix}/about`, element: <AboutPage /> },
  ]
}

/**
 * AppRoutes - 合并中文和英文路由树
 * 使用 react-router-dom v6 的 useRoutes() 声明式路由
 */
function AppRoutes() {
  return useRoutes([
    ...buildRoutes(''),      // 中文路径：/
    ...buildRoutes('/en'),   // 英文路径：/en/
  ])
}

/**
 * AnimatedRoutes - 带页面切换动画的路由渲染
 * 
 * 使用 key={location.pathname} 确保每次路由变化触发离场/入场动画
 * AnimatePresence mode="wait" 保证旧页面先离场，新页面再入场
 */
function AnimatedRoutes() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <PageTransition key={location.pathname}>
        <SpaRedirect />
        <Suspense fallback={<PageFallback />}>
          <AppRoutes />
        </Suspense>
      </PageTransition>
    </AnimatePresence>
  )
}

/**
 * App - 应用根组件
 * 
 * Provider 嵌套顺序（外→内）：
 *   ThemeProvider → ToastProvider → 全局布局
 * 
 * 全局 UI 元素：
 *   - ParticleBackground：Canvas 粒子动画背景（fixed，始终可见）
 *   - ReadingProgress：页面顶部水平阅读进度条
 *   - Header：顶部导航栏（含语言切换、主题切换）
 *   - main：页面内容（z-10 确保在粒子上方）
 *   - Footer：页脚
 *   - BackToTop：回到顶部浮动按钮
 */
export default function App() {
  return (
    <ThemeProvider>
    <ToastProvider>
      <div className="min-h-dvh flex flex-col relative">
        <ParticleBackground />
        <ReadingProgress />
        <Header />
        <main className="flex-1 mx-auto w-full max-w-6xl px-4 pt-20 pb-8 relative z-10">
          <AnimatedRoutes />
        </main>
        <Footer />
        <BackToTop />
      </div>
    </ToastProvider>
    </ThemeProvider>
  )
}
