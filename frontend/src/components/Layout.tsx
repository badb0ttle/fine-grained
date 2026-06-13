import { NavLink } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { cn } from '../lib/utils'
import { ICON } from '../lib/icons'
import { useTheme } from './ThemeToggle'
import { useLocale } from '../lib/LocaleContext'

export function Header() {
  const { theme, toggle } = useTheme()
  const { locale, setLocale } = useLocale()
  const prefix = locale === 'en' ? '/en' : ''

  const navItems = [
    { to: `${prefix}/`, label: locale === 'en' ? 'Home' : '首页', icon: ICON.home, end: true },
    { to: `${prefix}/leaderboard`, label: locale === 'en' ? 'Leaderboard' : '排行榜', icon: ICON.leaderboard },
    { to: `${prefix}/timeline`, label: locale === 'en' ? 'Timeline' : '时间线', icon: ICON.timeline },
    { to: `${prefix}/clusters`, label: locale === 'en' ? 'Clusters' : '聚类', icon: ICON.clusters },
    { to: `${prefix}/about`, label: locale === 'en' ? 'About' : '关于', icon: ICON.infoCircle },
  ]

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-bg-primary/80 backdrop-blur-md border-b border-border-default">
      <div className="mx-auto max-w-6xl px-4 h-14 flex items-center justify-between">
        <NavLink to={`${prefix}/`} className="font-semibold text-lg tracking-tight text-text-primary hover:text-accent transition-colors flex items-center gap-2">
          <FontAwesomeIcon icon={ICON.robot} className="text-accent" />
          AllOfAI
        </NavLink>
        <nav className="flex items-center gap-1 overflow-x-auto">
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => cn(
                'px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors flex items-center gap-1.5',
                isActive
                  ? 'bg-accent-muted text-accent'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
              )}
            >
              <FontAwesomeIcon icon={item.icon} className="text-xs" />
              {item.label}
            </NavLink>
          ))}
          <NavLink
            to={`${prefix}/weekly`}
            className={({ isActive }) => cn(
              'px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors flex items-center gap-1.5',
              isActive
                ? 'bg-accent-muted text-accent'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
            )}
          >
            <FontAwesomeIcon icon={ICON.weekly} className="text-xs" />
            {locale === 'en' ? 'Weekly' : '周报'}
          </NavLink>
          <a
            href="https://github.com/badb0ttle/fine-grained"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
          >
            GitHub
          </a>

          {/* Language toggle */}
          <button
            onClick={() => setLocale(locale === 'zh' ? 'en' : 'zh')}
            className="ml-1 px-2 py-1 rounded-lg text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
            aria-label="Switch language"
          >
            {locale === 'zh' ? 'EN' : '中'}
          </button>

          <button
            onClick={toggle}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
            aria-label={theme === 'dark' ? '切换浅色模式' : '切换深色模式'}
          >
            <FontAwesomeIcon icon={theme === 'dark' ? ICON.sun : ICON.moon} className="text-sm" />
          </button>
        </nav>
      </div>
    </header>
  )
}

export function Footer() {
  const { locale } = useLocale()
  return (
    <footer className="mt-auto py-8 text-center text-text-muted text-sm border-t border-border-muted">
      <p>
        {locale === 'en'
          ? 'Copyright © 2026 ℬ𝒶𝒹𝒷0𝓉𝓉𝓁ℯ'
          : 'Copyright © 2026 ℬ𝒶𝒹𝒷0𝓉𝓉𝓁ℯ'
        }
      </p>
    </footer>
  )
}
