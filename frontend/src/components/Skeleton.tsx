import { cn } from '../lib/utils'

function Shimmer({ className }: { className?: string }) {
  return (
    <div className={cn('bg-bg-secondary rounded-lg overflow-hidden relative', className)}>
      <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.8s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-white/[0.03] to-transparent" />
    </div>
  )
}

export function ArticleCardSkeleton() {
  return (
    <div className="bg-bg-card border border-border-muted rounded-xl p-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <Shimmer className="h-5 flex-1" />
        <Shimmer className="h-5 w-5 rounded" />
      </div>
      <div className="flex items-center gap-2">
        <Shimmer className="h-3 w-16" />
        <Shimmer className="h-3 w-20" />
        <Shimmer className="h-3 w-24" />
      </div>
      <Shimmer className="h-10 w-full" />
    </div>
  )
}

export function ArticleListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <ArticleCardSkeleton key={i} />
      ))}
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="text-center py-4">
        <Shimmer className="h-8 w-48 mx-auto" />
        <Shimmer className="h-4 w-32 mx-auto mt-2" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-bg-card border border-border-muted rounded-xl p-4 space-y-2">
            <Shimmer className="h-3 w-16" />
            <Shimmer className="h-7 w-20" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-bg-card border border-border-muted rounded-xl p-5">
          <Shimmer className="h-5 w-32 mb-4" />
          <Shimmer className="h-[260px] w-full" />
        </div>
        <div className="bg-bg-card border border-border-muted rounded-xl p-5">
          <Shimmer className="h-5 w-24 mb-4" />
          <Shimmer className="h-[260px] w-full" />
        </div>
      </div>
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="bg-bg-card border border-border-muted rounded-xl p-5 space-y-3">
      <Shimmer className="h-5 w-32" />
      <Shimmer className="h-4 w-full" />
      <Shimmer className="h-4 w-2/3" />
    </div>
  )
}

export function HomePageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="text-center py-6 space-y-3">
        <Shimmer className="h-9 w-48 mx-auto" />
        <Shimmer className="h-5 w-64 mx-auto" />
        <div className="flex justify-center gap-6 mt-3">
          <Shimmer className="h-4 w-24" />
          <Shimmer className="h-4 w-16" />
          <Shimmer className="h-4 w-20" />
        </div>
        <Shimmer className="h-10 w-72 mx-auto mt-4 rounded-lg" />
      </div>
      <ArticleListSkeleton count={4} />
      <ArticleListSkeleton count={3} />
    </div>
  )
}
