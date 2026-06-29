import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

export type Locale = 'zh' | 'en'

interface LocaleContextType {
  locale: Locale
  setLocale: (l: Locale) => void
  t: (zh: string, en: string) => string
}

const LocaleContext = createContext<LocaleContextType>({
  locale: 'zh',
  setLocale: () => {},
  t: (zh) => zh,
})

export function useLocale() {
  return useContext(LocaleContext)
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (location.pathname.startsWith('/en')) return 'en'
    // Check localStorage
    const saved = localStorage.getItem('ai_locale')
    if (saved === 'en' || saved === 'zh') return saved
    return 'zh'
  })

  // Sync URL with locale
  useEffect(() => {
    const isEnPath = location.pathname.startsWith('/en')
    if (locale === 'en' && !isEnPath) {
      const newPath = '/en' + location.pathname + location.search
      navigate(newPath, { replace: true })
    } else if (locale === 'zh' && isEnPath) {
      const newPath = location.pathname.replace(/^\/en/, '') || '/'
      navigate(newPath + location.search, { replace: true })
    }
  }, [locale])

  // Sync locale from URL (only when URL explicitly has /en prefix)
  useEffect(() => {
    const isEnPath = location.pathname.startsWith('/en')
    if (isEnPath && locale !== 'en') {
      setLocaleState('en')
      localStorage.setItem('ai_locale', 'en')
    }
    // Don't force zh when path lacks /en — let user preference persist
  }, [location.pathname])

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l)
    localStorage.setItem('ai_locale', l)
  }, [])

  const t = useCallback((zh: string, en: string) => locale === 'en' ? en : zh, [locale])

  return (
    <LocaleContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </LocaleContext.Provider>
  )
}
