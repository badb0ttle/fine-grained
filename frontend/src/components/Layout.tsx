import { NavLink } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { cn } from '../lib/utils'
import { ICON } from '../lib/icons'

const NAV_ITEMS = [
  { to: '/', label: '首页', icon: ICON.home, end: true },
  { to: '/dashboard', label: '仪表盘', icon: ICON.dashboard },
  { to: '/leaderboard', label: '排行榜', icon: ICON.leaderboard },
  { to: '/timeline', label: '时间线', icon: ICON.timeline },
  { to: '/clusters', label: '聚类', icon: ICON.clusters },
]

export function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-bg-primary/80 backdrop-blur-md border-b border-border-default">
      <div className="mx-auto max-w-6xl px-4 h-14 flex items-center justify-between">
        <NavLink to="/" className="font-semibold text-lg tracking-tight text-text-primary hover:text-accent transition-colors flex items-center gap-2">
          <FontAwesomeIcon icon={ICON.robot} className="text-accent" />
          AI 情报站
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
        </nav>
      </div>
    </header>
  )
}

export function Footer() {
  return (
    <footer className="mt-auto py-8 text-center text-text-muted text-sm border-t border-border-muted">
      <p>
        <a href="https://ai.hjhai.xyz" className="hover:text-accent transition-colors">ai.hjhai.xyz</a>
        {' · '}自动生成 ·{' '}
        <a href="https://github.com/badb0ttle/fine-grained" target="_blank" rel="noopener noreferrer" className="hover:text-accent transition-colors">
          GitHub
        </a>
      </p>
    </footer>
  )
}
