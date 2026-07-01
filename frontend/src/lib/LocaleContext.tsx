/**
 * LocaleContext - 中英双语切换 Context
 * 
 * 功能：
 *   - 提供全局 locale 状态（'zh' | 'en'）
 *   - URL 路径同步：/en 前缀 ↔ 英文，无前缀 ↔ 中文
 *   - localStorage 持久化用户语言偏好（key: ai_locale）
 *   - 提供 t(zhText, enText) 快捷翻译函数
 * 
 * 导出：
 *   - LocaleProvider：Context Provider，包裹在 BrowserRouter 内部
 *   - useLocale()：获取 { locale, setLocale, t } 的 Hook
 *   - Locale 类型：'zh' | 'en'
 * 
 * 路由规则：
 *   - 中文（默认）：/、/weekly、/about ...（无 /en 前缀）
 *   - 英文：/en/、/en/weekly、/en/about ...（带 /en 前缀）
 *   用户在中文路径下切换到英文 → navigate 到 /en/... 路径
 *   用户在英文路径下切换到中文 → navigate 到 /... 路径
 */

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

/** 支持的语言类型 */
export type Locale = 'zh' | 'en'

/** LocaleContext 的值类型 */
interface LocaleContextType {
  locale: Locale
  setLocale: (l: Locale) => void
  t: (zh: string, en: string) => string
}

/** 创建 LocaleContext，默认值为中文 */
const LocaleContext = createContext<LocaleContextType>({
  locale: 'zh',
  setLocale: () => {},
  t: (zh) => zh,
})

/** useLocale Hook：获取当前 locale、setLocale、t 翻译函数 */
export function useLocale() {
  return useContext(LocaleContext)
}

/**
 * LocaleProvider - 语言上下文 Provider
 * 
 * 初始化逻辑：
 *   1. URL 以 /en 开头 → locale = 'en'
 *   2. 否则检查 localStorage 中的 ai_locale
 *   3. 默认 fallback 为 'zh'
 * 
 * URL 同步逻辑（两个 useEffect）：
 *   locale → URL：locale 变为 en 但路径无 /en → navigate 添加前缀
 *   URL → locale：路径有 /en 但 locale 不是 en → 更新 locale + localStorage
 */
export function LocaleProvider({ children }: { children: ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()

  /** locale：当前语言状态，初始值根据 URL 和 localStorage 决定 */
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (location.pathname.startsWith('/en')) return 'en'
    const saved = localStorage.getItem('ai_locale')
    if (saved === 'en' || saved === 'zh') return saved
    return 'zh'
  })

  /** locale 变化 → 同步 URL（添加/移除 /en 前缀） */
  useEffect(() => {
    const isEnPath = location.pathname.startsWith('/en')
    if (locale === 'en' && !isEnPath) {
      // 切换到英文：在路径前添加 /en 前缀
      const newPath = '/en' + location.pathname + location.search
      navigate(newPath, { replace: true })
    } else if (locale === 'zh' && isEnPath) {
      // 切换到中文：移除 /en 前缀
      const newPath = location.pathname.replace(/^\/en/, '') || '/'
      navigate(newPath + location.search, { replace: true })
    }
  }, [locale])

  /** URL 变化 → 同步 locale（仅当 URL 显式包含 /en 时） */
  useEffect(() => {
    const isEnPath = location.pathname.startsWith('/en')
    if (isEnPath && locale !== 'en') {
      setLocaleState('en')
      localStorage.setItem('ai_locale', 'en')
    }
    // 注意：不会因路径无 /en 就强制切回中文，尊重用户手动选择
  }, [location.pathname])

  /** setLocale：更新 locale 并持久化到 localStorage */
  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l)
    localStorage.setItem('ai_locale', l)
  }, [])

  /** t 翻译函数：根据当前 locale 返回中文或英文文案 */
  const t = useCallback((zh: string, en: string) => locale === 'en' ? en : zh, [locale])

  return (
    <LocaleContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </LocaleContext.Provider>
  )
}
