/**
 * WeeklyPage - 周报列表页
 * 
 * 页面功能：展示所有 AI 周报（每周大事记）列表，包含近 30 天数据趋势折线图
 *          每个周报条目以卡片形式展示，点击跳转到周报详情页
 * 
 * 路由路径：/weekly
 * 
 * 数据来源：
 *   - API 模式（VITE_API_MODE=true）：${API_BASE}/weekly
 *   - 静态模式：data/weekly/index.json
 *   - 统计趋势：data/stats.json（daily_trends 用于折线图）
 * 
 * 使用 Context：LocaleContext（中英双语）
 */

import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'
import { ICON } from '../lib/icons'
import { FadeIn, ScrollReveal } from '../components/Animations'
import { CardSkeleton } from '../components/Skeleton'
import { useLocale } from '../lib/LocaleContext'

/** 周报数据结构 */
interface WeeklyReport {
  date: string; title: string; title_en?: string; summary: string; summary_en?: string; url: string; url_en?: string
}

/** API 模式开关及 API 基础地址 */
const API_MODE = import.meta.env.VITE_API_MODE === 'true'
const API_BASE = import.meta.env.VITE_API_BASE || 'https://api.hjhai.xyz'

/** i18n 中英双语文案 */
const T = {
  weeklyReport:  { zh: '每周 AI 大事记',   en: 'Weekly AI Briefing' },
  subhead:       { zh: '深度行业分析简报',   en: 'In-depth industry analysis' },
  trend30d:      { zh: '近 30 天趋势',      en: '30-Day Trend' },
  daysNew:       { zh: '7天新增',           en: '7d new' },
  daysCurated:   { zh: '精选',              en: 'curated' },
  articles:      { zh: '篇',                en: '' },
  newArticles:   { zh: '新增文章',           en: 'New Articles' },
  curatedLine:   { zh: '精选',              en: 'Curated' },
  noReports:     { zh: '暂无周报',           en: 'No reports yet' },
}
function t(o: {zh:string;en:string}, l:'zh'|'en') { return o[l] }

/**
 * WeeklyPage - 周报列表页组件
 */
export function WeeklyPage() {
  /** reports：周报列表数据 */
  const [reports, setReports] = useState<WeeklyReport[]>([])
  /** loading：数据加载状态 */
  const [loading, setLoading] = useState(true)
  /** stats：统计数据（含 daily_trends 用于趋势图） */
  const [stats, setStats] = useState<{ daily_trends: { date: string; new_articles: number; curated_count: number }[] } | null>(null)
  const { locale } = useLocale()

  // 组件挂载时获取周报列表 + 统计数据
  useEffect(() => {
    const fetchData = async () => {
      let indexData: { reports: WeeklyReport[] }
      // 根据 API_MODE 决定数据来源：API 或静态 JSON
      if (API_MODE) {
        // API 模式：从后端 ${API_BASE}/weekly 获取周报索引
        const res = await fetch(`${API_BASE}/weekly`)
        indexData = await res.json()
      } else {
        // 静态模式：从 data/weekly/index.json 获取周报索引
        const res = await fetch(`${import.meta.env.BASE_URL}data/weekly/index.json`)
        indexData = await res.json()
      }
      // 获取统计数据（daily_trends 用于折线图）
      const statsRes = await fetch(`${import.meta.env.BASE_URL}data/stats.json`)
      const statsData = statsRes.ok ? await statsRes.json() : null
      setReports(indexData.reports || [])
      setStats(statsData)
    }
    fetchData()
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  /** trendData：近 30 天每日新增文章 + 精选数量（用于折线图），按日期升序 */
  const trendData = useMemo(() => {
    if (!stats?.daily_trends) return []
    return stats.daily_trends.slice(-30).sort((a, b) => a.date.localeCompare(b.date))
  }, [stats])

  /** overviewStats：近 7 天的汇总统计 */
  const overviewStats = useMemo(() => {
    if (!trendData.length) return null
    const last7 = trendData.slice(-7)
    const totalArticles = last7.reduce((s, d) => s + (d.new_articles || 0), 0)
    const totalCurated = last7.reduce((s, d) => s + (d.curated_count || 0), 0)
    return { totalArticles, totalCurated, days: last7.length }
  }, [trendData])

  // 加载中 → 骨架屏
  if (loading) {
    return <div className="space-y-4"><CardSkeleton /><CardSkeleton /><CardSkeleton /></div>
  }

  return (
    <div className="space-y-6">
      {/* ========== 页面标题 ========== */}
      <FadeIn>
        <div className="text-center py-4">
          <h1 className="text-3xl font-bold text-text-primary flex items-center justify-center gap-2">
            <FontAwesomeIcon icon={ICON.weekly} className="text-accent" />
            {t(T.weeklyReport, locale)}
          </h1>
          <p className="mt-2 text-text-muted text-sm">{t(T.subhead, locale)}</p>
        </div>
      </FadeIn>

      {/* ========== 近 30 天趋势折线图 ========== */}
      {trendData.length >= 7 && overviewStats && (
        <FadeIn delay={0.05}>
          <div className="bg-bg-card border border-border-muted rounded-xl p-5">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <FontAwesomeIcon icon={ICON.trendUp} className="text-accent" />
                {t(T.trend30d, locale)}
              </h2>
              <div className="flex gap-4 text-xs">
                <span className="text-text-muted">{t(T.daysNew, locale)} <strong className="text-accent">{overviewStats.totalArticles}</strong> {t(T.articles, locale)}</span>
                <span className="text-text-muted">{t(T.daysCurated, locale)} <strong className="text-green">{overviewStats.totalCurated}</strong> {t(T.articles, locale)}</span>
              </div>
            </div>
            {/* Recharts 折线图：X=日期, Y=数量，两条线：新增文章（紫色）、精选（绿色） */}
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={trendData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--_border-muted, #161825)" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--_text-muted, #686880)' }} tickFormatter={(d: string) => d.slice(5)} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 10, fill: 'var(--_text-muted, #686880)' }} width={32} />
                <Tooltip contentStyle={{ background: 'var(--_bg-elevated, #12141f)', border: '1px solid var(--_border-default, #1e2033)', borderRadius: '8px', fontSize: '12px', color: 'var(--_text-primary, #e8e9f0)' }} />
                <Line type="monotone" dataKey="new_articles" stroke="#6C5CE7" strokeWidth={2} dot={false} name={t(T.newArticles, locale)} />
                <Line type="monotone" dataKey="curated_count" stroke="#00b894" strokeWidth={2} dot={false} name={t(T.curatedLine, locale)} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </FadeIn>
      )}

      {/* ========== 周报列表 ========== */}
      {reports.length === 0 ? (
        /* 空状态 */
        <div className="text-center py-20">
          <FontAwesomeIcon icon={ICON.inbox} className="text-4xl text-text-muted mb-4" />
          <p className="text-text-muted">{t(T.noReports, locale)}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((report, i) => {
            const card = (
              <Link key={report.date} to={`/weekly/${report.date}`} className="block bg-bg-card border border-border-muted rounded-xl p-5 hover:border-accent/20 hover:bg-bg-elevated hover:shadow-[0_0_20px_-8px_rgba(108,92,231,0.1)] transition-all duration-300 group">
                <div className="flex items-start gap-4">
                  {/* 左侧图标 */}
                  <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-accent-muted flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                    <FontAwesomeIcon icon={ICON.weekly} className="text-accent text-lg" />
                  </div>
                  {/* 周报标题 + 摘要 */}
                  <div className="flex-1 min-w-0">
                    <h2 className="text-base font-semibold text-text-primary group-hover:text-accent transition-colors">
                      {locale === 'en' && report.title_en ? report.title_en : report.title} ({report.date})
                    </h2>
                    <p className="mt-1 text-sm text-text-secondary">{locale === 'en' && report.summary_en ? report.summary_en : report.summary}</p>
                  </div>
                  {/* 右侧箭头 */}
                  <div className="flex-shrink-0 self-center">
                    <FontAwesomeIcon icon={ICON.arrowRight} className="text-text-muted group-hover:text-accent group-hover:translate-x-1 transition-all" />
                  </div>
                </div>
              </Link>
            )
            // 前 12 条添加滚动渐入动画，其余直接渲染
            return i < 12 ? (
              <ScrollReveal key={report.date} index={i}>{card}</ScrollReveal>
            ) : card
          })}
        </div>
      )}
    </div>
  )
}
