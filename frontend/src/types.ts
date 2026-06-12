export interface Article {
  title: string
  title_cn?: string
  link: string
  source: string
  published: string
  summary?: string
  summary_cn?: string
  category: string
  score?: number
  why_it_matters?: string
  is_paper?: boolean
}

export interface Stats {
  generated_at: string
  daily_trends: DailyTrend[]
  source_health: SourceHealth[]
  score_distribution: Record<string, number>
  category_distribution: Record<string, number>
  top_articles: TopArticle[]
  keyword_trends?: {
    keywords: KeywordTrend[]
  }
}

export interface DailyTrend {
  date: string
  total_articles: number
  new_articles: number
  curated_count: number
}

export interface SourceHealth {
  name: string
  status: 'healthy' | 'degraded' | 'error'
  category: string
  last_success: string
}

export interface TopArticle {
  title: string
  score: number
  source: string
}

export interface KeywordTrend {
  keyword: string
  change_pct: number
  direction: 'surging' | 'rising' | 'falling' | 'declining' | 'stable'
}

export interface TrendingRepo {
  repo_full: string
  url: string
  description: string
  language: string
  stars_today: number
  total_stars: number
  paper_linked: boolean
}

export interface TrendingData {
  snapshot_at: string
  repos: TrendingRepo[]
}

export interface ClusterData {
  clusters: Cluster[]
}

export interface Cluster {
  id: string
  label: string
  keywords: string[]
  count: number
  articles: Article[]
}

export interface LatestData {
  scanned_at: string
  successful_sources: number
  total_sources: number
  articles: Article[]
}

export type CategoryKey = 'AI Lab' | 'Paper' | '中文媒体' | 'Blog' | 'Community' | 'Discussion' | string
