import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faTrophy, faEye, faCode, faBrain, faDollarSign, faArrowsLeftRight, faArrowUpFromBracket, faCalendar, faSearch, faChartBar } from '@fortawesome/free-solid-svg-icons'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
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

const SCORE_COLORS = {
  intelligence: '#6C5CE7',
  coding: '#00b894',
  agentic: '#f0a050',
  elo: '#74b9ff',
}

function filterByTab(models: LeaderboardModel[], tab: Tab): LeaderboardModel[] {
  if (tab === 'all') return models
  if (tab === 'vision') return models.filter(m => m.tags.includes('vision') || m.tags.includes('video'))
  return models.filter(m => {
    const name = m.name.toLowerCase()
    const pid = m.id.toLowerCase()
    if (tab === 'coding') {
      return name.includes('code') || name.includes('coder') || pid.includes('code') ||
             name.includes('programming') || m.tags.includes('file')
    }
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

// ============ Score Bar ============
function ScoreBar({ value, color, label }: { value: number; color: string; label: string }) {
  const pct = Math.min(value, 100)
  return (
    <div className="flex items-center gap-1.5" title={`${label}: ${value}`}>
      <span className="text-[10px] text-text-muted w-8 text-right tabular-nums">{label}</span>
      <div className="flex-1 h-1.5 bg-bg-secondary rounded-full max-w-[60px]">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-[10px] font-mono text-text-muted w-7 tabular-nums">{pct}</span>
    </div>
  )
}

// ============ Model Row ============
function ModelRow({ model, isTop3 }: { model: LeaderboardModel; isTop3: boolean }) {
  const s = model.scores

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
            <span className="text-xs px-1.5 py-0.5 rounded bg-accent-muted text-accent font-medium flex-shrink-0">
              {model.provider}
            </span>
            {s?.best_elo && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-blue/15 text-blue font-semibold flex-shrink-0" title={`Best ELO: ${s.best_elo} (${s.best_elo_category})`}>
                ELO {s.best_elo}
              </span>
            )}
          </div>

          {/* Specs row */}
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-muted">
            <span className="inline-flex items-center gap-1">
              <FontAwesomeIcon icon={faDollarSign} className="text-[10px] text-green" />
              <span className="text-green font-medium">{model.price_input}</span>
              <span className="text-text-muted/50">/</span>
              <span className="text-green font-medium">{model.price_output}</span>
              <span className="text-text-muted/50">/1M</span>
            </span>

            <span className="inline-flex items-center gap-1">
              <FontAwesomeIcon icon={faArrowsLeftRight} className="text-[10px] text-blue" />
              <span className="text-blue">{model.context_display}</span>
            </span>

            {model.max_output && (
              <span className="inline-flex items-center gap-1">
                <FontAwesomeIcon icon={faArrowUpFromBracket} className="text-[10px] text-amber" />
                <span className="text-amber">{model.max_output}</span>
              </span>
            )}

            <span className="inline-flex items-center gap-1">
              <FontAwesomeIcon icon={faCalendar} className="text-[10px]" />
              {formatDate(model.created)}
            </span>
          </div>

          {/* Score bars */}
          {s && (s.intelligence || s.coding || s.agentic) && (
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-0.5">
              {s.intelligence != null && <ScoreBar value={s.intelligence} color={SCORE_COLORS.intelligence} label="AI" />}
              {s.coding != null && <ScoreBar value={s.coding} color={SCORE_COLORS.coding} label="Code" />}
              {s.agentic != null && <ScoreBar value={s.agentic} color={SCORE_COLORS.agentic} label="Agent" />}
            </div>
          )}

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

// ============ Skeleton ============
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

// ============ Score Comparison Chart ============
function ScoreChart({ models }: { models: LeaderboardModel[] }) {
  const chartData = useMemo(() => {
    const scored = models
      .filter(m => m.scores?.intelligence != null)
      .slice(0, 15)
      .map(m => ({
        name: m.name.split(':').pop()?.trim() || m.name,
        intelligence: m.scores!.intelligence ?? 0,
        coding: m.scores!.coding ?? 0,
        agentic: m.scores!.agentic ?? 0,
      }))
    return scored
  }, [models])

  if (chartData.length < 3) return null

  return (
    <div className="bg-bg-card border border-border-muted rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <FontAwesomeIcon icon={faChartBar} className="text-accent" />
        <h3 className="text-sm font-semibold text-text-primary">
          Top 15 模型能力对比
        </h3>
        <span className="text-xs text-text-muted">Artificial Analysis 评分</span>
      </div>
      <div className="flex items-center gap-4 mb-3 text-xs">
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm" style={{background: SCORE_COLORS.intelligence}} /> 智能</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm" style={{background: SCORE_COLORS.coding}} /> 编程</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm" style={{background: SCORE_COLORS.agentic}} /> 智能体</span>
      </div>
      <ResponsiveContainer width="100%" height={chartData.length * 28 + 40}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 0, right: 10, left: 10, bottom: 0 }}
          barSize={8}
          barGap={2}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--_border-muted, #161825)" />
          <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: 'var(--_text-muted, #686880)' }} />
          <YAxis
            type="category"
            dataKey="name"
            width={140}
            tick={{ fontSize: 11, fill: 'var(--_text-secondary, #9898b0)' }}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--_bg-elevated, #12141f)',
              border: '1px solid var(--_border-default, #1e2033)',
              borderRadius: '8px',
              fontSize: '12px',
              color: 'var(--_text-primary, #e8e9f0)',
            }}
          />
          <Bar dataKey="intelligence" fill={SCORE_COLORS.intelligence} radius={[0, 2, 2, 0]} />
          <Bar dataKey="coding" fill={SCORE_COLORS.coding} radius={[0, 2, 2, 0]} />
          <Bar dataKey="agentic" fill={SCORE_COLORS.agentic} radius={[0, 2, 2, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ============ HOME PAGE PREVIEW (compact Top 5) ============
export function ModelLeaderboardPreview() {
  const { data, loading } = useLeaderboard()

  if (loading) return null
  if (!data || !data.models.length) return null

  const top5 = data.models.slice(0, 5)

  return (
    <FadeIn delay={0.1}>
      <section className="mt-6">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FontAwesomeIcon icon={faTrophy} className="text-accent" />
            <h2 className="text-base font-semibold text-text-primary">最新模型</h2>
            <span className="text-xs text-text-muted">Top 5</span>
          </div>
          <Link
            to="/leaderboard"
            className="text-xs text-accent hover:text-accent-hover transition-colors font-medium"
          >
            查看全部 {data.total_models} 个模型 →
          </Link>
        </div>

        <div className="space-y-1.5">
          {top5.map((m, i) => (
            <Link
              key={m.id}
              to="/leaderboard"
              className="flex items-center gap-3 bg-bg-card border border-border-muted rounded-lg px-3 py-2.5 hover:border-accent/20 transition-all duration-200"
            >
              <span className={`flex-shrink-0 w-5 h-5 rounded-md flex items-center justify-center text-xs font-bold tabular-nums
                ${i < 3 ? 'bg-accent text-white' : 'bg-bg-hover text-text-muted'}`}>
                {i + 1}
              </span>
              <span className="flex-1 text-sm text-text-primary font-medium truncate">{m.name}</span>
              <span className="text-xs text-text-muted flex-shrink-0">{m.provider}</span>
              <span className="text-xs text-green font-mono flex-shrink-0">{m.price_input}</span>
            </Link>
          ))}
        </div>
      </section>
    </FadeIn>
  )
}

// ============ FULL PAGE (for /leaderboard) ============
export function ModelLeaderboard() {
  const { data, loading } = useLeaderboard()
  const [tab, setTab] = useState<Tab>('all')
  const [query, setQuery] = useState('')

  const models = useMemo(() => {
    if (!data) return []
    let filtered = filterByTab(data.models, tab)
    if (query.trim().length > 0) {
      const q = query.toLowerCase()
      filtered = filtered.filter(m =>
        m.name.toLowerCase().includes(q) ||
        m.provider.toLowerCase().includes(q) ||
        m.id.toLowerCase().includes(q) ||
        m.tags.some(t => t.toLowerCase().includes(q))
      )
    }
    return filtered
  }, [data, tab, query])

  const displayModels = models.slice(0, 50)

  return (
    <FadeIn>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
              <FontAwesomeIcon icon={faTrophy} className="text-accent" />
              AI 模型排行榜
            </h1>
            <p className="text-text-muted text-sm mt-1">
              数据来源 OpenRouter + Artificial Analysis · 每日更新 · {data?.total_models ?? '?'} 个模型
            </p>
          </div>
        </div>

        {/* Score comparison chart */}
        {data && <ScoreChart models={data.models} />}

        {/* Search + Tabs */}
        <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
          <div className="relative flex-1 max-w-sm">
            <FontAwesomeIcon icon={faSearch} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="搜索模型或机构..."
              className="w-full bg-bg-secondary border border-border-default rounded-lg pl-9 pr-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50 transition-colors"
            />
          </div>

          <div className="flex gap-1 overflow-x-auto">
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
        </div>

        {/* Model list */}
        <div className="space-y-2">
          {loading ? (
            Array.from({ length: 8 }, (_, i) => <SkeletonRow key={i} />)
          ) : displayModels.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              {query ? '没有匹配的模型' : '暂无数据'}
            </div>
          ) : (
            displayModels.map((model, i) => (
              <ScrollReveal key={model.id} index={i}>
                <ModelRow model={model} isTop3={model.rank <= 3} />
              </ScrollReveal>
            ))
          )}
        </div>

        {models.length > 50 && (
          <div className="text-center py-4 text-xs text-text-muted">
            显示前 50 个，共 {models.length} 个匹配模型
          </div>
        )}
      </div>
    </FadeIn>
  )
}
