import { useEffect, useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { ICON } from '../lib/icons'
import { FadeIn } from '../components/Animations'
import { CardSkeleton } from '../components/Skeleton'

// Chart colors from the existing palette
const CHART_COLORS = ['#6C5CE7', '#00b894', '#f0a050', '#74b9ff', '#fd79a8', '#e17055', '#a29bfe', '#55efc4']

interface StatsData {
  daily_trends: { date: string; new_articles: number; curated_count: number; total_articles: number }[]
  category_distribution: Record<string, number>
  source_health: { name: string; status: string; category: string }[]
  top_articles: { title: string; score: number; source: string; category: string }[]
}

interface LeaderboardData {
  models: { name: string; provider: string; scores: { intelligence?: number } | null }[]
}

export function WeeklyDetailPage() {
  const { date } = useParams<{ date: string }>()
  const [html, setHtml] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [stats, setStats] = useState<StatsData | null>(null)
  const [leaderboard, setLeaderboard] = useState<LeaderboardData | null>(null)

  useEffect(() => {
    if (!date) return
    const url = `${import.meta.env.BASE_URL}data/weekly/${date}.html`

    // Fetch everything in parallel
    Promise.all([
      fetch(url),
      fetch(`${import.meta.env.BASE_URL}data/stats.json`).then(r => r.ok ? r.json() : null),
      fetch(`${import.meta.env.BASE_URL}data/model_leaderboard.json`).then(r => r.ok ? r.json() : null),
    ])
      .then(([htmlRes, statsData, lbData]) => {
        if (!htmlRes.ok) throw new Error('Not found')
        setStats(statsData)
        setLeaderboard(lbData)
        return htmlRes.text()
      })
      .then(raw => {
        const titleMatch = raw.match(/<title>(.*?)<\/title>/)
        if (titleMatch) document.title = titleMatch[1]

        let body = raw
        const bodyStart = body.indexOf('<body>')
        const bodyEnd = body.indexOf('</body>')
        if (bodyStart >= 0 && bodyEnd >= 0) {
          body = body.slice(bodyStart + 6, bodyEnd)
        }
        body = body.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
        body = body.replace(/\sstyle="[^"]*"/gi, '')
        body = body.replace(/\sclass="[^"]*"/gi, '')
        body = body.replace(/href="index\.html"/g, 'href="/weekly"')
        body = body
          .replace(/<h1>/g, '<h1 class="text-2xl font-bold text-text-primary mt-4 mb-3">')
          .replace(/<h2>/g, '<h2 class="text-lg font-semibold text-accent mt-6 mb-2">')
          .replace(/<p>/g, '<p class="text-text-secondary leading-relaxed my-3">')
          .replace(/<strong>/g, '<strong class="text-text-primary font-semibold">')
          .replace(/<a /g, '<a class="text-accent hover:text-accent-hover transition-colors" ')

        setHtml(body)
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [date])

  // Compute week-specific data from stats
  const weekStats = useMemo(() => {
    if (!stats || !date) return null
    const d = new Date(date + 'T00:00:00')
    const weekStart = new Date(d)
    weekStart.setDate(d.getDate() - 6)
    const startStr = weekStart.toISOString().slice(0, 10)

    const weekTrends = (stats.daily_trends || [])
      .filter(t => t.date >= startStr && t.date <= date)
      .sort((a, b) => a.date.localeCompare(b.date))

    const totalArticles = weekTrends.reduce((s, t) => s + (t.new_articles || 0), 0)
    const totalCurated = weekTrends.reduce((s, t) => s + (t.curated_count || 0), 0)
    const avgPerDay = weekTrends.length ? Math.round(totalArticles / weekTrends.length) : 0

    // Category distribution for pie chart
    const catEntries = Object.entries(stats.category_distribution || {})
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)

    // Source health summary
    const healthySources = (stats.source_health || []).filter(s => s.status === 'healthy').length
    const totalSources = (stats.source_health || []).length

    // Top 5 models
    const top5 = (leaderboard?.models || [])
      .filter(m => m.scores?.intelligence != null)
      .sort((a, b) => (b.scores!.intelligence ?? 0) - (a.scores!.intelligence ?? 0))
      .slice(0, 5)

    return {
      weekTrends,
      totalArticles,
      totalCurated,
      avgPerDay,
      catEntries,
      healthySources,
      totalSources,
      top5,
    }
  }, [stats, leaderboard, date])

  if (loading) {
    return <div className="space-y-4 pt-8"><CardSkeleton /></div>
  }

  if (error || !html) {
    return (
      <div className="text-center py-20">
        <FontAwesomeIcon icon={ICON.inbox} className="text-4xl text-text-muted mb-4" />
        <p className="text-text-muted mb-4">找不到该周报</p>
        <Link to="/weekly" className="text-accent hover:text-accent-hover transition-colors text-sm">
          &larr; 返回周报列表
        </Link>
      </div>
    )
  }

  return (
    <FadeIn>
      {/* Back link */}
      <Link
        to="/weekly"
        className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-accent transition-colors mb-6"
      >
        <FontAwesomeIcon icon={ICON.arrowRight} className="rotate-180 text-xs" />
        返回周报列表
      </Link>

      {/* Two-column layout: content + data sidebar */}
      <div className="flex flex-col lg:flex-row gap-6 pb-12">
        {/* === Main Report === */}
        <article className="flex-1 min-w-0 max-w-3xl prose-custom"
          dangerouslySetInnerHTML={{ __html: html }}
        />

        {/* === Data Sidebar === */}
        {weekStats && (
          <aside className="lg:w-80 flex-shrink-0 space-y-4">
            {/* Weekly Summary Card */}
            <div className="bg-bg-card border border-border-muted rounded-xl p-4">
              <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                <FontAwesomeIcon icon={ICON.dashboard} className="text-accent text-xs" />
                本周数据
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-bg-secondary rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-accent">{weekStats.totalArticles}</div>
                  <div className="text-xs text-text-muted mt-0.5">新增文章</div>
                </div>
                <div className="bg-bg-secondary rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-green">{weekStats.totalCurated}</div>
                  <div className="text-xs text-text-muted mt-0.5">精选篇数</div>
                </div>
                <div className="bg-bg-secondary rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-blue">{weekStats.avgPerDay}</div>
                  <div className="text-xs text-text-muted mt-0.5">日均文章</div>
                </div>
                <div className="bg-bg-secondary rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-amber">{weekStats.healthySources}/{weekStats.totalSources}</div>
                  <div className="text-xs text-text-muted mt-0.5">健康信源</div>
                </div>
              </div>
            </div>

            {/* Daily Trend Line Chart */}
            {weekStats.weekTrends.length >= 3 && (
              <div className="bg-bg-card border border-border-muted rounded-xl p-4">
                <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                  <FontAwesomeIcon icon={ICON.trendUp} className="text-accent text-xs" />
                  每日文章趋势
                </h3>
                <ResponsiveContainer width="100%" height={160}>
                  <LineChart data={weekStats.weekTrends} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--_border-muted, #161825)" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 10, fill: 'var(--_text-muted, #686880)' }}
                      tickFormatter={(d: string) => d.slice(5)}
                    />
                    <YAxis tick={{ fontSize: 10, fill: 'var(--_text-muted, #686880)' }} width={28} />
                    <Tooltip
                      contentStyle={{
                        background: 'var(--_bg-elevated, #12141f)',
                        border: '1px solid var(--_border-default, #1e2033)',
                        borderRadius: '8px',
                        fontSize: '12px',
                        color: 'var(--_text-primary, #e8e9f0)',
                      }}
                    />
                    <Line type="monotone" dataKey="new_articles" stroke="#6C5CE7" strokeWidth={2} dot={false} name="新增" />
                    <Line type="monotone" dataKey="curated_count" stroke="#00b894" strokeWidth={2} dot={false} name="精选" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Category Pie Chart */}
            {weekStats.catEntries.length >= 2 && (
              <div className="bg-bg-card border border-border-muted rounded-xl p-4">
                <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                  <FontAwesomeIcon icon={ICON.chartBar} className="text-accent text-xs" />
                  分类分布
                </h3>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={weekStats.catEntries.map(([name, value]) => ({ name, value }))}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {weekStats.catEntries.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: 'var(--_bg-elevated, #12141f)',
                        border: '1px solid var(--_border-default, #1e2033)',
                        borderRadius: '8px',
                        fontSize: '12px',
                        color: 'var(--_text-primary, #e8e9f0)',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-wrap gap-2 mt-2">
                  {weekStats.catEntries.map(([name], i) => (
                    <span key={name} className="flex items-center gap-1 text-xs text-text-muted">
                      <span className="w-2 h-2 rounded-full" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Top 5 Models */}
            {weekStats.top5.length > 0 && (
              <div className="bg-bg-card border border-border-muted rounded-xl p-4">
                <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                  <FontAwesomeIcon icon={ICON.leaderboard} className="text-accent text-xs" />
                  本周 Top 5 模型
                </h3>
                <div className="space-y-1.5">
                  {weekStats.top5.map((m, i) => (
                    <div key={m.name} className="flex items-center gap-2 text-sm">
                      <span className={`w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold flex-shrink-0
                        ${i < 3 ? 'bg-accent text-white' : 'bg-bg-secondary text-text-muted'}`}>
                        {i + 1}
                      </span>
                      <span className="text-text-primary truncate flex-1">{m.name.split(':').pop()}</span>
                      <span className="text-xs text-accent font-mono">{m.scores?.intelligence}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </aside>
        )}
      </div>

      {/* Bottom back link */}
      <Link
        to="/weekly"
        className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-accent transition-colors mt-4"
      >
        <FontAwesomeIcon icon={ICON.arrowRight} className="rotate-180 text-xs" />
        返回周报列表
      </Link>
    </FadeIn>
  )
}
