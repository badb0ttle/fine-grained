/**
 * Animations - framer-motion 动画组件库
 * 
 * 功能：提供可复用的页面/元素级动画组件，统一项目中动画风格
 * 
 * 组件清单：
 *   - PageTransition：页面切换动画（fade + 上下滑动，配合 AnimatePresence mode="wait"）
 *   - ScrollReveal：滚动驱动入场动画（元素进入视口时淡入+上移）
 *   - StaggerContainer：子元素交错入场容器（children 按序延迟出场）
 *   - PressEffect：点击缩放反馈（whileTap scale 0.97）
 *   - FadeIn：挂载时淡入+上移（适合 KPI 卡片、统计数据等）
 * 
 * 技术细节：
 *   - 使用 framer-motion Variants 定义多状态动画
 *   - spring 弹簧配置用于 PressEffect（stiffness=260, damping=20）
 *   - ScrollReveal 使用 viewport.once 确保仅触发一次
 */

import { motion, type Variants } from 'framer-motion'
import type { ReactNode } from 'react'

/** Spring 弹簧动画配置（自然感觉的弹性反馈） */
const spring = { type: 'spring' as const, stiffness: 260, damping: 20 }

// ============ PageTransition - 页面切换动画 ============
/** 页面入场/离场动画变体：淡入 + 上下微移 */
export const pageVariants: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15, ease: 'easeIn' } },
}

/** PageTransition - 包裹页面内容的动画容器（配合 AnimatePresence 使用） */
export function PageTransition({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={className}
    >
      {children}
    </motion.div>
  )
}

// ============ ScrollReveal - 滚动驱动入场动画 ============
/** 滚动入场动画变体（hidden → visible，支持级联延迟） */
const revealVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: 'easeOut', delay: i * 0.05 },
  }),
}

/** ScrollReveal - 元素进入视口时触发淡入动画（通过 index 控制级联延迟） */
export function ScrollReveal({ children, index = 0, className = '' }: { children: ReactNode; index?: number; className?: string }) {
  return (
    <motion.div
      variants={revealVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-40px' }}
      custom={index}
      className={className}
    >
      {children}
    </motion.div>
  )
}

// ============ StaggerContainer - 子元素交错入场容器 ============
/** 交错容器动画变体：控制子元素按序延迟出场 */
const staggerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.05 },
  },
}

/** StaggerContainer - 包裹多个子元素，子元素按序交错淡入 */
export function StaggerContainer({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      variants={staggerVariants}
      initial="hidden"
      animate="visible"
      className={className}
    >
      {children}
    </motion.div>
  )
}

// ============ PressEffect - 点击缩放反馈 ============
/** PressEffect - 点击时轻微缩放到 0.97（触觉反馈） */
export function PressEffect({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      whileTap={{ scale: 0.97 }}
      transition={spring}
      className={className}
    >
      {children}
    </motion.div>
  )
}

// ============ FadeIn - 挂载时淡入 ============
/** FadeIn - 组件挂载时淡入 + 上移（适合 KPI 卡片、统计数据展示） */
export function FadeIn({ children, delay = 0, className = '' }: { children: ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: 'easeOut' }}
      className={className}
    >
      {children}
    </motion.div>
  )
}
