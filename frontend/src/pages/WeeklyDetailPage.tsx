import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { ICON } from '../lib/icons'
import { FadeIn } from '../components/Animations'
import { CardSkeleton } from '../components/Skeleton'

export function WeeklyDetailPage() {
  const { date } = useParams<{ date: string }>()
  const [html, setHtml] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!date) return
    const url = `${import.meta.env.BASE_URL}data/weekly/${date}.html`
    fetch(url)
      .then(r => {
        if (!r.ok) throw new Error('Not found')
        return r.text()
      })
      .then(raw => {
        // Extract title for the document
        const titleMatch = raw.match(/<title>(.*?)<\/title>/)
        if (titleMatch) document.title = titleMatch[1]

        // Extract body content, strip style/head tags
        let body = raw
        // Remove everything before <body>
        const bodyStart = body.indexOf('<body>')
        const bodyEnd = body.indexOf('</body>')
        if (bodyStart >= 0 && bodyEnd >= 0) {
          body = body.slice(bodyStart + 6, bodyEnd)
        }
        // Remove <style> blocks
        body = body.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
        // Remove inline style attributes
        body = body.replace(/\sstyle="[^"]*"/gi, '')
        // Remove class attributes (old styling)
        body = body.replace(/\sclass="[^"]*"/gi, '')
        // Fix back-link to use React router
        body = body.replace(/href="index\.html"/g, 'href="/weekly"')
        // Wrap headings and paragraphs with theme classes
        body = body
          .replace(/<h1>/g, '<h1 class="text-2xl font-bold text-text-primary mt-4 mb-3">')
          .replace(/<h2>/g, '<h2 class="text-lg font-semibold text-accent mt-6 mb-2">')
          .replace(/<p>/g, '<p class="text-text-secondary leading-relaxed my-3">')
          .replace(/<strong>/g, '<strong class="text-text-primary font-semibold">')
          .replace(/<a /g, '<a class="text-accent hover:text-accent-hover transition-colors" ')

        setHtml(body)
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [date])

  if (loading) {
    return (
      <div className="space-y-4 pt-8">
        <CardSkeleton />
      </div>
    )
  }

  if (error || !html) {
    return (
      <div className="text-center py-20">
        <FontAwesomeIcon icon={ICON.inbox} className="text-4xl text-text-muted mb-4" />
        <p className="text-text-muted mb-4">找不到该周报</p>
        <Link to="/weekly" className="text-accent hover:text-accent-hover transition-colors text-sm">
          ← 返回周报列表
        </Link>
      </div>
    )
  }

  return (
    <FadeIn>
      <div className="max-w-3xl mx-auto pt-4 pb-12">
        <Link
          to="/weekly"
          className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-accent transition-colors mb-6"
        >
          <FontAwesomeIcon icon={ICON.arrowRight} className="rotate-180 text-xs" />
          返回周报列表
        </Link>
        <article
          className="prose-custom"
          dangerouslySetInnerHTML={{ __html: html }}
        />
        <Link
          to="/weekly"
          className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-accent transition-colors mt-8"
        >
          <FontAwesomeIcon icon={ICON.arrowRight} className="rotate-180 text-xs" />
          返回周报列表
        </Link>
      </div>
    </FadeIn>
  )
}
