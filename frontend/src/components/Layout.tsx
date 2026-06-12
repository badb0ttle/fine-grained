import { NavLink } from 'react-router-dom'
import { cn } from '../lib/utils'

const NAV_ITEMS = [
  { to: '/', label: '🏠 首页', end: true },
  { to: '/dashboard', label: '📊 仪表盘' },
  { to: '/leaderboard', label: '🏆 排行榜' },
  { to: '/timeline', label: '📅 时间线' },
  { to: '/clusters', label: '🗺️ 聚类' },
]

export function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-bg-primary/80 backdrop-blur-md border-b border-border-default">
      <div className="mx-auto max-w-6xl px-4 h-14 flex items-center justify-between">
        <NavLink to="/" className="font-semibold text-lg tracking-tight text-text-primary hover:text-accent transition-colors">
          🤖 AI 情报站
        </NavLink>
        <nav className="flex items-center gap-1 overflow-x-auto">
          {NAV_ITEMS.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => cn(
                'px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
                isActive
                  ? 'bg-accent-muted text-accent'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
              )}
            >
              {item.label}
            </NavLink>
          ))}
          <a
            href="/data/weekly/"
            className="px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
          >
            📰 周报
          </a>
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
