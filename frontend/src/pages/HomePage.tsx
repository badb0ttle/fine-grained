import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { useLatest, useTrending, useTop5, useAgentTools, useEvents } from '../hooks/useData'
import type { Article, CategoryKey, Top5Data, AgentToolsData, EventsData } from '../types'
import { CATEGORY_ICONS, DEFAULT_CATEGORY_ICON, ICON } from '../lib/icons'
import { ScrollReveal, StaggerContainer, FadeIn } from '../components/Animations'
import { HomePageSkeleton } from '../components/Skeleton'
import { ModelLeaderboardPreview } from '../components/ModelLeaderboard'
import { useLocale, type Locale } from '../lib/LocaleContext'
import { useJsonLd } from '../lib/useJsonLd'

// ── i18n dictionaries ──
const T = {
  categoryMeta: {
    'AI Lab':    { zh: '热点文章',    en: 'Hot Articles' },
    'Paper':     { zh: '学术论文',     en: 'Papers' },
    '中文媒体':   { zh: '中文媒体',     en: 'Chinese Media' },
    'Blog':      { zh: '技术博客',     en: 'Tech Blogs' },
    'Community': { zh: '社区动态',     en: 'Community' },
    'Discussion':{ zh: '技术讨论',     en: 'Discussion' },
  } as Record<string, { zh: string; en: string }>,
  defaultCategory: { zh: '其他', en: 'Other' },
  searchPlaceholder: { zh: '搜索文章...', en: 'Search articles...' },
  noResults: { zh: '未找到相关文章', en: 'No results found' },
  sources: { zh: '源', en: 'sources' },
  curated: { zh: '篇精选', en: 'curated' },
  heroDesc: {
    zh: '每日自动扫描 30+ 全球 AI 信源 — 顶级实验室博客、学术论文、技术媒体、GitHub 热门项目 — 由 LLM 精选并深度解读，帮你 5 分钟把握 AI 技术脉搏',
    en: 'Daily AI intelligence — scanning 30+ global sources, curated and translated by LLM. Stay on top of AI in 5 minutes a day.',
  },
  sourceTags: [
    'OpenAI / Anthropic / DeepMind',
    { zh: 'arXiv 论文',       en: 'arXiv Papers' },
    'Hacker News / Reddit',
    'GitHub Trending',
    { zh: '中文 AI 媒体',     en: 'Chinese AI Media' },
  ],
  githubTop5:        { zh: 'GitHub AI 开源项目 · Top 5', en: 'GitHub AI Open Source · Top 5' },
  sortedByStars:     { zh: '按 Star 排序',  en: 'By Stars' },
  viewOnGithub:      { zh: '在 GitHub 上查看', en: 'View on GitHub' },
  agentTools:        { zh: 'Agent & MCP 工具周榜', en: 'Agent & MCP Tools Weekly' },
  agentTypeMCP:      { zh: 'MCP 服务器', en: 'MCP Server' },
  agentTypeTool:     { zh: 'Agent 工具', en: 'Agent Tool' },
  agentTypeSkill:    { zh: 'Agent 技能', en: 'Agent Skill' },
  eventsTitle:       { zh: '多源事件聚合', en: 'Cross-source Events' },
  eventsSubtitle:    { zh: '按事件聚合', en: 'Grouped by event' },
  eventsArticles:    { zh: '篇报道', en: 'articles' },
  paperTag:          { zh: '论文',    en: 'Paper' },
  continueReading:   { zh: '继续阅读', en: 'Continue Reading' },
  noData:            { zh: '暂无数据，等待首次扫描完成...', en: 'No data yet. Waiting for the first scan...' },
}

function t(obj: { zh: string; en: string } | string, locale: Locale): string {
  if (typeof obj === 'string') return obj
  return obj[locale]
}

// ── Search Bar ──
function SearchBar({ query, setQuery, results, clear, locale }: ReturnType<typeof useSearch> & { locale: Locale }) {
  const [focused, setFocused] = useState(false)

  return (
    <div className="relative" onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget)) setFocused(false) }}>
      <div className="relative">
        <FontAwesomeIcon icon={ICON.search} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm" />
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          placeholder={t(T.searchPlaceholder, locale)}
          className="w-60 lg:w-72 bg-bg-secondary border border-border-default rounded-lg pl-9 pr-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50 transition-colors"
        />
      </div>
      {focused && query.length >= 2 && (
        <div className="absolute top-full mt-2 left-0 w-80 bg-bg-card border border-border-default rounded-xl shadow-2xl overflow-hidden z-50">
          {results.length === 0 ? (
            <div className="p-4 text-text-muted text-sm text-center">{t(T.noResults, locale)}</div>
          ) : (
            results.map((a, i) => (
              <a
                key={i}
                href={a.link}
                target="_blank"
                rel="noopener noreferrer"
                onClick={clear}
                className="block px-4 py-3 hover:bg-bg-hover transition-colors border-b border-border-muted last:border-0"
              >
                <div className="text-sm font-medium text-text-primary truncate">
                  {highlightText(a.title_cn || a.title || '', query)}
                </div>
                <div className="text-xs text-text-muted mt-1 flex items-center gap-2">
                  <span>{a.source}</span>
                  <span>·</span>
                  <span>{(a.published || '').slice(0, 10)}</span>
                  {a.category && <span className="bg-bg-secondary px-1.5 py-0.5 rounded text-[10px]">{a.category}</span>}
                  {a.is_paper && (
                    <span className="text-accent/70"><FontAwesomeIcon icon={ICON.fileLines} /></span>
                  )}
                </div>
              </a>
            ))
          )}
        </div>
      )}
    </div>
  )
}

function highlightText(text: string, query: string) {
  if (!query || query.length < 2) return text
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const parts = text.split(new RegExp(`(${escaped})`, 'gi'))
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase()
      ? <mark key={i} className="bg-accent/30 text-accent rounded-sm px-0.5">{part}</mark>
      : part
  )
}

function useSearch() {
  const [query, setQuery] = useState('')
  const [index, setIndex] = useState<Article[]>([])

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/search_index.json`)
      .then(r => r.json())
      .then(setIndex)
      .catch(() => {})
  }, [])

  const results = useMemo(() => {
    if (query.length < 2 || !index.length) return []
    const q = query.toLowerCase()
    return index
      .map(a => {
        let score = 0
        const t = (a.title_cn || a.title || '').toLowerCase()
        const s = (a.summary_cn || a.summary || '').toLowerCase()
        const src = (a.source || '').toLowerCase()
        if (t.includes(q)) score += 10
        if (t.startsWith(q)) score += 5
        if (s.includes(q)) score += 3
        if (src.includes(q)) score += 2
        return { ...a, _score: score }
      })
      .filter(a => a._score > 0)
      .sort((a, b) => b._score - a._score)
      .slice(0, 12)
  }, [query, index])

  return { query, setQuery, results, clear: () => setQuery('') }
}

// ── Article Card ──
function cleanSummary(raw: string): string {
  // Strip arXiv boilerplate: "arXiv:XXXXvX Announce Type: new \nAbstract: "
  return raw
    .replace(/^arXiv:[\d.]+v?\d*\s*(Announce Type:\s*\w+\s*)?\n?Abstract:\s*/i, '')
    .slice(0, 280)
}

function ArticleCard({ article, index = 0, lang = 'zh' }: { article: Article; index?: number; lang?: string }) {
  const isEn = lang === 'en'
  const title = isEn ? (article.title || article.title_cn) : (article.title_cn || article.title)
  // EN: use cleaned original English abstract; ZH: use AI-generated Chinese summary
  const summary = isEn
    ? (article.summary ? cleanSummary(article.summary) : (article.summary_cn ? article.summary_cn.slice(0, 280) : ''))
    : (article.summary_cn || (article.summary ? cleanSummary(article.summary) : ''))
  // EN: hide why_it_matters (pipeline only generates Chinese); ZH: show it
  const why = !isEn && article.why_it_matters ? article.why_it_matters : null

  const handleClick = () => {
    try {
      const h = JSON.parse(localStorage.getItem('ai_read') || '[]')
      const filtered = h.filter((x: { link: string }) => x.link !== article.link)
      filtered.unshift({ link: article.link, title: (title || '').slice(0, 80), ts: Date.now() })
      localStorage.setItem('ai_read', JSON.stringify(filtered.slice(0, 50)))
    } catch {}
  }

  const catIcon = CATEGORY_ICONS[article.category] || DEFAULT_CATEGORY_ICON

  return (
    <ScrollReveal index={index}>
      <div className="article-item bg-bg-card border border-border-muted rounded-xl p-4 hover:border-accent/20 hover:bg-bg-elevated hover:shadow-[0_0_20px_-8px_rgba(108,92,231,0.1)] transition-all duration-300 group">
        <div className="flex items-start gap-2">
          <a
            href={article.link}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleClick}
            className="text-[15px] font-medium text-text-primary group-hover:text-accent transition-colors leading-snug flex-1"
          >
            {article.is_paper && (
              <FontAwesomeIcon icon={ICON.fileLines} className="mr-1.5 text-accent/60 text-xs" />
            )}
            {title}
          </a>
        </div>
        <div className="flex items-center gap-2 mt-1.5 text-xs text-text-muted">
          {article.category && (
            <FontAwesomeIcon icon={catIcon} className="mr-1 text-text-muted/60" />
          )}
          <span className="text-text-secondary">{article.source}</span>
          <span>·</span>
          <span>{article.published}</span>
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
}

// ── Agent & MCP Tools Weekly ──
function AgentTools({ data, locale }: { data: AgentToolsData; locale: Locale }) {
  const [expanded, setExpanded] = useState<number | null>(null)

  const typeBadge = (type: string) => {
    switch (type) {
      case 'mcp-server': return { label: t(T.agentTypeMCP, locale), className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' }
      case 'agent-tool': return { label: t(T.agentTypeTool, locale), className: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' }
      case 'agent-skill': return { label: t(T.agentTypeSkill, locale), className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' }
      default: return { label: type, className: 'bg-bg-secondary text-text-muted' }
    }
  }

  return (
    <FadeIn delay={0.09}>
      <section>
        <div className="flex items-center gap-2 mb-3">
          <FontAwesomeIcon icon={ICON.robot} className="text-accent" />
          <h2 className="text-lg font-semibold text-text-primary">
            {t(T.agentTools, locale)}
          </h2>
          {data.stats && (
            <div className="flex items-center gap-1.5 ml-auto">
              <span className="text-[11px] px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
                MCP {data.stats.total_mcp}
              </span>
              <span className="text-[11px] px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400">
                Agent {data.stats.total_agent}
              </span>
              <span className="text-[11px] px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400">
                Skill {data.stats.total_skill}
              </span>
            </div>
          )}
        </div>
        <div className="space-y-2">
          {data.tools.map((tool, i) => {
            const isOpen = expanded === i
            const badge = typeBadge(tool.type)
            return (
              <ScrollReveal key={tool.full_name} index={i}>
                <div className="bg-bg-card border border-border-muted rounded-xl overflow-hidden hover:border-accent/20 transition-all duration-300">
                  <button
                    onClick={() => setExpanded(isOpen ? null : i)}
                    className="w-full text-left p-4 flex items-start gap-3"
                  >
                    <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-accent-muted flex items-center justify-center text-sm font-bold text-accent tabular-nums">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-[15px] text-text-primary">
                          <span className="text-text-muted font-normal">{tool.owner}/</span>
                          {tool.name}
                        </span>
                        <span className={`text-[11px] px-1.5 py-0.5 rounded ${badge.className}`}>
                          {badge.label}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-text-secondary line-clamp-1">{tool.description}</p>
                      <div className="mt-1.5 flex items-center gap-3 text-xs text-text-muted">
                        <span className="flex items-center gap-1">
                          <FontAwesomeIcon icon={ICON.star} className="text-amber text-[10px]" />
                          {tool.stars_formatted}
                        </span>
                        <span>Fork {(tool.forks ?? 0).toLocaleString()}</span>
                      </div>
                    </div>
                    <FontAwesomeIcon
                      icon={ICON.chevronDown}
                      className={`flex-shrink-0 mt-1 text-text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                    />
                  </button>
                  <div className={`overflow-hidden transition-all duration-300 ${isOpen ? 'max-h-48 opacity-100' : 'max-h-0 opacity-0'}`}>
                    <div className="px-4 pb-4 pl-14">
                      <div className="text-xs text-accent/80 bg-accent-muted border border-accent/10 rounded-lg px-3 py-2.5 leading-relaxed">
                        <FontAwesomeIcon icon={ICON.robot} className="mr-1.5 text-accent/60" />
                        {tool.summary}
                      </div>
                      <a
                        href={tool.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 mt-2 text-xs text-accent hover:text-accent-hover transition-colors"
                      >
                        {t(T.viewOnGithub, locale)}
                        <FontAwesomeIcon icon={ICON.arrowRight} className="text-[10px]" />
                      </a>
                    </div>
                  </div>
                </div>
              </ScrollReveal>
            )
          })}
        </div>
      </section>
    </FadeIn>
  )
}

// ── GithubTop5 ──
function GithubTop5({ data, locale }: { data: Top5Data; locale: Locale }) {
  const [expanded, setExpanded] = useState<number | null>(null)

  return (
    <FadeIn delay={0.08}>
      <section>
        <div className="flex items-center gap-2 mb-3">
          <FontAwesomeIcon icon={ICON.star} className="text-amber" />
          <h2 className="text-lg font-semibold text-text-primary">
            {t(T.githubTop5, locale)}
          </h2>
          <span className="text-xs text-text-muted bg-bg-secondary px-2 py-0.5 rounded-full">
            {t(T.sortedByStars, locale)}
          </span>
        </div>
        <div className="space-y-2">
          {data.repos.map((repo, i) => {
            const isOpen = expanded === i
            return (
              <ScrollReveal key={repo.full_name} index={i}>
                <div className="bg-bg-card border border-border-muted rounded-xl overflow-hidden hover:border-accent/20 transition-all duration-300">
                  <button
                    onClick={() => setExpanded(isOpen ? null : i)}
                    className="w-full text-left p-4 flex items-start gap-3"
                  >
                    <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-accent-muted flex items-center justify-center text-sm font-bold text-accent tabular-nums">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-[15px] text-text-primary">
                          <span className="text-text-muted font-normal">{repo.owner}/</span>
                          {repo.name}
                        </span>
                        {repo.language && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-bg-secondary text-text-muted">{repo.language}</span>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-text-secondary line-clamp-1">{repo.description}</p>
                      <div className="mt-1.5 flex items-center gap-3 text-xs text-text-muted">
                        <span className="flex items-center gap-1">
                          <FontAwesomeIcon icon={ICON.star} className="text-amber text-[10px]" />
                          {repo.stars_formatted}
                        </span>
                        <span>Fork {(repo.forks ?? 0).toLocaleString()}</span>
                      </div>
                    </div>
                    <FontAwesomeIcon
                      icon={ICON.chevronDown}
                      className={`flex-shrink-0 mt-1 text-text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                    />
                  </button>
                  <div className={`overflow-hidden transition-all duration-300 ${isOpen ? 'max-h-48 opacity-100' : 'max-h-0 opacity-0'}`}>
                    <div className="px-4 pb-4 pl-14">
                      <div className="text-xs text-accent/80 bg-accent-muted border border-accent/10 rounded-lg px-3 py-2.5 leading-relaxed">
                        <FontAwesomeIcon icon={ICON.robot} className="mr-1.5 text-accent/60" />
                        {repo.summary}
                      </div>
                      <a
                        href={repo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 mt-2 text-xs text-accent hover:text-accent-hover transition-colors"
                      >
                        {t(T.viewOnGithub, locale)}
                        <FontAwesomeIcon icon={ICON.arrowRight} className="text-[10px]" />
                      </a>
                    </div>
                  </div>
                </div>
              </ScrollReveal>
            )
          })}
        </div>
      </section>
    </FadeIn>
  )
}

// ── Cross-source Events ──
function Events({ data, locale }: { data: EventsData; locale: Locale }) {
  const [expanded, setExpanded] = useState<string | null>(null)

  return (
    <FadeIn delay={0.10}>
      <section>
        <div className="flex items-center gap-2 mb-3">
          <FontAwesomeIcon icon={ICON.globe} className="text-accent" />
          <h2 className="text-lg font-semibold text-text-primary">
            {t(T.eventsTitle, locale)}
          </h2>
          <span className="text-xs text-text-muted bg-bg-secondary px-2 py-0.5 rounded-full">
            {t(T.eventsSubtitle, locale)}
          </span>
          <span className="text-xs text-text-muted ml-auto">
            {data.events.length} clusters · {data.source_articles} {t(T.eventsArticles, locale)}
          </span>
        </div>
        <div className="space-y-2">
          {data.events.map((event) => {
            const isOpen = expanded === event.id
            return (
              <ScrollReveal key={event.id} index={data.events.indexOf(event)}>
                <div className="bg-bg-card border border-border-muted rounded-xl overflow-hidden hover:border-accent/20 transition-all duration-300">
                  <button
                    onClick={() => setExpanded(isOpen ? null : event.id)}
                    className="w-full text-left p-4 flex items-start gap-3"
                  >
                    <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-accent-muted flex items-center justify-center text-sm font-bold text-accent">
                      {event.article_count}
                    </span>
                    <div className="flex-1 min-w-0">
                      <span className="font-medium text-[15px] text-text-primary">{event.title}</span>
                      <div className="mt-1.5 flex items-center gap-3 text-xs text-text-muted">
                        <span>{event.time_range.start} → {event.time_range.end}</span>
                        <span className="flex items-center gap-1 flex-wrap">
                          {event.categories.map((c, j) => (
                            <span key={j} className="bg-bg-secondary px-1.5 py-0.5 rounded text-[10px]">{c}</span>
                          ))}
                        </span>
                      </div>
                    </div>
                    <FontAwesomeIcon
                      icon={ICON.chevronDown}
                      className={`flex-shrink-0 mt-1 text-text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                    />
                  </button>
                  <div className={`overflow-hidden transition-all duration-300 ${isOpen ? 'max-h-80 opacity-100' : 'max-h-0 opacity-0'}`}>
                    <div className="px-4 pb-4 pl-14 space-y-2">
                      {event.sources.length > 0 && (
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {event.sources.map((s, j) => (
                            <span key={j} className="text-[11px] bg-accent-muted text-accent px-2 py-0.5 rounded">{s}</span>
                          ))}
                        </div>
                      )}
                      {event.articles.slice(0, 5).map((a: any) => (
                        <a
                          key={a.id}
                          href={a.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block text-xs text-text-secondary hover:text-accent transition-colors border-l-2 border-border-muted hover:border-accent/50 pl-3 py-1"
                        >
                          [{a.source}] {a.title}
                        </a>
                      ))}
                    </div>
                  </div>
                </div>
              </ScrollReveal>
            )
          })}
        </div>
      </section>
    </FadeIn>
  )
}

// ── Continue Reading ──
function ContinueReading({ locale }: { locale: Locale }) {
  const [items, setItems] = useState<{ link: string; title: string }[]>([])

  useEffect(() => {
    try {
      const h = JSON.parse(localStorage.getItem('ai_read') || '[]')
      setItems(h.slice(0, 5))
    } catch {}
  }, [])

  if (!items.length) return null

  return (
    <FadeIn delay={0.2}>
      <section>
        <h2 className="text-lg font-semibold text-text-primary mb-3 flex items-center gap-2">
          <FontAwesomeIcon icon={ICON.bookOpen} className="text-accent" />
          {t(T.continueReading, locale)}
        </h2>
        <div className="space-y-1">
          {items.map((item, i) => (
            <a
              key={i}
              href={item.link}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-sm text-text-secondary hover:text-accent transition-colors py-1"
            >
              {item.title}
            </a>
          ))}
        </div>
      </section>
    </FadeIn>
  )
}

// ── HomePage ──
const CAT_ORDER: CategoryKey[] = ['AI Lab', 'Paper', '中文媒体', 'Blog', 'Community', 'Discussion']

export function HomePage() {
  const { data, loading, error } = useLatest()
  const { data: trending } = useTrending()
  const { data: top5 } = useTop5()
  const { data: agentTools } = useAgentTools()
  const { data: events } = useEvents()
  const search = useSearch()
  const { locale } = useLocale()

  // ItemList structured data for SEO
  const itemListSchema = useMemo(() => {
    if (!data?.articles?.length) return null
    return {
      '@context': 'https://schema.org',
      '@type': 'ItemList',
      itemListElement: data.articles.slice(0, 20).map((a, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        item: {
          '@type': 'Article',
          url: a.link,
          name: a.title_cn || a.title,
          description: a.summary_cn || a.summary || '',
          datePublished: a.published,
        },
      })),
    }
  }, [data])
  useJsonLd(itemListSchema)

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

  const byCat: Record<string, Article[]> = {}
  for (const a of data.articles) {
    const cat = a.category || 'Other'
    if (!byCat[cat]) byCat[cat] = []
    byCat[cat].push(a)
  }

  return (
    <div className="space-y-8">
      {/* Hero */}
      <FadeIn>
        <div className="text-center py-8">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-text-primary tracking-tight">
            AllOfAI
          </h1>
          <p className="mt-3 text-sm sm:text-base md:text-lg text-text-secondary max-w-2xl mx-auto leading-relaxed">
            {t(T.heroDesc, locale)}
          </p>
          <div className="flex items-center justify-center gap-6 mt-4 text-sm text-text-muted">
            <span className="flex items-center gap-1">
              <FontAwesomeIcon icon={ICON.timeline} />
              {data.scanned_at?.slice(0, 16)}
            </span>
            <span className="flex items-center gap-1">
              <FontAwesomeIcon icon={ICON.satelliteDish} />
              {data.successful_sources}/{data.total_sources} {t(T.sources, locale)}
            </span>
            <span className="flex items-center gap-1">
              <FontAwesomeIcon icon={ICON.news} />
              {data.articles.length} {t(T.curated, locale)}
            </span>
          </div>
          {/* Source tags */}
          <div className="mt-5 flex flex-wrap items-center justify-center gap-2 text-xs text-text-muted">
            {T.sourceTags.map((tag, i) => (
              <span key={i} className="bg-bg-secondary px-2.5 py-1 rounded-full">
                {t(tag, locale)}
              </span>
            ))}
          </div>
          <div className="mt-6 flex justify-center">
            <SearchBar {...search} locale={locale} />
          </div>
        </div>
      </FadeIn>

      {/* GitHub AI Top 5 */}
      {top5 && top5.repos && top5.repos.length > 0 && (
        <GithubTop5 data={top5} locale={locale} />
      )}

      {/* Agent & MCP Tools Weekly */}
      {agentTools && agentTools.tools && agentTools.tools.length > 0 && (
        <AgentTools data={agentTools} locale={locale} />
      )}

      {/* Cross-source Events */}
      {events && events.events && events.events.length > 0 && (
        <Events data={events} locale={locale} />
      )}

      {/* Model Leaderboard Preview */}
      <ModelLeaderboardPreview locale={locale} />

      {/* Articles by category */}
      <StaggerContainer className="space-y-8">
        {[...CAT_ORDER, ...Object.keys(byCat).filter(c => !CAT_ORDER.includes(c as CategoryKey))]
          .filter(cat => byCat[cat])
          .map(cat => {
            const meta = T.categoryMeta[cat] || T.defaultCategory
            const catIcon = CATEGORY_ICONS[cat as CategoryKey] || DEFAULT_CATEGORY_ICON
            const items = byCat[cat]
            return (
              <section key={cat}>
                <FadeIn delay={0.05}>
                  <div className="flex items-center gap-2 mb-3">
                    <FontAwesomeIcon icon={catIcon} className="text-accent" />
                    <h2 className="text-lg font-semibold text-text-primary">{t(meta, locale)}</h2>
                    <span className="text-sm text-text-muted bg-bg-secondary px-2 py-0.5 rounded-full">{items.length}</span>
                  </div>
                </FadeIn>
                <div className="space-y-2">
                  {items.slice(0, 5).map((a, i) => (
                    <ArticleCard key={i} article={a} index={i} lang={locale} />
                  ))}
                  {items.length > 5 && (
                    <Link
                      to={`${locale === 'en' ? '/en' : ''}/category/${encodeURIComponent(cat)}`}
                      className="flex items-center justify-center gap-1.5 py-2.5 text-sm text-accent hover:text-accent-hover bg-bg-secondary/50 hover:bg-bg-secondary rounded-lg transition-all duration-200"
                    >
                      {locale === 'en' ? `View all ${items.length} articles` : `查看全部 ${items.length} 篇`}
                      <FontAwesomeIcon icon={ICON.arrowRight} className="text-xs" />
                    </Link>
                  )}
                </div>
              </section>
            )
          })}
      </StaggerContainer>

      {/* Trending */}
      {trending && trending.repos && trending.repos.length > 0 && (
        <section>
          <FadeIn delay={0.1}>
            <div className="flex items-center gap-2 mb-3">
              <FontAwesomeIcon icon={ICON.fire} className="text-amber" />
              <h2 className="text-lg font-semibold text-text-primary">GitHub Trending · AI/ML</h2>
              {trending.snapshot_at && (
                <span className="text-sm text-text-muted flex items-center gap-1">
                  <FontAwesomeIcon icon={ICON.timeline} />
                  {trending.snapshot_at.slice(0, 10)}
                </span>
              )}
            </div>
          </FadeIn>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {trending.repos.slice(0, 12).map((repo, i) => (
              <ScrollReveal key={i} index={i}>
                <a
                  href={repo.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block bg-bg-card border border-border-muted rounded-xl p-4 hover:border-accent/20 hover:bg-bg-elevated hover:shadow-[0_0_20px_-8px_rgba(108,92,231,0.1)] transition-all duration-300"
                >
                  <div className="font-medium text-sm text-text-primary truncate">
                    <span className="text-text-muted">{repo.repo_full.split('/')[0]}/</span>
                    <strong>{repo.repo_full.split('/')[1]}</strong>
                  </div>
                  <p className="mt-1.5 text-xs text-text-secondary line-clamp-2">{repo.description?.slice(0, 120)}</p>
                  <div className="mt-2 flex items-center gap-3 text-xs text-text-muted">
                    <span className="flex items-center gap-1"><FontAwesomeIcon icon={ICON.star} className="text-amber text-[10px]" /> {repo.stars_today} today</span>
                    <span>{(repo.total_stars ?? 0).toLocaleString()} total</span>
                    {repo.language && <span>{repo.language}</span>}
                    {repo.paper_linked && (
                      <span className="text-accent/70 flex items-center gap-0.5">
                        <FontAwesomeIcon icon={ICON.fileLines} />
                        {t(T.paperTag, locale)}
                      </span>
                    )}
                  </div>
                </a>
              </ScrollReveal>
            ))}
          </div>
        </section>
      )}

      <ContinueReading locale={locale} />
    </div>
  )
}
