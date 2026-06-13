import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { ICON } from '../lib/icons'
import { FadeIn, ScrollReveal } from '../components/Animations'
import { CardSkeleton } from '../components/Skeleton'

interface WeeklyReport {
  date: string
  title: string
  summary: string
  url: string
}

export function WeeklyPage() {
  const [reports, setReports] = useState<WeeklyReport[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/weekly/index.json`)
      .then(r => r.json())
      .then(data => setReports(data.reports || []))
      .catch(() => {
        setReports([
          {
            date: '2026-06-02',
            title: '本周 AI 大事记',
            summary: 'MiniMax M3 · Agent 规模化 · 基准测试危机 · 记忆机制',
            url: '',
          },
        ])
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="space-y-4">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <FadeIn>
        <div className="text-center py-4">
          <h1 className="text-3xl font-bold text-text-primary flex items-center justify-center gap-2">
            <FontAwesomeIcon icon={ICON.weekly} className="text-accent" />
            每周 AI 大事记
          </h1>
          <p className="mt-2 text-text-muted text-sm">深度行业分析简报</p>
        </div>
      </FadeIn>

      {reports.length === 0 ? (
        <div className="text-center py-20">
          <FontAwesomeIcon icon={ICON.inbox} className="text-4xl text-text-muted mb-4" />
          <p className="text-text-muted">暂无周报</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((report, i) => (
            <ScrollReveal key={report.date} index={i}>
              <Link
                to={`/weekly/${report.date}`}
                className="block bg-bg-card border border-border-muted rounded-xl p-5 hover:border-accent/20 hover:bg-bg-elevated hover:shadow-[0_0_20px_-8px_rgba(108,92,231,0.1)] transition-all duration-300 group"
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-accent-muted flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                    <FontAwesomeIcon icon={ICON.weekly} className="text-accent text-lg" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h2 className="text-base font-semibold text-text-primary group-hover:text-accent transition-colors">
                      {report.title} ({report.date})
                    </h2>
                    <p className="mt-1 text-sm text-text-secondary">{report.summary}</p>
                  </div>
                  <div className="flex-shrink-0 self-center">
                    <FontAwesomeIcon icon={ICON.arrowRight} className="text-text-muted group-hover:text-accent group-hover:translate-x-1 transition-all" />
                  </div>
                </div>
              </Link>
            </ScrollReveal>
          ))}
        </div>
      )}
    </div>
  )
}
