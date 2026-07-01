/**
 * Skeleton - 骨架屏组件集合
 * 
 * 功能：在数据加载期间显示占位骨架动画，提升感知性能
 * 
 * 组件清单：
 *   - Shimmer：基础闪烁效果（CSS animation 驱动，从左到右扫光）
 *   - ArticleCardSkeleton：单篇文章卡片骨架屏
 *   - ArticleListSkeleton：文章列表骨架屏（n 个 ArticleCardSkeleton）
 *   - DashboardSkeleton：仪表盘页面骨架屏（统计卡片 + 图表）
 *   - CardSkeleton：通用卡片骨架屏
 *   - HomePageSkeleton：首页骨架屏（标题 + 两段文章列表）
 * 
 * 动画原理：
 *   - 使用 Tailwind CSS 自定义 keyframe [shimmer]（translateX 从 -100% 到 100%）
 *   - 伪元素 overlay 带渐变背景（transparent → white/3% → transparent）
 *   - animated 1.8s ease-in-out infinite 循环
 */

import { cn } from '../lib/utils'

/** Shimmer - 基础骨架屏条（带扫光动画的占位矩形） */
function Shimmer({ className }: { className?: string }) {
  return (
    <div className={cn('bg-bg-secondary rounded-lg overflow-hidden relative', className)}>
      {/* 扫光效果层：白色半透明渐变从左到右循环移动 */}
      <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.8s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-white/[0.03] to-transparent" />
    </div>
  )
}

/** ArticleCardSkeleton - 文章卡片骨架屏 */
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

/** ArticleListSkeleton - 文章列表骨架屏（默认 5 条） */
export function ArticleListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <ArticleCardSkeleton key={i} />
      ))}
    </div>
  )
}

/** DashboardSkeleton - 仪表盘页面骨架屏（标题 + 4 统计卡 + 2 图表区域） */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="text-center py-4">
        <Shimmer className="h-8 w-48 mx-auto" />
        <Shimmer className="h-4 w-32 mx-auto mt-2" />
      </div>
      {/* 统计卡片行（4 列） */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-bg-card border border-border-muted rounded-xl p-4 space-y-2">
            <Shimmer className="h-3 w-16" />
            <Shimmer className="h-7 w-20" />
          </div>
        ))}
      </div>
      {/* 图表区域（双列） */}
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

/** CardSkeleton - 通用卡片骨架屏 */
export function CardSkeleton() {
  return (
    <div className="bg-bg-card border border-border-muted rounded-xl p-5 space-y-3">
      <Shimmer className="h-5 w-32" />
      <Shimmer className="h-4 w-full" />
      <Shimmer className="h-4 w-2/3" />
    </div>
  )
}

/** HomePageSkeleton - 首页骨架屏（标题区 + 两段文章列表） */
export function HomePageSkeleton() {
  return (
    <div className="space-y-6">
      {/* 首页标题区 */}
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
      {/* 文章列表骨架 */}
      <ArticleListSkeleton count={4} />
      <ArticleListSkeleton count={3} />
    </div>
  )
}
