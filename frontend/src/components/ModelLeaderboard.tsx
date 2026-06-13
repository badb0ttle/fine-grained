import { useState, useMemo } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faTrophy, faEye, faCode, faBrain, faDollarSign, faArrowsLeftRight, faArrowUpFromBracket, faCalendar } from '@fortawesome/free-solid-svg-icons'
import { useLeaderboard } from '../hooks/useData'
import type { LeaderboardModel } from '../types'
import { ScrollReveal, FadeIn } from './Animations'

type Tab = 'all' | 'vision' | 'coding' | 'reasoning'

const TABS: { key: Tab; label: string; icon: typeof faTrophy }[] = [
  { key: 'all', label: '全部', icon: faTrophy },
  { key: 'vision', label: '视觉', icon: faEye },
  { key: 'coding', label: '编程', icon: faCode },
  { key: 'reasoning', label: '推理', icon: faBrain },
]

function filterByTab(models: LeaderboardModel[], tab: Tab): LeaderboardModel[] {
  if (tab === 'all') return models
  if (tab === 'vision') return models.filter(m => m.tags.includes('vision') || m.tags.includes('video'))
  return models.filter(m => {
    const name = m.name.toLowerCase()
    const pid = m.id.toLowerCase()
    // Coding models: code/coder/programming in name, or from providers known for coding
    if (tab === 'coding') {
      return name.includes('code') || name.includes('coder') || pid.includes('code') ||
             name.includes('programming') || name.includes('dev') ||
             m.tags.includes('file')
    }
    // Reasoning models: think/reason/o1/r1 etc in name
    if (tab === 'reasoning') {
      return name.includes('think') || name.includes('reason') ||
             name.includes('o1') || name.includes('o3') || name.includes('o4') ||
             pid.includes('reason')
    }
    return false
  })
}

function formatDate(unix: number): string {
  if (!unix) return '?'
  return new Date(unix * 1000).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function ModelRow({ model }: { model: LeaderboardModel }) {
  const isTop3 = model.rank <= 3

  return (
    <div className="bg-bg-card border border-border-muted rounded-xl p-4 hover:border-accent/20 transition-all duration-300">
      <div className="flex items-start gap-3">
        {/* Rank */}
        <span className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold tabular-nums
          ${isTop3 ? 'bg-accent text-white' : 'bg-bg-hover text-text-muted'}`}>
          {model.rank}
        </span>

        {/* Main info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-[15px] text-text-primary truncate">
              {model.name}
            </span>
            {/* Provider badge */}
            <span className="text-xs px-1.5 py-0.5 rounded bg-accent-muted text-accent font-medium flex-shrink-0">
              {model.provider}
            </span>
          </div>

          {/* Specs row */}
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-muted">
            {/* Price */}
            <span className="inline-flex items-center gap-1" title="Input / Output price per 1M tokens">
              <FontAwesomeIcon icon={faDollarSign} className="text-[10px] text-green" />
              <span className="text-green font-medium">{model.price_input}</span>
              <span className="text-text-muted/50">/</span>
              <span className="text-green font-medium">{model.price_output}</span>
              <span className="text-text-muted/50">/1M</span>
            </span>

            {/* Context */}
            <span className="inline-flex items-center gap-1" title="Context window">
              <FontAwesomeIcon icon={faArrowsLeftRight} className="text-[10px] text-blue" />
              <span className="text-blue">{model.context_display}</span>
            </span>

            {/* Max output */}
            {model.max_output && (
              <span className="inline-flex items-center gap-1" title="Max output tokens">
                <FontAwesomeIcon icon={faArrowUpFromBracket} className="text-[10px] text-amber" />
                <span className="text-amber">{model.max_output}</span>
              </span>
            )}

            {/* Date */}
            <span className="inline-flex items-center gap-1" title="Release date">
              <FontAwesomeIcon icon={faCalendar} className="text-[10px]" />
              {formatDate(model.created)}
            </span>
          </div>

          {/* Tags */}
          {model.tags.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {model.tags.map(tag => (
                <span key={tag} className="text-[11px] px-1.5 py-0.5 rounded bg-bg-secondary text-text-muted/70 font-mono">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function SkeletonRow() {
  return (
    <div className="bg-bg-card border border-border-muted rounded-xl p-4 animate-pulse">
      <div className="flex items-start gap-3">
        <span className="w-7 h-7 rounded-lg bg-bg-hover" />
        <div className="flex-1 space-y-2">
          <div className="flex gap-2">
            <div className="h-4 bg-bg-hover rounded w-48" />
            <div className="h-4 bg-bg-hover rounded w-16" />
          </div>
          <div className="flex gap-3">
            <div className="h-3 bg-bg-hover rounded w-24" />
            <div className="h-3 bg-bg-hover rounded w-16" />
            <div className="h-3 bg-bg-hover rounded w-20" />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function ModelLeaderboard() {
  const { data, loading } = useLeaderboard()
  const [tab, setTab] = useState<Tab>('all')

  const models = useMemo(() => {
    if (!data) return []
    return filterByTab(data.models, tab)
  }, [data, tab])

  // Show top 30 for better performance
  const displayModels = models.slice(0, 30)

  return (
    <FadeIn delay={0.1}>
      <section className="mt-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FontAwesomeIcon icon={faTrophy} className="text-accent" />
            <h2 className="text-lg font-semibold text-text-primary">
              AI 模型排行榜
            </h2>
            {data && (
              <span className="text-xs text-text-muted bg-bg-secondary px-2 py-0.5 rounded-full">
                {data.total_models} 个模型
              </span>
            )}
          </div>
          <span className="text-xs text-text-muted">
            via OpenRouter
          </span>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-3 overflow-x-auto pb-1">
          {TABS.map(({ key, label, icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap
                ${tab === key
                  ? 'bg-accent text-white shadow-sm'
                  : 'bg-bg-secondary text-text-muted hover:text-text-secondary hover:bg-bg-hover'
                }`}
            >
              <FontAwesomeIcon icon={icon} className="text-xs" />
              {label}
            </button>
          ))}
        </div>

        {/* Model list */}
        <div className="space-y-2">
          {loading ? (
            Array.from({ length: 6 }, (_, i) => <SkeletonRow key={i} />)
          ) : displayModels.length === 0 ? (
            <div className="text-center py-8 text-text-muted text-sm">
              暂无数据
            </div>
          ) : (
            displayModels.map((model, i) => (
              <ScrollReveal key={model.id} index={i}>
                <ModelRow model={model} />
              </ScrollReveal>
            ))
          )}
        </div>

        {/* View more link */}
        {models.length > 30 && (
          <div className="text-center mt-4">
            <span className="text-xs text-text-muted">
              显示前 30 个，共 {models.length} 个模型
            </span>
          </div>
        )}
      </section>
    </FadeIn>
  )
}
