/**
 * DashboardPage - 管理仪表盘页面（密码保护）
 * 
 * 页面功能：Pipeline 数据总览仪表盘，展示：
 *          - KPI 卡片：总文章数、信源健康、高分文章数(80+)、论文数
 *          - 每日采集趋势折线图（总文章 / 新增 / 精选三条线）
 *          - 分类分布饼图（甜甜圈图）
 *          - 信源健康表（状态列带颜色指示灯）
 *          - 最高分文章排行榜（带进度条）
 *          - 关键词趋势标签（7 天变化率 + 方向指示）
 * 
 * 路由路径：/dashboard（受 AdminGate 密码保护）
 * 
 * 数据来源：useStats() → data/stats.json
 * 
 * Props：无
 * 注意：此页面在 App.tsx 中被 <AdminGate> 包裹，需输入仪表盘密码才能访问
 */

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { useStats } from '../hooks/useData'
import { ICON } from '../lib/icons'
import { FadeIn } from '../components/Animations'
import { DashboardSkeleton } from '../components/Skeleton'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart as RePieChart, Pie, Cell, Legend,
} from 'recharts'

/** 分类饼图配色表 */
const COLORS: Record<string, string> = {
  'AI Lab': '#6C5CE7',
  'Paper': '#00b894',
  'Community': '#74b9ff',
  'Blog': '#f0a050',
  '中文媒体': '#fd79a8',
  'Discussion': '#e17055',
}

/** 关键词趋势方向映射：方向名 → 中文标签 + 对应图标 */
const DIRECTION_MAP: Record<string, { label: string; icon: typeof ICON.trendUp }> = {
  surging:  { label: '飙升', icon: ICON.rocket },
  rising:   { label: '上升', icon: ICON.trendUp },
  falling:  { label: '下降', icon: ICON.trendDown },
  declining:{ label: '下滑', icon: ICON.chevronDown },
  stable:   { label: '平稳', icon: ICON.arrowRight },
}

/**
 * DashboardPage - 管理仪表盘页面组件
 * 
 * 数据源：useStats() → data/stats.json（daily_trends, source_health, category_distribution, top_articles, keyword_trends）
 */
export function DashboardPage() {
  const { data, loading, error } = useStats()

  // 加载中 → 专用仪表盘骨架屏
  if (loading) return <DashboardSkeleton />

  // 错误/空数据状态
  if (error || !data) {
    return (
      <div className="text-center py-20">
        <FontAwesomeIcon icon={ICON.inbox} className="text-4xl text-text-muted mb-4" />
        <p className="text-text-muted">暂无仪表盘数据</p>
        {error && <p className="text-xs text-red mt-2">{error}</p>}
      </div>
    )
  }

  /** tr：每日趋势数组 */
  const tr = data.daily_trends || []
  /** sh：信源健康数组 */
  const sh = data.source_health || []
  /** healthy：健康信源数量 */
  const healthy = sh.filter(s => s.status === 'healthy').length
  /** cats：分类分布对象 */
  const cats = data.category_distribution || {}

  /** trendData：Recharts 折线图数据（日期简化到月-日） */
  const trendData = tr.map(r => ({
    date: r.date.slice(5),
    总文章: r.total_articles,
    新增: r.new_articles,
    精选: r.curated_count,
  }))

  /** catData：Recharts 饼图数据 */
  const catData = Object.entries(cats).map(([name, value]) => ({ name, value }))

  return (
    <div className="space-y-6">
      {/* ========== 页面标题 ========== */}
      <FadeIn>
        <div className="text-center py-4">
          <h1 className="text-3xl font-bold text-text-primary flex items-center justify-center gap-2">
            <FontAwesomeIcon icon={ICON.dashboard} className="text-accent" />
            Pipeline 仪表盘
          </h1>
          {data.generated_at && (
            <p className="mt-2 text-sm text-text-muted">
              更新于 {data.generated_at.slice(0, 16)}
            </p>
          )}
        </div>
      </FadeIn>

      {/* ========== KPI 卡片（2x2 或 4列响应式网格） ========== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { value: tr.length ? tr[tr.length - 1].total_articles : 0, label: '总文章数', icon: ICON.news, delay: 0 },
          { value: `${healthy}/${sh.length}`, label: '信源健康', icon: ICON.satelliteDish, delay: 0.05 },
          { value: data.score_distribution?.['80-100'] || 0, label: '高分 (80+)', icon: ICON.star, delay: 0.1 },
          { value: (cats['Paper'] || 0), label: '论文数', icon: ICON.paper, delay: 0.15 },
        ].map((kpi, i) => (
          <FadeIn key={i} delay={kpi.delay}>
            <KpiCard value={kpi.value} label={kpi.label} icon={kpi.icon} />
          </FadeIn>
        ))}
      </div>

      {/* ========== 图表行：趋势折线图 + 分类饼图 ========== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 每日采集趋势折线图 */}
        {tr.length > 1 && (
          <FadeIn delay={0.15}>
            <div className="bg-bg-card border border-border-muted rounded-xl p-5">
              <h2 className="text-base font-semibold text-text-primary mb-4 flex items-center gap-2">
                <FontAwesomeIcon icon={ICON.trendUp} className="text-accent" />
                每日采集趋势
              </h2>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={trendData}>
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
                  {/* 三条线：总文章(紫)、新增(绿)、精选(橙) */}
                  <Line type="monotone" dataKey="总文章" stroke="#6C5CE7" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="新增" stroke="#00b894" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="精选" stroke="#f0a050" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </FadeIn>
        )}

        {/* 分类分布饼图 */}
        {Object.keys(cats).length > 0 && (
          <FadeIn delay={0.2}>
            <div className="bg-bg-card border border-border-muted rounded-xl p-5">
              <h2 className="text-base font-semibold text-text-primary mb-4 flex items-center gap-2">
                <FontAwesomeIcon icon={ICON.tags} className="text-accent" />
                分类分布
              </h2>
              <ResponsiveContainer width="100%" height={260}>
                <RePieChart>
                  <Pie
                    data={catData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}        // 甜甜圈样式
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {catData.map((entry, i) => (
                      <Cell key={i} fill={COLORS[entry.name] || '#686880'} stroke="#0a0b14" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: '#0e0f1a',
                      border: '1px solid #1e2033',
                      borderRadius: '8px',
                      color: '#e8e9f0',
                      fontSize: '13px',
                    }}
                  />
                  <Legend
                    wrapperStyle={{ color: '#9898b0', fontSize: '12px' }}
                    iconType="circle"
                  />
                </RePieChart>
              </ResponsiveContainer>
            </div>
          </FadeIn>
        )}
      </div>

      {/* ========== 信源健康表 ========== */}
      <FadeIn delay={0.25}>
        <div className="bg-bg-card border border-border-muted rounded-xl p-5">
          <h2 className="text-base font-semibold text-text-primary mb-4 flex items-center gap-2">
            <FontAwesomeIcon icon={ICON.satelliteDish} className="text-accent" />
            信源健康
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-muted border-b border-border-muted">
                  <th className="text-left py-2 font-medium">信源</th>
                  <th className="text-left py-2 font-medium">状态</th>
                  <th className="text-left py-2 font-medium">上次成功</th>
                </tr>
              </thead>
              <tbody>
                {sh.map((s, i) => (
                  <tr key={i} className="border-b border-border-muted/50 last:border-0">
                    <td className="py-2.5 text-text-primary">
                      {s.name}
                      <span className="ml-2 text-xs text-text-muted">{s.category}</span>
                    </td>
                    <td className="py-2.5">
                      {/* 状态徽章：绿(healthy) / 黄(degraded) / 红(其他) */}
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                        s.status === 'healthy' ? 'bg-green/10 text-green' :
                        s.status === 'degraded' ? 'bg-amber/10 text-amber' :
                        'bg-red/10 text-red'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          s.status === 'healthy' ? 'bg-green' :
                          s.status === 'degraded' ? 'bg-amber' : 'bg-red'
                        }`} />
                        {s.status}
                      </span>
                    </td>
                    <td className="py-2.5 text-xs text-text-muted">
                      {s.last_success ? s.last_success.slice(0, 16) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </FadeIn>

      {/* ========== 最高分文章排行榜 ========== */}
      <FadeIn delay={0.3}>
        <div className="bg-bg-card border border-border-muted rounded-xl p-5">
          <h2 className="text-base font-semibold text-text-primary mb-4 flex items-center gap-2">
            <FontAwesomeIcon icon={ICON.leaderboard} className="text-accent" />
            最高分文章
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-muted border-b border-border-muted">
                  <th className="text-left py-2 font-medium">文章</th>
                  <th className="text-left py-2 font-medium">分数</th>
                  <th className="text-left py-2 font-medium">来源</th>
                </tr>
              </thead>
              <tbody>
                {(data.top_articles || []).map((a, i) => (
                  <tr key={i} className="border-b border-border-muted/50 last:border-0">
                    <td className="py-2.5 text-text-primary max-w-[220px] truncate">{a.title}</td>
                    <td className="py-2.5">
                      {/* 分数进度条（0-100） */}
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-bg-secondary rounded-full max-w-[80px]">
                          <div
                            className="h-full bg-accent rounded-full transition-all"
                            style={{ width: `${Math.min(a.score, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-text-muted">{a.score}</span>
                      </div>
                    </td>
                    <td className="py-2.5 text-xs text-text-muted">{a.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </FadeIn>

      {/* ========== 关键词趋势（7 天，最多 18 个） ========== */}
      {data.keyword_trends?.keywords && data.keyword_trends.keywords.length > 0 && (
        <FadeIn delay={0.35}>
          <div className="bg-bg-card border border-border-muted rounded-xl p-5">
            <h2 className="text-base font-semibold text-text-primary mb-4 flex items-center gap-2">
              <FontAwesomeIcon icon={ICON.fire} className="text-amber" />
              关键词趋势 (7 天)
            </h2>
            <div className="flex flex-wrap gap-2">
              {data.keyword_trends.keywords.slice(0, 18).map((t, i) => {
                /** opacity：根据变化百分比计算透明度（越大越明显） */
                const opacity = Math.min(1, 0.3 + Math.abs(t.change_pct) / 100)
                const dir = DIRECTION_MAP[t.direction] || DIRECTION_MAP.stable
                return (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-bg-secondary border border-border-muted"
                    style={{ opacity }}
                  >
                    <FontAwesomeIcon icon={dir.icon} className="text-text-muted" />
                    <span className="text-text-muted">{dir.label}</span>
                    <strong className="text-text-primary">{t.keyword}</strong>
                    {/* 变化率：正绿色/负红色 */}
                    <span style={{ color: t.change_pct > 0 ? '#00b894' : '#e17055' }}>
                      {t.change_pct > 0 ? '+' : ''}{t.change_pct}%
                    </span>
                  </span>
                )
              })}
            </div>
          </div>
        </FadeIn>
      )}
    </div>
  )
}

/**
 * KpiCard - KPI 统计卡片组件
 * 
 * Props：
 *   - value：数值（string | number）
 *   - label：标签文本
 *   - icon：图标
 */
function KpiCard({ value, label, icon }: { value: string | number; label: string; icon: typeof ICON.star }) {
  return (
    <div className="bg-bg-card border border-border-muted rounded-xl p-4 hover:border-accent/20 hover:shadow-[0_0_20px_-8px_rgba(108,92,231,0.1)] transition-all duration-300">
      <div className="flex items-center gap-2 text-text-muted mb-1">
        <FontAwesomeIcon icon={icon} className="text-xs" />
        <span className="text-xs">{label}</span>
      </div>
      <div className="text-2xl font-bold text-text-primary">{value}</div>
    </div>
  )
}
