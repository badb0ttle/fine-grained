/**
 * Toast - 全局通知提示组件（ToastContext + ToastProvider + useToast Hook）
 * 
 * 功能：
 *   - ToastProvider：全局通知 Context Provider，包裹在 App 内部
 *   - useToast() Hook：获取 toast 函数，任意组件可调用 toast(message, type)
 *   - 支持三种类型：success（绿色）/ error（红色）/ info（默认）
 *   - 自动消失：每条通知 2.5 秒后自动移除
 *   - 动画：framer-motion AnimatePresence 入场/离场动画（滑入 + 缩放）
 *   - 最多同时显示 5 条（超出后移除最早的）
 *   - 手动关闭：每条通知有关闭按钮
 *   - 固定定位：右下角 fixed 容器（pointer-events-none 容器 + pointer-events-auto 通知）
 * 
 * 导出：
 *   - ToastProvider：包裹应用的 Provider
 *   - useToast()：获取 toast 函数的 Hook
 */

import { useState, useCallback, createContext, useContext, type ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCheck, faXmark } from '@fortawesome/free-solid-svg-icons'
import { cn } from '../lib/utils'

/** 通知类型：success / error / info */
type ToastType = 'success' | 'error' | 'info'

/** 单条通知的数据结构 */
interface Toast {
  id: number          // 唯一标识
  message: string     // 通知文案
  type: ToastType     // 通知类型（决定颜色和图标）
}

/** ToastContext 的值类型 */
interface ToastCtx {
  toast: (message: string, type?: ToastType) => void
}

/** 创建 ToastContext，默认 toast 为空函数 */
const ToastContext = createContext<ToastCtx>({ toast: () => {} })

/** useToast Hook：获取 toast 函数 */
export function useToast() {
  return useContext(ToastContext)
}

/** 全局自增 ID 计数器（用于生成通知唯一标识） */
let nextId = 0

/** ToastProvider - 全局通知 Provider */
export function ToastProvider({ children }: { children: ReactNode }) {
  /** toasts：当前显示的通知列表 */
  const [toasts, setToasts] = useState<Toast[]>([])

  /** add：添加新通知（最多保留 5 条，2.5 秒后自动移除） */
  const add = useCallback((message: string, type: ToastType = 'info') => {
    const id = nextId++
    setToasts(prev => [...prev.slice(-4), { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 2500)
  }, [])

  /** remove：手动移除指定通知（点击关闭按钮） */
  const remove = (id: number) => setToasts(prev => prev.filter(t => t.id !== id))

  return (
    <ToastContext.Provider value={{ toast: add }}>
      {children}

      {/* 通知容器：固定在右下角，pointer-events-none 避免阻挡交互 */}
      <div className="fixed bottom-20 right-6 z-[70] flex flex-col gap-2 pointer-events-none">
        <AnimatePresence>
          {toasts.map(t => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: 40, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 40, scale: 0.95 }}
              className={cn(
                'pointer-events-auto flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium backdrop-blur-md shadow-xl border',
                t.type === 'success' && 'bg-green/15 border-green/30 text-green',
                t.type === 'error' && 'bg-red/15 border-red/30 text-red',
                t.type === 'info' && 'bg-bg-elevated/90 border-border-default text-text-primary',
              )}
            >
              {/* 类型图标（success = 勾，error = 叉，info = 勾） */}
              <FontAwesomeIcon
                icon={t.type === 'success' ? faCheck : t.type === 'error' ? faXmark : faCheck}
                className="text-xs"
              />
              {t.message}
              {/* 手动关闭按钮 */}
              <button
                onClick={() => remove(t.id)}
                className="ml-1 opacity-50 hover:opacity-100 transition-opacity"
              >
                <FontAwesomeIcon icon={faXmark} className="text-[10px]" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
