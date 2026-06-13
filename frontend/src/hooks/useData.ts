import { useEffect, useState } from 'react'
import type { LatestData, Stats, TrendingData, ClusterData, Top5Data } from '../types'

const DATA_BASE = import.meta.env.BASE_URL

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${DATA_BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export function useLatest() {
  const [data, setData] = useState<LatestData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchJSON<LatestData>('data/latest.json')
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
    fetchJSON<Stats>('data/stats.json')
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
    fetchJSON<TrendingData>('data/trending.json')
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
    fetchJSON<ClusterData>('data/clusters.json')
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
    fetchJSON<Top5Data>('data/github_top5.json')
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { data, loading }
}
