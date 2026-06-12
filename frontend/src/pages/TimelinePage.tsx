import { useStats } from '../hooks/useData'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts'

export function TimelinePage() {
  const { data, loading } = useStats()

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    )
  }

  const tr = data?.daily_trends || []

  if (!tr.length) {
    return (
      <div className="text-center py-20">
        <p className="text-4xl mb-4">📅</p>
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
      <div className="text-center py-4">
        <h1 className="text-3xl font-bold text-text-primary">📅 时间线</h1>
        <p className="mt-2 text-text-muted text-sm">每日采集数据总览</p>
      </div>

      <div className="bg-bg-card border border-border-muted rounded-xl p-5">
        <h2 className="text-base font-semibold text-text-primary mb-4">📊 每日柱状图</h2>
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

      <div className="space-y-2">
        {[...tr].reverse().map((d, i) => (
          <div
            key={i}
            className="bg-bg-card border border-border-muted rounded-xl p-4 hover:border-accent/20 transition-all"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-text-primary">📅 {d.date}</span>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-text-muted">📰 总文章 <strong className="text-text-primary">{d.total_articles}</strong></span>
                <span className="text-green">+{d.new_articles} 新增</span>
                <span className="text-amber">⭐ {d.curated_count} 精选</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
