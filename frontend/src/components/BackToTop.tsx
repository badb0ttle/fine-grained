/**
 * BackToTop - 回到顶部浮动按钮
 * 
 * 功能：
 *   - 页面滚动超过 400px 时显示（framer-motion AnimatePresence 控制显隐动画）
 *   - 点击后平滑滚动到页面顶部（behavior: 'smooth'）
 *   - 固定定位右下角 (z-50)，毛玻璃背景 + 带阴影
 *   - 滚动事件使用 passive 监听优化性能
 * 
 * 动画：
 *   - 入场：opacity 0→1 + scale 0.8→1
 *   - 离场：opacity 1→0 + scale 1→0.8
 */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowUp } from '@fortawesome/free-solid-svg-icons'

export function BackToTop() {
  /** visible：是否显示按钮（scrollY > 400 时显示） */
  const [visible, setVisible] = useState(false)

  /** 监听 scroll 事件（passive 优化性能） */
  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 400)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <AnimatePresence>
      {visible && (
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="fixed bottom-6 right-6 z-50 w-10 h-10 rounded-xl bg-accent/90 hover:bg-accent text-white shadow-lg shadow-accent/20 flex items-center justify-center transition-colors backdrop-blur-sm"
          aria-label="回到顶部"
        >
          <FontAwesomeIcon icon={faArrowUp} className="text-sm" />
        </motion.button>
      )}
    </AnimatePresence>
  )
}
