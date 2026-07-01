/**
 * LeaderboardPage - 模型排行榜页面（薄封装）
 * 
 * 页面功能：直接渲染 ModelLeaderboard 全页组件，提供完整的 AI 模型排行榜
 *          （含搜索、分类 Tab 筛选、能力对比柱状图）
 * 
 * 路由路径：/leaderboard
 * 
 * 数据来源：由 ModelLeaderboard 组件内部通过 useLeaderboard() hook 获取
 * 
 * Props：无
 */

import { ModelLeaderboard } from '../components/ModelLeaderboard'

/**
 * LeaderboardPage - 模型排行榜页
 * 纯代理组件，所有逻辑在 ModelLeaderboard 中
 */
export function LeaderboardPage() {
  return <ModelLeaderboard />
}
