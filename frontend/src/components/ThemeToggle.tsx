/**
 * ThemeToggle - 暗色/亮色主题切换（ThemeContext + ThemeProvider + useTheme Hook）
 * 
 * 功能：
 *   - ThemeProvider：主题 Context Provider，管理全局 theme 状态
 *   - useTheme() Hook：获取 { theme, toggle } 的便捷方法
 *   - 主题持久化：localStorage 存储用户选择（key: theme）
 *   - 系统主题跟随：首次访问时读取 prefers-color-scheme 媒体查询
 *   - 系统主题变更监听：未手动设置时自动跟随系统
 *   - 主题应用：通过 document.documentElement.classList 添加/移除 'light' class
 * 
 * 导出：
 *   - ThemeProvider：包裹在 App 组件最外层
 *   - useTheme()：任意组件获取主题状态和切换函数
 */

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

/** 主题类型：暗色 dark / 亮色 light */
type Theme = 'dark' | 'light'

/** ThemeContext 的 value 类型 */
interface ThemeCtx {
  theme: Theme
  toggle: () => void
}

/** 创建 ThemeContext，默认值为暗色 */
const ThemeContext = createContext<ThemeCtx>({ theme: 'dark', toggle: () => {} })

/** useTheme Hook：在任意组件中获取当前 theme 和 toggle 切换函数 */
export function useTheme() {
  return useContext(ThemeContext)
}

/** 读取系统主题偏好（prefers-color-scheme 媒体查询） */
function getSystemTheme(): Theme {
  if (typeof window === 'undefined') return 'dark'
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

/** 将主题应用到 DOM：添加/移除 documentElement 上的 'light' class */
function applyTheme(theme: Theme) {
  const root = document.documentElement
  if (theme === 'light') {
    root.classList.add('light')
  } else {
    root.classList.remove('light')
  }
}

/** ThemeProvider - 主题 Context Provider */
export function ThemeProvider({ children }: { children: ReactNode }) {
  /** theme 状态：优先从 localStorage 读取，否则跟随系统 */
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = localStorage.getItem('theme') as Theme | null
    return stored || getSystemTheme()
  })

  /** theme 变化时：应用到 DOM + 持久化到 localStorage */
  useEffect(() => {
    applyTheme(theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  /** 监听系统主题变化（仅当用户未手动设置主题时跟随） */
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: light)')
    const handler = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem('theme')) {
        setTheme(e.matches ? 'light' : 'dark')
      }
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  return (
    <ThemeContext.Provider value={{ theme, toggle: () => setTheme(t => t === 'dark' ? 'light' : 'dark') }}>
      {children}
    </ThemeContext.Provider>
  )
}
