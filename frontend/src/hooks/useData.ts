import { useEffect, useState, useCallback } from 'react'
import type { LatestData, Stats, TrendingData, ClusterData, Top5Data, LeaderboardData, Article } from '../types'

// ── Mode configuration ──
const API_MODE: boolean = import.meta.env.VITE_API_MODE === 'true'
const API_BASE: string = import.meta.env.VITE_API_BASE || 'https://api.hjhai.xyz'
const DATA_BASE = import.meta.env.BASE_URL

// ── Unified fetcher ──
async function fetchJSON<T>(path: string): Promise<T> {
  const url = API_MODE ? `${API_BASE}${path}` : `${DATA_BASE}data/${path}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

async function fetchAPI<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

// ── Data hooks ──

export function useLatest() {
  const [data, setData] = useState<LatestData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const path = API_MODE ? '/latest' : 'latest.json'
    fetchJSON<LatestData>(path)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return { data, loading, error }
}

export function useStats() {
  const [data, setData] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const path = API_MODE ? '/stats' : 'stats.json'
    fetchJSON<Stats>(path)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return { data, loading, error }
}

export function useTrending() {
  const [data, setData] = useState<TrendingData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const path = API_MODE ? '/trending' : 'trending.json'
    fetchJSON<TrendingData>(path)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { data, loading }
}

export function useClusters() {
  const [data, setData] = useState<ClusterData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const path = API_MODE ? '/clusters' : 'clusters.json'
    fetchJSON<ClusterData>(path)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { data, loading }
}

export function useTop5() {
  const [data, setData] = useState<Top5Data | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Top5 is now served via /trending endpoint
    const path = API_MODE ? '/trending' : 'github_top5.json'
    fetchJSON<Top5Data>(path)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { data, loading }
}

export function useLeaderboard() {
  const [data, setData] = useState<LeaderboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const path = API_MODE ? '/model-leaderboard' : 'model_leaderboard.json'
    fetchJSON<LeaderboardData>(path)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { data, loading }
}

// ── API-only hooks ──

export function useSearch() {
  const [results, setResults] = useState<Article[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const search = useCallback(async (query: string, limit = 20) => {
    if (!query.trim()) {
      setResults([])
      setTotal(0)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAPI<{ articles: Article[]; total: number }>(
        `/search?q=${encodeURIComponent(query)}&limit=${limit}`
      )
      setResults(data.articles)
      setTotal(data.total)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { results, total, loading, error, search }
}

export function useWeekly() {
  const [weeks, setWeeks] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAPI<{ weeks: string[] }>('/weekly')
      .then(data => setWeeks(data.weeks || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { weeks, loading }
}
