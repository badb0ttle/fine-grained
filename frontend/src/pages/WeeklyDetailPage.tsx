import { useEffect, useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { ICON } from '../lib/icons'
import { FadeIn } from '../components/Animations'
import { CardSkeleton } from '../components/Skeleton'
import { useLocale } from '../lib/LocaleContext'

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

const T = {
  notFound:       { zh: '找不到该周报',      en: 'Report not found' },
  backToList:     { zh: '返回周报列表',       en: 'Back to reports' },
  thisWeek:       { zh: '本周数据',           en: 'This Week' },
  newArticles:    { zh: '新增文章',           en: 'New Articles' },
  curatedCount:   { zh: '精选篇数',           en: 'Curated' },
  avgPerDay:      { zh: '日均文章',           en: 'Avg/Day' },
  healthySources: { zh: '健康信源',           en: 'Healthy Sources' },
  dailyTrend:     { zh: '每日文章趋势',        en: 'Daily Trend' },
  categories:     { zh: '分类分布',           en: 'Categories' },
  top5Models:     { zh: '本周 Top 5 模型',    en: 'Top 5 Models This Week' },
  newLabel:       { zh: '新增',               en: 'New' },
  curatedLabel:   { zh: '精选',               en: 'Curated' },
}
function t(o: {zh:string;en:string}, l:'zh'|'en') { return o[l] }

export function WeeklyDetailPage() {
  const { date } = useParams<{ date: string }>()
  const [html, setHtml] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [stats, setStats] = useState<StatsData | null>(null)
  const [leaderboard, setLeaderboard] = useState<LeaderboardData | null>(null)
  const { locale } = useLocale()

  useEffect(() => {
    if (!date) return
    setLoading(true)
    setError(false)

    const loadWeekly = async () => {
      // Try English first if locale is 'en', fall back to Chinese
      let htmlRes: Response
      if (locale === 'en') {
        htmlRes = await fetch(`${import.meta.env.BASE_URL}data/weekly/${date}_en.html`)
        if (!htmlRes.ok) htmlRes = await fetch(`${import.meta.env.BASE_URL}data/weekly/${date}.html`)
      } else {
        htmlRes = await fetch(`${import.meta.env.BASE_URL}data/weekly/${date}.html`)
      }

      const [statsData, lbData] = await Promise.all([
        fetch(`${import.meta.env.BASE_URL}data/stats.json`).then(r => r.ok ? r.json() : null),
        fetch(`${import.meta.env.BASE_URL}data/model_leaderboard.json`).then(r => r.ok ? r.json() : null),
      ])

      if (!htmlRes.ok) throw new Error('Not found')
      setStats(statsData)
      setLeaderboard(lbData)

      const raw = await htmlRes.text()

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
    }

    loadWeekly()
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [date, locale])

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

    const catEntries = Object.entries(stats.category_distribution || {})
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)

    const healthySources = (stats.source_health || []).filter(s => s.status === 'healthy').length
    const totalSources = (stats.source_health || []).length

    const top5 = (leaderboard?.models || [])
      .filter(m => m.scores?.intelligence != null)
      .sort((a, b) => (b.scores!.intelligence ?? 0) - (a.scores!.intelligence ?? 0))
      .slice(0, 5)

    return { weekTrends, totalArticles, totalCurated, avgPerDay, catEntries, healthySources, totalSources, top5 }
  }, [stats, leaderboard, date])

  if (loading) return <div className="space-y-4 pt-8"><CardSkeleton /></div>

  if (error || !html) {
    return (
      <div className="text-center py-20">
        <FontAwesomeIcon icon={ICON.inbox} className="text-4xl text-text-muted mb-4" />
        <p className="text-text-muted mb-4">{t(T.notFound, locale)}</p>
        <Link to="/weekly" className="text-accent hover:text-accent-hover transition-colors text-sm">
          &larr; {t(T.backToList, locale)}
        </Link>
      </div>
    )
  }

  return (
    <FadeIn>
      <Link to="/weekly" className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-accent transition-colors mb-6">
        <FontAwesomeIcon icon={ICON.arrowRight} className="rotate-180 text-xs" />
        {t(T.backToList, locale)}
      </Link>

      <div className="flex flex-col lg:flex-row gap-6 pb-12">
        <article className="flex-1 min-w-0 max-w-3xl prose-custom"
          dangerouslySetInnerHTML={{ __html: html }}
        />

        {weekStats && (
          <aside className="lg:w-80 flex-shrink-0 space-y-4">
            <div className="bg-bg-card border border-border-muted rounded-xl p-4">
              <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                <FontAwesomeIcon icon={ICON.dashboard} className="text-accent text-xs" />
                {t(T.thisWeek, locale)}
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-bg-secondary rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-accent">{weekStats.totalArticles}</div>
                  <div className="text-xs text-text-muted mt-0.5">{t(T.newArticles, locale)}</div>
                </div>
                <div className="bg-bg-secondary rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-green">{weekStats.totalCurated}</div>
                  <div className="text-xs text-text-muted mt-0.5">{t(T.curatedCount, locale)}</div>
                </div>
                <div className="bg-bg-secondary rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-blue">{weekStats.avgPerDay}</div>
                  <div className="text-xs text-text-muted mt-0.5">{t(T.avgPerDay, locale)}</div>
                </div>
                <div className="bg-bg-secondary rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-amber">{weekStats.healthySources}/{weekStats.totalSources}</div>
                  <div className="text-xs text-text-muted mt-0.5">{t(T.healthySources, locale)}</div>
                </div>
              </div>
            </div>

            {weekStats.weekTrends.length >= 3 && (
              <div className="bg-bg-card border border-border-muted rounded-xl p-4">
                <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                  <FontAwesomeIcon icon={ICON.trendUp} className="text-accent text-xs" />
                  {t(T.dailyTrend, locale)}
                </h3>
                <ResponsiveContainer width="100%" height={160}>
                  <LineChart data={weekStats.weekTrends} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--_border-muted, #161825)" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--_text-muted, #686880)' }} tickFormatter={(d: string) => d.slice(5)} />
                    <YAxis tick={{ fontSize: 10, fill: 'var(--_text-muted, #686880)' }} width={28} />
                    <Tooltip contentStyle={{ background: 'var(--_bg-elevated, #12141f)', border: '1px solid var(--_border-default, #1e2033)', borderRadius: '8px', fontSize: '12px', color: 'var(--_text-primary, #e8e9f0)' }} />
                    <Line type="monotone" dataKey="new_articles" stroke="#6C5CE7" strokeWidth={2} dot={false} name={t(T.newLabel, locale)} />
                    <Line type="monotone" dataKey="curated_count" stroke="#00b894" strokeWidth={2} dot={false} name={t(T.curatedLabel, locale)} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {weekStats.catEntries.length >= 2 && (
              <div className="bg-bg-card border border-border-muted rounded-xl p-4">
                <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                  <FontAwesomeIcon icon={ICON.chartBar} className="text-accent text-xs" />
                  {t(T.categories, locale)}
                </h3>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={weekStats.catEntries.map(([name, value]) => ({ name, value }))} cx="50%" cy="50%" innerRadius={45} outerRadius={80} paddingAngle={2} dataKey="value">
                      {weekStats.catEntries.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: 'var(--_bg-elevated, #12141f)', border: '1px solid var(--_border-default, #1e2033)', borderRadius: '8px', fontSize: '12px', color: 'var(--_text-primary, #e8e9f0)' }} />
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

            {weekStats.top5.length > 0 && (
              <div className="bg-bg-card border border-border-muted rounded-xl p-4">
                <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                  <FontAwesomeIcon icon={ICON.leaderboard} className="text-accent text-xs" />
                  {t(T.top5Models, locale)}
                </h3>
                <div className="space-y-1.5">
                  {weekStats.top5.map((m, i) => (
                    <div key={m.name} className="flex items-center gap-2 text-sm">
                      <span className={`w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${i < 3 ? 'bg-accent text-white' : 'bg-bg-secondary text-text-muted'}`}>
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

      <Link to="/weekly" className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-accent transition-colors mt-4">
        <FontAwesomeIcon icon={ICON.arrowRight} className="rotate-180 text-xs" />
        {t(T.backToList, locale)}
      </Link>
    </FadeIn>
  )
}
