import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { useStats } from '../hooks/useData'
import { ICON } from '../lib/icons'
import { FadeIn, ScrollReveal } from '../components/Animations'
import { DashboardSkeleton } from '../components/Skeleton'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts'

export function TimelinePage() {
  const { data, loading } = useStats()

  if (loading) return <DashboardSkeleton />

  const tr = data?.daily_trends || []

  if (!tr.length) {
    return (
      <div className="text-center py-20">
        <FontAwesomeIcon icon={ICON.timeline} className="text-4xl text-text-muted mb-4" />
        <p className="text-text-muted">暂无时间线数据</p>
      </div>
    )
  }

  const barData = tr.map(r => ({
    date: r.date.slice(5),
    总文章: r.total_articles,
    新增: r.new_articles,
  }))

  return (
    <div className="space-y-6">
      <FadeIn>
        <div className="text-center py-4">
          <h1 className="text-3xl font-bold text-text-primary flex items-center justify-center gap-2">
            <FontAwesomeIcon icon={ICON.timeline} className="text-accent" />
            时间线
          </h1>
          <p className="mt-2 text-text-muted text-sm">每日采集数据总览</p>
        </div>
      </FadeIn>

      <FadeIn delay={0.1}>
        <div className="bg-bg-card border border-border-muted rounded-xl p-5">
          <h2 className="text-base font-semibold text-text-primary mb-4 flex items-center gap-2">
            <FontAwesomeIcon icon={ICON.chartBar} className="text-accent" />
            每日柱状图
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barData}>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fill: '#686880', fontSize: 12 }} />
              <YAxis tick={{ fill: '#686880', fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: '#0e0f1a',
                  border: '1px solid #1e2033',
                  borderRadius: '8px',
                  color: '#e8e9f0',
                  fontSize: '13px',
                }}
              />
              <Bar dataKey="总文章" fill="#6C5CE7" radius={[4, 4, 0, 0]} />
              <Bar dataKey="新增" fill="#00b894" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </FadeIn>

      <div className="space-y-2">
        {[...tr].reverse().map((d, i) => (
          <ScrollReveal key={i} index={i}>
            <div
              className="bg-bg-card border border-border-muted rounded-xl p-4 hover:border-accent/20 hover:shadow-[0_0_20px_-8px_rgba(108,92,231,0.1)] transition-all duration-300"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-text-primary flex items-center gap-1.5">
                  <FontAwesomeIcon icon={ICON.timeline} className="text-text-muted" />
                  {d.date}
                </span>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-text-muted">
                    <FontAwesomeIcon icon={ICON.news} className="mr-1" />
                    总文章 <strong className="text-text-primary">{d.total_articles}</strong>
                  </span>
                  <span className="text-green">+{d.new_articles} 新增</span>
                  <span className="text-amber">
                    <FontAwesomeIcon icon={ICON.star} className="mr-1" />
                    {d.curated_count} 精选
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
