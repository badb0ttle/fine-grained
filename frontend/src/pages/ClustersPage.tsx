/**
 * ClustersPage - 话题聚类分析页面
 * 
 * 页面功能：基于 TF-IDF 语义相似度的文章聚类可视化
 *          - 顶部：Canvas 散点图（支持按聚类筛选、悬停查看详情、点击跳转原文）
 *          - 底部：聚类卡片网格（展示每个聚类的关键词和文章列表）
 * 
 * 路由路径：/clusters
 * 
 * 数据来源：useClusters() hook → data/clusters.json（含聚类中心、散点坐标、关键词）
 * 
 * 使用 Context：LocaleContext（中英双语）
 */

import { useEffect, useRef, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { ICON } from '../lib/icons'
import { FadeIn } from '../components/Animations'
import { CardSkeleton } from '../components/Skeleton'
import { useLocale } from '../lib/LocaleContext'
import { useClusters } from '../hooks/useData'
import type { ClusterData } from '../types'

/** Canvas 散点图布局常量 */
const PADDING = 50          // 画布内边距
const DOT_RADIUS = 4        // 散点半径
const HOVER_RADIUS = 8      // 悬停高亮半径

/**
 * ClusterScatter - Canvas 散点图组件
 * 
 * 功能：用 Canvas 绘制 TF-IDF 文章散点图，支持：
 *       - 按聚类筛选（顶部按钮）
 *       - 鼠标悬停高亮 + tooltip 显示详情
 *       - 点击跳转原文
 * 实现：使用离屏 Canvas 缓存背景渲染，悬停时仅重绘高亮圆圈
 * 
 * Props：
 *   - data：ClusterData（聚类数据）
 *   - locale：当前语言
 */
function ClusterScatter({ data, locale }: { data: ClusterData; locale: 'zh' | 'en' }) {
  /** canvasRef：主 Canvas DOM 引用 */
  const canvasRef = useRef<HTMLCanvasElement>(null)
  /** tooltipRef：悬停提示框 DOM 引用 */
  const tooltipRef = useRef<HTMLDivElement>(null)
  /** offscreenRef：离屏 Canvas（缓存背景渲染） */
  const offscreenRef = useRef<HTMLCanvasElement | null>(null)
  /** activeCluster：当前选中的聚类 ID（-1 = 全部） */
  const [activeCluster, setActiveCluster] = useState<number>(-1)
  /** info：底部统计信息文本 */
  const [info, setInfo] = useState('')
  /** coordsRef：当前显示的散点屏幕坐标数组 */
  const coordsRef = useRef<{ cx: number; cy: number; title: string; source: string; published: string; score: number; link: string; cluster: number }[]>([])
  /** clusterMap：聚类 ID → 颜色映射 */
  const clusterMap = useRef<Record<number, string>>({})

  // 数据变化时更新聚类颜色映射
  useEffect(() => {
    const map: Record<number, string> = {}
    for (const c of data.clusters) map[c.id] = c.color
    clusterMap.current = map
  }, [data])

  /**
   * renderBackground - 渲染背景图层（网格 + 所有散点）到离屏 Canvas
   * 仅在数据或筛选条件变化时重新计算
   */
  const renderBackground = () => {
    const canvas = canvasRef.current
    if (!canvas) return

    const dpr = window.devicePixelRatio || 1
    const parent = canvas.parentElement!
    const W = parent.clientWidth
    const H = Math.min(W * 0.7, 550)

    // 设置主 Canvas 尺寸（适配 DPR 高清屏）
    canvas.width = W * dpr
    canvas.height = H * dpr
    canvas.style.width = W + 'px'
    canvas.style.height = H + 'px'

    // 创建或复用来离屏 Canvas
    if (!offscreenRef.current) {
      offscreenRef.current = document.createElement('canvas')
    }
    const off = offscreenRef.current
    off.width = W * dpr
    off.height = H * dpr

    const octx = off.getContext('2d')!
    octx.scale(dpr, dpr)

    // 背景色填充
    octx.fillStyle = '#0a0b14'
    octx.fillRect(0, 0, W, H)

    // 筛选散点（若选中特定聚类则过滤）
    let points = data.points
    if (activeCluster >= 0) {
      points = points.filter(p => p.cluster === activeCluster)
    }

    // 计算散点在画布上的坐标（x,y 是从 UMAP/t-SNE 归一化到 0-1 的值）
    const plotW = W - PADDING * 2
    const plotH = H - PADDING * 2
    coordsRef.current = points.map(p => ({
      cx: PADDING + p.x * plotW,
      cy: PADDING + (1 - p.y) * plotH,
      title: p.title,
      source: p.source,
      published: p.published || '',
      score: p.score || 0,
      link: p.link || '',
      cluster: p.cluster,
    }))

    // 绘制半透明网格线（4x4）
    octx.strokeStyle = 'rgba(255,255,255,0.03)'
    octx.lineWidth = 0.5
    for (let i = 0; i <= 4; i++) {
      const gx = PADDING + (plotW / 4) * i
      const gy = PADDING + (plotH / 4) * i
      octx.beginPath(); octx.moveTo(gx, PADDING); octx.lineTo(gx, PADDING + plotH); octx.stroke()
      octx.beginPath(); octx.moveTo(PADDING, gy); octx.lineTo(PADDING + plotW, gy); octx.stroke()
    }

    // 绘制所有散点
    for (const p of coordsRef.current) {
      const color = clusterMap.current[p.cluster] || '#888'
      const alpha = activeCluster >= 0 ? 'e6' : 'a6'  // 筛选模式下增加不透明度
      octx.beginPath()
      octx.arc(p.cx, p.cy, DOT_RADIUS, 0, Math.PI * 2)
      octx.fillStyle = color + alpha
      octx.fill()
      octx.strokeStyle = 'rgba(0,0,0,0.3)'
      octx.lineWidth = 0.3
      octx.stroke()
    }

    // 更新底部统计信息
    const en = locale === 'en'
    setInfo(en
      ? `Showing ${coordsRef.current.length} articles · ${data.n_clusters} clusters total`
      : `显示 ${coordsRef.current.length} 篇文章 · 共 ${data.n_clusters} 个聚类`
    )

    // 将离屏 Canvas 复制到主 Canvas
    const ctx = canvas.getContext('2d')!
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(off, 0, 0)
  }

  /**
   * redrawHighlight - 轻量重绘：先复制离屏背景，再绘制高亮圆圈
   * 用于鼠标悬停时的高效响应
   */
  const redrawHighlight = (hovered: typeof coordsRef.current[0] | null) => {
    const canvas = canvasRef.current
    const off = offscreenRef.current
    if (!canvas || !off) return

    const ctx = canvas.getContext('2d')!
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(off, 0, 0)

    if (hovered) {
      const dpr = window.devicePixelRatio || 1
      const c = clusterMap.current[hovered.cluster] || '#888'
      ctx.save()
      ctx.scale(dpr, dpr)
      ctx.beginPath()
      ctx.arc(hovered.cx, hovered.cy, HOVER_RADIUS, 0, Math.PI * 2)
      ctx.fillStyle = c + '40'
      ctx.fill()
      ctx.strokeStyle = c
      ctx.lineWidth = 2
      ctx.stroke()
      ctx.restore()
    }
  }

  /**
   * draw - 完整绘制流程：渲染背景 + 绑定交互事件
   */
  const draw = () => {
    renderBackground()

    const canvas = canvasRef.current
    const tooltip = tooltipRef.current
    if (!canvas || !tooltip) return

    const W = parseInt(canvas.style.width)
    const H = parseInt(canvas.style.height)
    let hovered: (typeof coordsRef.current)[0] | null = null

    // 鼠标移动：查找最近散点 → 高亮 + 显示 tooltip
    canvas.onmousemove = (e) => {
      const rect = canvas.getBoundingClientRect()
      const mx = (e.clientX - rect.left) * (W / rect.width)
      const my = (e.clientY - rect.top) * (H / rect.height)

      let closest: (typeof coordsRef.current)[0] | null = null
      let minDist = 15
      for (const p of coordsRef.current) {
        const dx = mx - p.cx, dy = my - p.cy
        const d = Math.sqrt(dx * dx + dy * dy)
        if (d < minDist) { minDist = d; closest = p }
      }

      if (closest !== hovered) {
        hovered = closest
        redrawHighlight(closest)

        if (closest) {
          // 构建 tooltip HTML（带 XSS 防护的 HTML 转义）
          const esc = (s: string) => {
            const d = document.createElement('div')
            d.textContent = s
            return d.innerHTML
          }
          tooltip.innerHTML = `
            <div style="font-weight:500;color:#e8e9f0;line-height:1.35;margin-bottom:.3rem;font-size:.8rem">${esc(closest.title)}</div>
            <div style="color:#9898b0;font-size:.72rem;display:flex;gap:.5rem;flex-wrap:wrap">
              <span>${esc(closest.source)}</span>
              <span>${esc(closest.published.slice(0, 10))}</span>
              <span>${closest.score}</span>
            </div>`
          tooltip.style.opacity = '1'

          // 智能定位 tooltip（避免超出边界）
          const tw = tooltip.offsetWidth
          const th = tooltip.offsetHeight
          let tx = mx + 16, ty = my - th - 10
          if (tx + tw > W) tx = mx - tw - 16
          if (ty < 0) ty = my + 16
          tooltip.style.left = tx + 'px'
          tooltip.style.top = ty + 'px'
        } else {
          tooltip.style.opacity = '0'
        }
      }
    }

    // 点击：打开对应文章原文链接
    canvas.onclick = (e) => {
      const rect = canvas.getBoundingClientRect()
      const mx = (e.clientX - rect.left) * (W / rect.width)
      const my = (e.clientY - rect.top) * (H / rect.height)

      let closest: (typeof coordsRef.current)[0] | null = null
      let minDist = 15
      for (const p of coordsRef.current) {
        const dx = mx - p.cx, dy = my - p.cy
        const d = Math.sqrt(dx * dx + dy * dy)
        if (d < minDist) { minDist = d; closest = p }
      }
      if (closest?.link) window.open(closest.link, '_blank')
    }

    // 鼠标离开：隐藏 tooltip + 清除高亮
    canvas.onmouseleave = () => {
      tooltip.style.opacity = '0'
      hovered = null
      redrawHighlight(null)
    }
  }

  // 数据或聚类筛选变化时重绘
  useEffect(() => { draw() }, [data, activeCluster])
  // 窗口大小变化时重绘
  useEffect(() => {
    const onResize = () => draw()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [data, activeCluster])

  return (
    <div className="space-y-3">
      {/* ========== 聚类筛选按钮栏 ========== */}
      <div className="flex flex-wrap gap-2 justify-center">
        {/* "全部"按钮 */}
        <button
          onClick={() => setActiveCluster(-1)}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs transition-all border ${
            activeCluster === -1
              ? 'border-accent bg-accent-muted text-accent shadow-[0_0_8px_rgba(108,92,231,0.15)]'
              : 'border-transparent text-text-secondary hover:border-border-default hover:bg-bg-hover'
          }`}
        >
          <span className="w-2.5 h-2.5 rounded-full bg-text-muted" />
          {locale === 'en' ? `All (${data.total_articles})` : `全部 (${data.total_articles})`}
        </button>
        {/* 各聚类筛选按钮 */}
        {data.clusters.map(c => (
          <button
            key={c.id}
            onClick={() => setActiveCluster(c.id)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs transition-all border ${
              activeCluster === c.id
                ? 'border-accent bg-accent-muted text-accent shadow-[0_0_8px_rgba(108,92,231,0.15)]'
                : 'border-transparent text-text-secondary hover:border-border-default hover:bg-bg-hover'
            }`}
          >
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c.color }} />
            {c.title.slice(0, 35)} ({c.count})
          </button>
        ))}
      </div>

      {/* ========== Canvas 散点图 ========== */}
      <div className="relative w-full overflow-hidden bg-bg-secondary rounded-xl border border-border-muted">
        <canvas ref={canvasRef} className="block w-full cursor-crosshair" />
        {/* 悬停 tooltip */}
        <div
          ref={tooltipRef}
          className="absolute pointer-events-none z-50 bg-bg-card border border-border-default rounded-lg px-3 py-2.5 max-w-[280px] shadow-xl opacity-0 transition-opacity"
        />
      </div>
      {/* 底部统计信息 */}
      <p className="text-center text-xs text-text-muted">{info}</p>
    </div>
  )
}

/**
 * ClustersPage - 话题聚类分析页面入口
 * 
 * 数据来源：useClusters() → data/clusters.json
 * 页面结构：标题 + Canvas 散点图 + 聚类卡片网格
 */
export function ClustersPage() {
  const { data, loading } = useClusters()
  const { locale } = useLocale()

  // 加载中 → 骨架屏
  if (loading) {
    return (
      <div className="space-y-4">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    )
  }

  // 空数据状态
  if (!data || !data.clusters || !data.clusters.length) {
    return (
      <div className="text-center py-20">
        <FontAwesomeIcon icon={ICON.clusters} className="text-4xl text-text-muted mb-4" />
        <p className="text-text-muted">{locale === 'en' ? 'No cluster data yet' : '暂无聚类数据'}</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* ========== 页面标题 ========== */}
      <FadeIn>
        <div className="text-center py-4">
          <h1 className="text-3xl font-bold text-text-primary flex items-center justify-center gap-2">
            <FontAwesomeIcon icon={ICON.clusters} className="text-accent" />
            {locale === 'en' ? 'Cluster Analysis' : '聚类分析'}
          </h1>
          <p className="mt-2 text-text-muted text-sm">
            {locale === 'en'
              ? `TF-IDF semantic clustering · ${data.n_clusters} clusters · ${data.total_articles} articles`
              : `基于 TF-IDF 语义相似度的文章聚类可视化 · ${data.n_clusters} 个聚类 · ${data.total_articles} 篇文章`
            }
          </p>
        </div>
      </FadeIn>

      {/* ========== Canvas 散点图 ========== */}
      <FadeIn delay={0.1}>
        <ClusterScatter data={data} locale={locale} />
      </FadeIn>

      {/* ========== 聚类详情卡片网格 ========== */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.clusters.map((cluster) => {
          // 取该聚类下分数最高的前 8 篇文章
          const clusterArticles = (data.points || [])
            .filter(p => p.cluster === cluster.id)
            .sort((a, b) => (b.score || 0) - (a.score || 0))
            .slice(0, 8)

          return (
          <FadeIn key={cluster.id} delay={0.05}>
            <div
              className="bg-bg-card border border-border-muted rounded-xl p-5 hover:border-accent/20 hover:shadow-[0_0_20px_-8px_rgba(108,92,231,0.1)] transition-all duration-300"
            >
              {/* 聚类标题 + 颜色标识 + 文章数 */}
              <div className="flex items-center gap-2 mb-3">
                <span
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: cluster.color }}
                />
                <h2 className="text-base font-semibold text-text-primary">{cluster.title}</h2>
                <span className="text-xs text-text-muted bg-bg-secondary px-2 py-0.5 rounded-full">
                  {cluster.count} {locale === 'en' ? '' : '篇'}
                </span>
              </div>
              {/* 关键词标签 */}
              {cluster.keywords && cluster.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {cluster.keywords.slice(0, 8).map((kw, j) => (
                    <span
                      key={j}
                      className="px-2 py-0.5 rounded-full text-[11px] bg-accent-muted text-accent"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              )}
              {/* 文章链接列表 */}
              {clusterArticles.length > 0 && (
                <ul className="space-y-1.5 border-t border-border-muted pt-3">
                  {clusterArticles.map((a) => (
                    <li key={a.id}>
                      <a
                        href={a.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-start gap-2 text-sm text-text-secondary hover:text-accent transition-colors group"
                      >
                        <span className="text-[10px] text-text-muted mt-0.5 flex-shrink-0">&#9679;</span>
                        <span className="line-clamp-1">{a.title}</span>
                        <span className="text-xs text-text-muted flex-shrink-0 ml-auto">{a.source}</span>
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </FadeIn>
        )})}
      </div>
    </div>
  )
}
