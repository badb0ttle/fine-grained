/**
 * ReadingProgress - 阅读进度条（页面顶部水平进度指示器）
 * 
 * 功能：
 *   - 使用 framer-motion 的 useScroll() 监听页面滚动进度
 *   - 通过 useSpring 实现平滑过渡动画（弹性缓动）
 *   - 固定定位在页面顶部 (z-60)，2px 高度渐变色彩条
 *   - origin-left 变换原点（从左到右展开）
 * 
 * 视觉效果：
 *   - 渐变色：accent（紫色）→ blue（蓝色）→ pink（粉色）
 *   - 始终可见但不阻挡页面交互
 */

import { motion, useScroll, useSpring } from 'framer-motion'

export function ReadingProgress() {
  /** scrollYProgress：页面滚动进度（0~1），由 framer-motion 内部监听 scroll 事件 */
  const { scrollYProgress } = useScroll()
  /** scaleX：spring 过渡后的平滑值（stiffness=100 弹簧刚度, damping=30 阻尼） */
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30, restDelta: 0.001 })

  return (
    <motion.div
      className="fixed top-0 left-0 right-0 z-[60] h-[2px] origin-left bg-gradient-to-r from-accent via-blue to-pink"
      style={{ scaleX }}
    />
  )
}
