import { useClusters } from '../hooks/useData'

const CLUSTER_COLORS = [
  '#6C5CE7', '#00b894', '#74b9ff', '#f0a050', '#fd79a8',
  '#e17055', '#a29bfe', '#55efc4', '#81ecec', '#fab1a0',
]

export function ClustersPage() {
  const { data, loading } = useClusters()

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    )
  }

  if (!data || !data.clusters || !data.clusters.length) {
    return (
      <div className="text-center py-20">
        <p className="text-4xl mb-4">🗺️</p>
        <p className="text-text-muted">暂无聚类数据</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-center py-4">
        <h1 className="text-3xl font-bold text-text-primary">🗺️ 聚类分析</h1>
        <p className="mt-2 text-text-muted text-sm">文章主题聚类 · {data.clusters.length} 个聚类</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.clusters.map((cluster, i) => (
          <div
            key={cluster.id}
            className="bg-bg-card border border-border-muted rounded-xl p-5 hover:border-accent/20 transition-all"
          >
            <div className="flex items-center gap-2 mb-3">
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: CLUSTER_COLORS[i % CLUSTER_COLORS.length] }}
              />
              <h2 className="text-base font-semibold text-text-primary">{cluster.label}</h2>
              <span className="text-xs text-text-muted bg-bg-secondary px-2 py-0.5 rounded-full">
                {cluster.count} 篇
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
            {cluster.articles && cluster.articles.length > 0 && (
              <div className="space-y-1.5">
                {cluster.articles.slice(0, 5).map((a, j) => (
                  <a
                    key={j}
                    href={a.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-xs text-text-secondary hover:text-accent transition-colors truncate"
                  >
                    {a.title_cn || a.title}
                  </a>
                ))}
                {cluster.articles.length > 5 && (
                  <p className="text-xs text-text-muted">
                    ... 还有 {cluster.articles.length - 5} 篇
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
