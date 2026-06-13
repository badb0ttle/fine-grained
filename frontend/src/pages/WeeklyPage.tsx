import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'
import { ICON } from '../lib/icons'
import { FadeIn, ScrollReveal } from '../components/Animations'
import { CardSkeleton } from '../components/Skeleton'

interface WeeklyReport {
  date: string
  title: string
  summary: string
  url: string
}

export function WeeklyPage() {
  const [reports, setReports] = useState<WeeklyReport[]>([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<{ daily_trends: { date: string; new_articles: number; curated_count: number }[] } | null>(null)

  useEffect(() => {
    Promise.all([
      fetch(`${import.meta.env.BASE_URL}data/weekly/index.json`).then(r => r.json()),
      fetch(`${import.meta.env.BASE_URL}data/stats.json`).then(r => r.ok ? r.json() : null),
    ])
      .then(([indexData, statsData]) => {
        setReports(indexData.reports || [])
        setStats(statsData)
      })
      .catch(() => {
        setReports([{
          date: '2026-06-02',
          title: '本周 AI 大事记',
          summary: 'MiniMax M3 · Agent 规模化 · 基准测试危机 · 记忆机制',
          url: '',
        }])
      })
      .finally(() => setLoading(false))
  }, [])

  // Compute 30-day trend for overview chart
  const trendData = useMemo(() => {
    if (!stats?.daily_trends) return []
    return stats.daily_trends.slice(-30).sort((a, b) => a.date.localeCompare(b.date))
  }, [stats])

  // Compute aggregate stats
  const overviewStats = useMemo(() => {
    if (!trendData.length) return null
    const last7 = trendData.slice(-7)
    const totalArticles = last7.reduce((s, d) => s + (d.new_articles || 0), 0)
    const totalCurated = last7.reduce((s, d) => s + (d.curated_count || 0), 0)
    return { totalArticles, totalCurated, days: last7.length }
  }, [trendData])

  if (loading) {
    return (
      <div className="space-y-4">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <FadeIn>
        <div className="text-center py-4">
          <h1 className="text-3xl font-bold text-text-primary flex items-center justify-center gap-2">
            <FontAwesomeIcon icon={ICON.weekly} className="text-accent" />
            每周 AI 大事记
          </h1>
          <p className="mt-2 text-text-muted text-sm">深度行业分析简报</p>
        </div>
      </FadeIn>

      {/* 30-Day Trend Overview */}
      {trendData.length >= 7 && overviewStats && (
        <FadeIn delay={0.05}>
          <div className="bg-bg-card border border-border-muted rounded-xl p-5">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <FontAwesomeIcon icon={ICON.trendUp} className="text-accent" />
                近 30 天趋势
              </h2>
              <div className="flex gap-4 text-xs">
                <span className="text-text-muted">7天新增 <strong className="text-accent">{overviewStats.totalArticles}</strong> 篇</span>
                <span className="text-text-muted">精选 <strong className="text-green">{overviewStats.totalCurated}</strong> 篇</span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={trendData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--_border-muted, #161825)" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: 'var(--_text-muted, #686880)' }}
                  tickFormatter={(d: string) => d.slice(5)}
                  interval="preserveStartEnd"
                />
                <YAxis tick={{ fontSize: 10, fill: 'var(--_text-muted, #686880)' }} width={32} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--_bg-elevated, #12141f)',
                    border: '1px solid var(--_border-default, #1e2033)',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: 'var(--_text-primary, #e8e9f0)',
                  }}
                />
                <Line type="monotone" dataKey="new_articles" stroke="#6C5CE7" strokeWidth={2} dot={false} name="新增文章" />
                <Line type="monotone" dataKey="curated_count" stroke="#00b894" strokeWidth={2} dot={false} name="精选" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </FadeIn>
      )}

      {/* Report list */}
      {reports.length === 0 ? (
        <div className="text-center py-20">
          <FontAwesomeIcon icon={ICON.inbox} className="text-4xl text-text-muted mb-4" />
          <p className="text-text-muted">暂无周报</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((report, i) => (
            <ScrollReveal key={report.date} index={i}>
              <Link
                to={`/weekly/${report.date}`}
                className="block bg-bg-card border border-border-muted rounded-xl p-5 hover:border-accent/20 hover:bg-bg-elevated hover:shadow-[0_0_20px_-8px_rgba(108,92,231,0.1)] transition-all duration-300 group"
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-accent-muted flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                    <FontAwesomeIcon icon={ICON.weekly} className="text-accent text-lg" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h2 className="text-base font-semibold text-text-primary group-hover:text-accent transition-colors">
                      {report.title} ({report.date})
                    </h2>
                    <p className="mt-1 text-sm text-text-secondary">{report.summary}</p>
                  </div>
                  <div className="flex-shrink-0 self-center">
                    <FontAwesomeIcon icon={ICON.arrowRight} className="text-text-muted group-hover:text-accent group-hover:translate-x-1 transition-all" />
                  </div>
                </div>
              </Link>
            </ScrollReveal>
          ))}
        </div>
      )}
    </div>
  )
}
