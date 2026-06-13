import { NavLink } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { cn } from '../lib/utils'
import { ICON } from '../lib/icons'
import { useTheme } from './ThemeToggle'

const NAV_ITEMS = [
  { to: '/', label: '首页', icon: ICON.home, end: true },
  { to: '/leaderboard', label: '排行榜', icon: ICON.leaderboard },
  { to: '/timeline', label: '时间线', icon: ICON.timeline },
  { to: '/clusters', label: '聚类', icon: ICON.clusters },
  { to: '/about', label: '关于', icon: ICON.infoCircle },
]

export function Header() {
  const { theme, toggle } = useTheme()

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-bg-primary/80 backdrop-blur-md border-b border-border-default">
      <div className="mx-auto max-w-6xl px-4 h-14 flex items-center justify-between">
        <NavLink to="/" className="font-semibold text-lg tracking-tight text-text-primary hover:text-accent transition-colors flex items-center gap-2">
          <FontAwesomeIcon icon={ICON.robot} className="text-accent" />
          AllOfAI
        </NavLink>
        <nav className="flex items-center gap-1 overflow-x-auto">
          {NAV_ITEMS.map(item => (
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
            to="/weekly"
            className={({ isActive }) => cn(
              'px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors flex items-center gap-1.5',
              isActive
                ? 'bg-accent-muted text-accent'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
            )}
          >
            <FontAwesomeIcon icon={ICON.weekly} className="text-xs" />
            周报
          </NavLink>
          <a
            href="https://github.com/badb0ttle/fine-grained"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
          >
            GitHub
          </a>
          <button
            onClick={toggle}
            className="ml-1 w-8 h-8 rounded-lg flex items-center justify-center text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
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
  return (
    <footer className="mt-auto py-8 text-center text-text-muted text-sm border-t border-border-muted">
      <p>
        Copyright © 2026 ℬ𝒶𝒹𝒷0𝓉𝓉𝓁ℯ
      </p>
    </footer>
  )
}
