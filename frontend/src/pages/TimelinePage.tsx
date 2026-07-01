/**
 * TimelinePage - 时间线页面
 * 
 * 页面功能：展示每日采集数据总览
 *          - 柱状图：每日总文章数 + 新增文章数
 *          - 列表：按日期倒序展示每日统计详情（总文章、新增、精选数）
 * 
 * 路由路径：/timeline
 * 
 * 数据来源：useStats() hook → data/stats.json（daily_trends 字段）
 * 
 * 使用 Context：LocaleContext（中英双语）
 */

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { useStats } from '../hooks/useData'
import { ICON } from '../lib/icons'
import { FadeIn, ScrollReveal } from '../components/Animations'
import { DashboardSkeleton } from '../components/Skeleton'
import { useLocale } from '../lib/LocaleContext'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts'

/** i18n 文案 */
const T = {
  timeline:     { zh: '时间线', en: 'Timeline' },
  overview:     { zh: '每日采集数据总览', en: 'Daily Scan Overview' },
  barChart:     { zh: '每日柱状图', en: 'Daily Bar Chart' },
  totalArticles:{ zh: '总文章', en: 'Total' },
  newArticles:  { zh: '新增', en: 'New' },
  curated:      { zh: '精选', en: 'Curated' },
  noData:       { zh: '暂无时间线数据', en: 'No timeline data yet' },
}
function t(o: {zh:string;en:string}, l:'zh'|'en') { return o[l] }

/**
 * TimelinePage - 时间线页面组件
 * 
 * 数据：useStats() → data/stats.json（daily_trends 每日趋势数组）
 */
export function TimelinePage() {
  const { data, loading } = useStats()
  const { locale } = useLocale()

  // 加载中 → 骨架屏
  if (loading) return <DashboardSkeleton />

  /** tr：daily_trends 数组简写（每日扫描统计） */
  const tr = data?.daily_trends || []

  // 空数据状态
  if (!tr.length) {
    return (
      <div className="text-center py-20">
        <FontAwesomeIcon icon={ICON.timeline} className="text-4xl text-text-muted mb-4" />
        <p className="text-text-muted">{t(T.noData, locale)}</p>
      </div>
    )
  }

  /** barData：Recharts 柱状图数据（仅显示月-日部分，totalKey/newKey 由 locale 决定） */
  const barData = tr.map(r => ({
    date: r.date.slice(5),
    [t(T.totalArticles, locale)]: r.total_articles,
    [t(T.newArticles, locale)]: r.new_articles,
  }))

  /** totalKey：柱状图"总文章"柱的 dataKey（中/英文案） */
  const totalKey = t(T.totalArticles, locale)
  /** newKey：柱状图"新增"柱的 dataKey（中/英文案） */
  const newKey = t(T.newArticles, locale)

  return (
    <div className="space-y-6">
      {/* ========== 页面标题 ========== */}
      <FadeIn>
        <div className="text-center py-4">
          <h1 className="text-3xl font-bold text-text-primary flex items-center justify-center gap-2">
            <FontAwesomeIcon icon={ICON.timeline} className="text-accent" />
            {t(T.timeline, locale)}
          </h1>
          <p className="mt-2 text-text-muted text-sm">{t(T.overview, locale)}</p>
        </div>
      </FadeIn>

      {/* ========== 柱状图：总文章 vs 新增文章 ========== */}
      <FadeIn delay={0.1}>
        <div className="bg-bg-card border border-border-muted rounded-xl p-5">
          <h2 className="text-base font-semibold text-text-primary mb-4 flex items-center gap-2">
            <FontAwesomeIcon icon={ICON.chartBar} className="text-accent" />
            {t(T.barChart, locale)}
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barData}>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fill: '#686880', fontSize: 12 }} />
              <YAxis tick={{ fill: '#686880', fontSize: 12 }} />
              <Tooltip contentStyle={{ background: '#0e0f1a', border: '1px solid #1e2033', borderRadius: '8px', color: '#e8e9f0', fontSize: '13px' }} />
              <Bar dataKey={totalKey} fill="#6C5CE7" radius={[4, 4, 0, 0]} />
              <Bar dataKey={newKey} fill="#00b894" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </FadeIn>

      {/* ========== 每日统计列表（倒序） ========== */}
      <div className="space-y-2">
        {[...tr].reverse().map((d, i) => (
          <ScrollReveal key={i} index={i}>
            <div className="bg-bg-card border border-border-muted rounded-xl p-4 hover:border-accent/20 hover:shadow-[0_0_20px_-8px_rgba(108,92,231,0.1)] transition-all duration-300">
              <div className="flex items-center justify-between">
                <span className="font-medium text-text-primary flex items-center gap-1.5">
                  <FontAwesomeIcon icon={ICON.timeline} className="text-text-muted" />
                  {d.date}
                </span>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-text-muted">
                    <FontAwesomeIcon icon={ICON.news} className="mr-1" />
                    {t(T.totalArticles, locale)} <strong className="text-text-primary">{d.total_articles}</strong>
                  </span>
                  <span className="text-green">+{d.new_articles} {t(T.newArticles, locale)}</span>
                  <span className="text-amber">
                    <FontAwesomeIcon icon={ICON.star} className="mr-1" />
                    {d.curated_count} {t(T.curated, locale)}
                  </span>
                </div>
              </div>
            </div>
          </ScrollReveal>
        ))}
      </div>
    </div>
  )
}
