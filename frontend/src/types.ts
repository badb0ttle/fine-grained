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

export interface ClusterGroup {
  id: number
  title: string
  keywords: string[]
  count: number
  color: string
}

export interface ClusterPoint {
  id: number
  title: string
  source: string
  published: string
  link: string
  score: number
  x: number
  y: number
  cluster: number
}

export interface ClusterData {
  generated_at: string
  total_articles: number
  n_clusters: number
  clusters: ClusterGroup[]
  points: ClusterPoint[]
}

export interface LatestData {
  scanned_at: string
  successful_sources: number
  total_sources: number
  articles: Article[]
}

export type CategoryKey = 'AI Lab' | 'Paper' | '中文媒体' | 'Blog' | 'Community' | 'Discussion' | string

// GitHub Top 5
export interface Top5Repo {
  full_name: string
  name: string
  owner: string
  description: string
  url: string
  stars: number
  stars_formatted: string
  forks: number
  language: string
  topics: string[]
  summary: string
  updated_at: string
}

export interface Top5Data {
  generated_at: string
  repos: Top5Repo[]
}

// Model Leaderboard
export interface LeaderboardModel {
  id: string
  name: string
  provider: string
  description: string
  created: number
  context_length: number
  context_display: string
  max_output: string | null
  max_output_raw: number | null
  price_input: string
  price_output: string
  price_input_raw: number
  price_output_raw: number
  tags: string[]
  modality: string
  rank: number
  scores: ModelScores | null
}

export interface ModelScores {
  intelligence?: number
  coding?: number
  agentic?: number
  best_elo?: number
  best_elo_category?: string
  elo_categories?: EloCategory[]
}

export interface EloCategory {
  category: string
  elo: number | null
  win_rate: number | null
  rank: number | null
}

export interface LeaderboardData {
  updated_at: string
  total_models: number
  source: string
  models: LeaderboardModel[]
}

// Agent & MCP Tools
export interface AgentTool {
  full_name: string
  name: string
  owner: string
  description: string
  url: string
  stars: number
  forks: number
  language: string
  topics: string[]
  summary: string
  updated_at: string
  stars_formatted: string
  type: 'mcp-server' | 'agent-tool' | 'agent-skill'
  type_label: string
}

export interface AgentToolsData {
  generated_at: string | null
  generated_week: string | null
  tools: AgentTool[]
  stats: {
    total_mcp: number
    total_agent: number
    total_skill: number
  }
}

// Event Clusters
export interface EventArticle {
  id: number
  title: string
  source: string
  category: string
  link: string
  published: string
}

export interface EventCluster {
  id: string
  title: string
  sources: string[]
  categories: string[]
  time_range: { start: string; end: string }
  article_count: number
  articles: EventArticle[]
}

export interface EventsData {
  generated_at: string
  source_articles: number
  events: EventCluster[]
}

