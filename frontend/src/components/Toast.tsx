import { useState, useCallback, createContext, useContext, type ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCheck, faXmark } from '@fortawesome/free-solid-svg-icons'
import { cn } from '../lib/utils'

type ToastType = 'success' | 'error' | 'info'

interface Toast {
  id: number
  message: string
  type: ToastType
}

interface ToastCtx {
  toast: (message: string, type?: ToastType) => void
}

const ToastContext = createContext<ToastCtx>({ toast: () => {} })

export function useToast() {
  return useContext(ToastContext)
}

let nextId = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const add = useCallback((message: string, type: ToastType = 'info') => {
    const id = nextId++
    setToasts(prev => [...prev.slice(-4), { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 2500)
  }, [])

  const remove = (id: number) => setToasts(prev => prev.filter(t => t.id !== id))

  return (
    <ToastContext.Provider value={{ toast: add }}>
      {children}
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
              <FontAwesomeIcon
                icon={t.type === 'success' ? faCheck : t.type === 'error' ? faXmark : faCheck}
                className="text-xs"
              />
              {t.message}
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
