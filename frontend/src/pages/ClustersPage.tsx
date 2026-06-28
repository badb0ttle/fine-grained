import { useEffect, useRef, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { ICON } from '../lib/icons'
import { FadeIn } from '../components/Animations'
import { CardSkeleton } from '../components/Skeleton'
import { useLocale } from '../lib/LocaleContext'
import { useClusters } from '../hooks/useData'
import type { ClusterData } from '../types'

const PADDING = 50
const DOT_RADIUS = 4
const HOVER_RADIUS = 8

function ClusterScatter({ data, locale }: { data: ClusterData; locale: 'zh' | 'en' }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const offscreenRef = useRef<HTMLCanvasElement | null>(null)
  const [activeCluster, setActiveCluster] = useState<number>(-1)
  const [info, setInfo] = useState('')
  const coordsRef = useRef<{ cx: number; cy: number; title: string; source: string; published: string; score: number; link: string; cluster: number }[]>([])
  const clusterMap = useRef<Record<number, string>>({})

  useEffect(() => {
    const map: Record<number, string> = {}
    for (const c of data.clusters) map[c.id] = c.color
    clusterMap.current = map
  }, [data])

  /** Render background (grid + all dots) to offscreen canvas — only recalculated on data/filter change. */
  const renderBackground = () => {
    const canvas = canvasRef.current
    if (!canvas) return

    const dpr = window.devicePixelRatio || 1
    const parent = canvas.parentElement!
    const W = parent.clientWidth
    const H = Math.min(W * 0.7, 550)

    canvas.width = W * dpr
    canvas.height = H * dpr
    canvas.style.width = W + 'px'
    canvas.style.height = H + 'px'

    // Create or re-use offscreen canvas
    if (!offscreenRef.current) {
      offscreenRef.current = document.createElement('canvas')
    }
    const off = offscreenRef.current
    off.width = W * dpr
    off.height = H * dpr

    const octx = off.getContext('2d')!
    octx.scale(dpr, dpr)

    // Background
    octx.fillStyle = '#0a0b14'
    octx.fillRect(0, 0, W, H)

    // Points
    let points = data.points
    if (activeCluster >= 0) {
      points = points.filter(p => p.cluster === activeCluster)
    }

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

    // Grid
    octx.strokeStyle = 'rgba(255,255,255,0.03)'
    octx.lineWidth = 0.5
    for (let i = 0; i <= 4; i++) {
      const gx = PADDING + (plotW / 4) * i
      const gy = PADDING + (plotH / 4) * i
      octx.beginPath(); octx.moveTo(gx, PADDING); octx.lineTo(gx, PADDING + plotH); octx.stroke()
      octx.beginPath(); octx.moveTo(PADDING, gy); octx.lineTo(PADDING + plotW, gy); octx.stroke()
    }

    // Dots
    for (const p of coordsRef.current) {
      const color = clusterMap.current[p.cluster] || '#888'
      const alpha = activeCluster >= 0 ? 'e6' : 'a6'
      octx.beginPath()
      octx.arc(p.cx, p.cy, DOT_RADIUS, 0, Math.PI * 2)
      octx.fillStyle = color + alpha
      octx.fill()
      octx.strokeStyle = 'rgba(0,0,0,0.3)'
      octx.lineWidth = 0.3
      octx.stroke()
    }

    const en = locale === 'en'
    setInfo(en
      ? `Showing ${coordsRef.current.length} articles · ${data.n_clusters} clusters total`
      : `显示 ${coordsRef.current.length} 篇文章 · 共 ${data.n_clusters} 个聚类`
    )

    // Copy offscreen to main
    const ctx = canvas.getContext('2d')!
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(off, 0, 0)
  }

  /** Lightweight redraw: copy offscreen + highlight only. */
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

  const draw = () => {
    renderBackground()

    const canvas = canvasRef.current
    const tooltip = tooltipRef.current
    if (!canvas || !tooltip) return

    const W = parseInt(canvas.style.width)
    const H = parseInt(canvas.style.height)
    let hovered: (typeof coordsRef.current)[0] | null = null

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

    canvas.onmouseleave = () => {
      tooltip.style.opacity = '0'
      hovered = null
      redrawHighlight(null)
    }
  }

  useEffect(() => { draw() }, [data, activeCluster])
  useEffect(() => {
    const onResize = () => draw()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [data, activeCluster])

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 justify-center">
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

      <div className="relative w-full overflow-hidden bg-bg-secondary rounded-xl border border-border-muted">
        <canvas ref={canvasRef} className="block w-full cursor-crosshair" />
        <div
          ref={tooltipRef}
          className="absolute pointer-events-none z-50 bg-bg-card border border-border-default rounded-lg px-3 py-2.5 max-w-[280px] shadow-xl opacity-0 transition-opacity"
        />
      </div>
      <p className="text-center text-xs text-text-muted">{info}</p>
    </div>
  )
}

export function ClustersPage() {
  const { data, loading } = useClusters()
  const { locale } = useLocale()

  if (loading) {
    return (
      <div className="space-y-4">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    )
  }

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

      <FadeIn delay={0.1}>
        <ClusterScatter data={data} locale={locale} />
      </FadeIn>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.clusters.map((cluster) => {
          const clusterArticles = (data.points || [])
            .filter(p => p.cluster === cluster.id)
            .sort((a, b) => (b.score || 0) - (a.score || 0))
            .slice(0, 8)

          return (
          <FadeIn key={cluster.id} delay={0.05}>
            <div
              className="bg-bg-card border border-border-muted rounded-xl p-5 hover:border-accent/20 hover:shadow-[0_0_20px_-8px_rgba(108,92,231,0.1)] transition-all duration-300"
            >
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
              {/* Article links */}
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
