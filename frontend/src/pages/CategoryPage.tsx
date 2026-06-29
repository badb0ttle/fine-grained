import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { useLatest } from '../hooks/useData'
import type { CategoryKey } from '../types'
import { CATEGORY_ICONS, DEFAULT_CATEGORY_ICON, ICON } from '../lib/icons'
import { ScrollReveal, FadeIn } from '../components/Animations'
import { HomePageSkeleton } from '../components/Skeleton'
import { useLocale } from '../lib/LocaleContext'

// ── i18n ──
const T = {
  categoryMeta: {
    'AI Lab':    { zh: 'AI 实验室',    en: 'AI Labs' },
    'Paper':     { zh: '学术论文',     en: 'Papers' },
    '中文媒体':   { zh: '中文媒体',     en: 'Chinese Media' },
    'Blog':      { zh: '技术博客',     en: 'Tech Blogs' },
    'Community': { zh: '社区动态',     en: 'Community' },
    'Discussion':{ zh: '技术讨论',     en: 'Discussion' },
  } as Record<string, { zh: string; en: string }>,
  defaultCategory: { zh: '其他', en: 'Other' },
  backHome:       { zh: '← 返回首页', en: '← Back to Home' },
  totalArticles:  { zh: '篇', en: 'articles' },
  noData:         { zh: '暂无数据，等待首次扫描完成...', en: 'No data yet. Waiting for the first scan...' },
  paperTag:       { zh: '论文', en: 'Paper' },
}

function t(obj: { zh: string; en: string } | string, locale: string): string {
  if (typeof obj === 'string') return obj
  return obj[locale as 'zh' | 'en'] || obj.zh
}

// ── Helpers (mirrored from HomePage) ──
function cleanSummary(raw: string): string {
  return raw
    .replace(/^arXiv:[\d.]+v?\d*\s*(Announce Type:\s*\w+\s*)?\n?Abstract:\s*/i, '')
    .slice(0, 280)
}

// ── Category Page ──
export function CategoryPage() {
  const { name } = useParams<{ name: string }>()
  const { data, loading, error } = useLatest()
  const { locale } = useLocale()

  const categoryName = decodeURIComponent(name || '')

  const articles = useMemo(() => {
    if (!data?.articles) return []
    return data.articles.filter(a => (a.category || 'Other') === categoryName)
  }, [data, categoryName])

  const meta = T.categoryMeta[categoryName] || T.defaultCategory
  const catIcon = CATEGORY_ICONS[categoryName as CategoryKey] || DEFAULT_CATEGORY_ICON

  if (loading) return <HomePageSkeleton />

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
        <div className="flex items-center gap-3 mb-6">
          <Link
            to="/"
            className="text-sm text-text-muted hover:text-accent transition-colors flex items-center gap-1"
          >
            <FontAwesomeIcon icon={ICON.arrowLeft} />
            {t(T.backHome, locale)}
          </Link>
        </div>
        <div className="flex items-center gap-2">
          <FontAwesomeIcon icon={catIcon} className="text-accent text-xl" />
          <h1 className="text-2xl font-bold text-text-primary">{t(meta, locale)}</h1>
          <span className="text-sm text-text-muted bg-bg-secondary px-2.5 py-0.5 rounded-full">
            {articles.length} {t(T.totalArticles, locale)}
          </span>
        </div>
      </FadeIn>

      {articles.length === 0 ? (
        <div className="text-center py-16">
          <FontAwesomeIcon icon={ICON.inbox} className="text-4xl text-text-muted mb-3" />
          <p className="text-text-muted">{t(T.noData, locale)}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {articles.map((a, i) => {
            const isEn = locale === 'en'
            const title = isEn ? (a.title || a.title_cn) : (a.title_cn || a.title)
            const summary = isEn
              ? (a.summary ? cleanSummary(a.summary) : (a.summary_cn ? a.summary_cn.slice(0, 280) : ''))
              : (a.summary_cn || (a.summary ? cleanSummary(a.summary) : ''))
            const why = !isEn && a.why_it_matters ? a.why_it_matters : null

            return (
              <ScrollReveal key={i} index={i}>
                <div className="article-item bg-bg-card border border-border-muted rounded-xl p-4 hover:border-accent/20 hover:bg-bg-elevated hover:shadow-[0_0_20px_-8px_rgba(108,92,231,0.1)] transition-all duration-300 group">
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
                  <div className="flex items-center gap-2 mt-1.5 text-xs text-text-muted">
                    {a.category && (
                      <FontAwesomeIcon icon={catIcon} className="mr-1 text-text-muted/60" />
                    )}
                    <span className="text-text-secondary">{a.source}</span>
                    <span>·</span>
                    <span>{a.published}</span>
                  </div>
                  {summary && (
                    <p className="mt-2 text-sm text-text-secondary leading-relaxed line-clamp-2">
                      {summary.slice(0, 280)}
                    </p>
                  )}
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
    </div>
  )
}
