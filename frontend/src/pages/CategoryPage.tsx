/**
 * CategoryPage - 按分类浏览页面
 * 
 * 页面功能：展示某一分类下的所有文章，支持本地搜索筛选和分页浏览
 *         每页显示 20 篇文章，分页支持快捷导航（带省略号逻辑）
 * 
 * 路由路径：/category/:name（如 /category/AI Lab）
 * 参数说明：name 经过 encodeURIComponent 编码
 * 
 * 数据来源：useLatest() → data/latest.json（全部最新文章，前端按分类筛选）
 * 
 * Props：无（从 URL params 获取分类名称）
 * 使用 Context：LocaleContext（中英双语）
 */

import { useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { useLatest } from '../hooks/useData'
import type { CategoryKey } from '../types'
import { CATEGORY_ICONS, DEFAULT_CATEGORY_ICON, ICON } from '../lib/icons'
import { ScrollReveal, FadeIn } from '../components/Animations'
import { HomePageSkeleton } from '../components/Skeleton'
import { useLocale } from '../lib/LocaleContext'

/** 每页显示的文章数量 */
const PAGE_SIZE = 20

/** i18n 中英双语文案 */
const T = {
  categoryMeta: {
    'AI Lab':     { zh: '热点文章',  en: 'Hot Articles' },
    'Paper':      { zh: '学术论文',   en: 'Papers' },
    '中文媒体':    { zh: '中文媒体',   en: 'Chinese Media' },
    'Blog':       { zh: '技术博客',   en: 'Tech Blogs' },
    'Community':  { zh: '社区动态',   en: 'Community' },
    'Discussion': { zh: '技术讨论',   en: 'Discussion' },
  } as Record<string, { zh: string; en: string }>,
  defaultCategory:  { zh: '其他', en: 'Other' },
  backHome:         { zh: '返回首页', en: 'Back to Home' },
  totalArticles:    { zh: '篇', en: 'articles' },
  noData:           { zh: '暂无数据，等待首次扫描完成...', en: 'No data yet. Waiting for the first scan...' },
  paperTag:         { zh: '论文', en: 'Paper' },
  searchPlaceholder:{ zh: '搜索标题或摘要...', en: 'Search titles & summaries...' },
  noMatch:          { zh: '未找到匹配的文章', en: 'No matching articles' },
  pageInfo:         { zh: '第 {current} / {total} 页', en: 'Page {current} of {total}' },
}

/** i18n 辅助函数 */
function t(obj: { zh: string; en: string } | string, locale: string): string {
  if (typeof obj === 'string') return obj
  return obj[locale as 'zh' | 'en'] || obj.zh
}

/** 清理 arXiv boilerplate 文本（与 HomePage 一致性） */
function cleanSummary(raw: string): string {
  return raw
    .replace(/^arXiv:[\d.]+v?\d*\s*(Announce Type:\s*\w+\s*)?\n?Abstract:\s*/i, '')
    .slice(0, 280)
}

/**
 * CategoryPage - 按分类浏览页面组件
 * 
 * 功能流程：
 *   1. 从 URL 获取分类名称（decodeURIComponent 解码）
 *   2. 从 useLatest() 获取全部文章，前端按分类过滤
 *   3. 本地搜索框支持对标题/摘要模糊匹配
 *   4. 分页：每页 20 篇，支持前后翻页 + 页码省略号逻辑
 */
export function CategoryPage() {
  /** name：URL 路径中的分类名称（已 decodeURIComponent 解码） */
  const { name } = useParams<{ name: string }>()
  const { data, loading, error } = useLatest()
  const { locale } = useLocale()

  const categoryName = decodeURIComponent(name || '')

  /** query：本地搜索文本 */
  const [query, setQuery] = useState('')
  /** page：当前页码（从 1 开始） */
  const [page, setPage] = useState(1)

  /** normalizedQuery：trim + 转小写后的搜索文本 */
  const normalizedQuery = query.trim().toLowerCase()

  /** articles：按分类筛选后的文章列表（若搜索则进一步按标题/摘要过滤） */
  const articles = useMemo(() => {
    if (!data?.articles) return []
    let subset = data.articles.filter(a => (a.category || 'Other') === categoryName)
    if (normalizedQuery) {
      subset = subset.filter(a => {
        const isEn = locale === 'en'
        const title = isEn ? (a.title || a.title_cn || '') : (a.title_cn || a.title || '')
        const summary = isEn
          ? (a.summary || a.summary_cn || '')
          : (a.summary_cn || a.summary || '')
        return title.toLowerCase().includes(normalizedQuery)
          || summary.toLowerCase().includes(normalizedQuery)
      })
    }
    return subset
  }, [data, categoryName, normalizedQuery, locale])

  /** totalPages：总页数 */
  const totalPages = Math.max(1, Math.ceil(articles.length / PAGE_SIZE))
  /** safePage：安全页码（不超过总页数） */
  const safePage = Math.min(page, totalPages)
  /** pagedArticles：当前页的文章切片 */
  const pagedArticles = useMemo(
    () => articles.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE),
    [articles, safePage],
  )

  // 如果页码超出合法范围，修正到最后一页
  if (safePage !== page) {
    setTimeout(() => setPage(safePage), 0)
  }

  const meta = T.categoryMeta[categoryName] || T.defaultCategory
  const catIcon = CATEGORY_ICONS[categoryName as CategoryKey] || DEFAULT_CATEGORY_ICON

  /** pageWindow：分页导航栏的页码列表（含省略号逻辑） */
  const pageWindow = useMemo(() => {
    const pages: (number | '...')[] = []
    const delta = 2
    const EDGE_FIRST = 4  // 头部始终显示的页数
    const EDGE_LAST = 3   // 尾部始终显示的页数
    let start = Math.max(1, safePage - delta)
    let end = Math.min(totalPages, safePage + delta)
    if (totalPages <= 10) {
      // ≤10 页：全部显示
      for (let i = 1; i <= totalPages; i++) pages.push(i)
    } else {
      // 头部固定页
      if (start > EDGE_FIRST + 1) {
        for (let i = 1; i <= EDGE_FIRST; i++) pages.push(i)
        pages.push('...')
      } else {
        for (let i = 1; i < start; i++) pages.push(i)
      }
      // 当前窗口页
      for (let i = start; i <= end; i++) pages.push(i)
      // 尾部固定页
      if (end < totalPages - EDGE_LAST) {
        pages.push('...')
        for (let i = totalPages - EDGE_LAST + 1; i <= totalPages; i++) pages.push(i)
      } else {
        for (let i = end + 1; i <= totalPages; i++) pages.push(i)
      }
    }
    return pages
  }, [safePage, totalPages])

  /** 切换页码：滚动到顶部 */
  const handlePageChange = (p: number) => {
    if (p >= 1 && p <= totalPages) {
      setPage(p)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  /** 搜索输入 → 重置到第 1 页 */
  const handleSearch = (value: string) => {
    setQuery(value)
    setPage(1)
  }

  // 加载中 → 骨架屏
  if (loading) return <HomePageSkeleton />

  // 错误/空数据 → 提示
  if (error || !data || !data.articles.length) {
    return (
      <div className="text-center py-20">
        <FontAwesomeIcon icon={ICON.inbox} className="text-4xl text-text-muted mb-4" />
        <p className="text-text-muted">{t(T.noData, locale)}</p>
        {error && <p className="text-xs text-red mt-2">{error}</p>}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <FadeIn>
        {/* ========== 返回首页链接 ========== */}
        <div className="flex items-center gap-3 mb-4">
          <Link
            to="/"
            className="text-sm text-text-muted hover:text-accent transition-colors flex items-center gap-1"
          >
            <FontAwesomeIcon icon={ICON.arrowLeft} />
            {t(T.backHome, locale)}
          </Link>
        </div>

        {/* ========== 分类标题 + 搜索栏 ========== */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5">
          <div className="flex items-center gap-2">
            <FontAwesomeIcon icon={catIcon} className="text-accent text-xl" />
            <h1 className="text-2xl font-bold text-text-primary">{t(meta, locale)}</h1>
            <span className="text-sm text-text-muted bg-bg-secondary px-2.5 py-0.5 rounded-full">
              {articles.length} {t(T.totalArticles, locale)}
            </span>
          </div>

          {/* 本地搜索输入框 */}
          <div className="relative w-full sm:w-72">
            <FontAwesomeIcon
              icon={ICON.search}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm pointer-events-none"
            />
            <input
              type="text"
              value={query}
              onChange={e => handleSearch(e.target.value)}
              placeholder={t(T.searchPlaceholder, locale)}
              className="w-full pl-9 pr-8 py-2 text-sm bg-bg-secondary border border-border-muted rounded-lg text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-accent/40 transition-colors"
            />
            {/* 清除搜索按钮 */}
            {query && (
              <button
                onClick={() => handleSearch('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors"
                aria-label="Clear search"
              >
                <FontAwesomeIcon icon={ICON.times} className="text-xs" />
              </button>
            )}
          </div>
        </div>
      </FadeIn>

      {/* ========== 文章列表（分页展示） ========== */}
      {pagedArticles.length === 0 ? (
        <div className="text-center py-16">
          <FontAwesomeIcon icon={ICON.inbox} className="text-4xl text-text-muted mb-3" />
          <p className="text-text-muted">
            {normalizedQuery ? t(T.noMatch, locale) : t(T.noData, locale)}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {pagedArticles.map((a, i) => {
            const isEn = locale === 'en'
            const title = isEn ? (a.title || a.title_cn) : (a.title_cn || a.title)
            const summary = isEn
              ? (a.summary ? cleanSummary(a.summary) : (a.summary_cn ? a.summary_cn.slice(0, 280) : ''))
              : (a.summary_cn || (a.summary ? cleanSummary(a.summary) : ''))
            /** why_it_matters：LLM 解读（仅中文模式显示） */
            const why = !isEn && a.why_it_matters ? a.why_it_matters : null

            return (
              <ScrollReveal key={i} index={i}>
                {/* 文章卡片（与 HomePage 的 ArticleCard 结构一致） */}
                <div className="article-item bg-bg-card border border-border-muted rounded-xl p-4 hover:border-accent/20 hover:bg-bg-elevated hover:shadow-[0_0_20px_-8px_rgba(108,92,231,0.1)] transition-all duration-300 group">
                  {/* 标题行：论文图标 + 外链 */}
                  <div className="flex items-start gap-2">
                    <a
                      href={a.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[15px] font-medium text-text-primary group-hover:text-accent transition-colors leading-snug flex-1"
                    >
                      {a.is_paper && (
                        <FontAwesomeIcon icon={ICON.fileLines} className="mr-1.5 text-accent/60 text-xs" />
                      )}
                      {title}
                    </a>
                  </div>
                  {/* 元数据：来源 + 日期 */}
                  <div className="flex items-center gap-2 mt-1.5 text-xs text-text-muted">
                    {a.category && (
                      <FontAwesomeIcon icon={catIcon} className="mr-1 text-text-muted/60" />
                    )}
                    <span className="text-text-secondary">{a.source}</span>
                    <span>·</span>
                    <span>{a.published}</span>
                  </div>
                  {/* 摘要 */}
                  {summary && (
                    <p className="mt-2 text-sm text-text-secondary leading-relaxed line-clamp-2">
                      {summary.slice(0, 280)}
                    </p>
                  )}
                  {/* "为什么重要"解读 */}
                  {why && (
                    <div className="mt-2 text-xs text-amber/80 bg-amber/5 border border-amber/10 rounded-lg px-3 py-1.5 flex items-start gap-1.5">
                      <FontAwesomeIcon icon={ICON.lightbulb} className="mt-0.5 flex-shrink-0" />
                      {why}
                    </div>
                  )}
                </div>
              </ScrollReveal>
            )
          })}
        </div>
      )}

      {/* ========== 分页导航栏 ========== */}
      {totalPages > 1 && (
        <FadeIn>
          <div className="flex items-center justify-center gap-1.5 pt-4 pb-8">
            {/* 上一页按钮 */}
            <button
              onClick={() => handlePageChange(safePage - 1)}
              disabled={safePage <= 1}
              className="w-9 h-9 flex items-center justify-center rounded-lg text-sm text-text-muted hover:text-text-primary hover:bg-bg-secondary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              aria-label="Previous page"
            >
              <FontAwesomeIcon icon={ICON.chevronLeft} className="text-xs" />
            </button>

            {/* 页码按钮（含省略号） */}
            {pageWindow.map((p, idx) =>
              p === '...' ? (
                <span key={`dots-${idx}`} className="w-9 h-9 flex items-center justify-center text-sm text-text-muted">
                  …
                </span>
              ) : (
                <button
                  key={p}
                  onClick={() => handlePageChange(p)}
                  className={`w-9 h-9 flex items-center justify-center rounded-lg text-sm transition-colors ${
                    p === safePage
                      ? 'bg-accent text-white font-medium'
                      : 'text-text-muted hover:text-text-primary hover:bg-bg-secondary'
                  }`}
                >
                  {p}
                </button>
              ),
            )}

            {/* 下一页按钮 */}
            <button
              onClick={() => handlePageChange(safePage + 1)}
              disabled={safePage >= totalPages}
              className="w-9 h-9 flex items-center justify-center rounded-lg text-sm text-text-muted hover:text-text-primary hover:bg-bg-secondary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              aria-label="Next page"
            >
              <FontAwesomeIcon icon={ICON.chevronRight} className="text-xs" />
            </button>
          </div>
        </FadeIn>
      )}
    </div>
  )
}
