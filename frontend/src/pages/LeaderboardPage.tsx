import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import type { Article } from '../types'
import { ICON } from '../lib/icons'

export function LeaderboardPage() {
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/latest.json`)
      .then(r => r.json())
      .then(data => {
        const sorted = [...(data.articles || [])].sort((a, b) => (b.score || 0) - (a.score || 0))
        setArticles(sorted)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="text-center py-4">
        <h1 className="text-3xl font-bold text-text-primary flex items-center justify-center gap-2">
          <FontAwesomeIcon icon={ICON.leaderboard} className="text-accent" />
          排行榜
        </h1>
        <p className="mt-2 text-text-muted text-sm">按评分排序的文章</p>
      </div>

      <div className="space-y-2">
        {articles.slice(0, 100).map((a, i) => (
          <div
            key={i}
            className="flex items-center gap-4 bg-bg-card border border-border-muted rounded-xl p-4 hover:border-accent/20 transition-all"
          >
            <span className="text-2xl font-bold text-text-muted w-8 text-center tabular-nums">
              {i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <a
                href={a.link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-text-primary hover:text-accent transition-colors line-clamp-1"
              >
                {a.title_cn || a.title}
              </a>
              <div className="flex items-center gap-2 mt-1 text-xs text-text-muted">
                <span>{a.source}</span>
                <span>·</span>
                <span>{a.published}</span>
                {a.category && <span className="bg-bg-secondary px-1.5 py-0.5 rounded text-[10px]">{a.category}</span>}
              </div>
            </div>
            {a.score != null && (
              <div className="flex items-center gap-2 flex-shrink-0">
                <div className="w-16 h-1.5 bg-bg-secondary rounded-full">
                  <div
                    className="h-full bg-accent rounded-full"
                    style={{ width: `${Math.min(a.score, 100)}%` }}
                  />
                </div>
                <span className="text-sm font-bold text-accent tabular-nums w-8 text-right">{a.score}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
