import { motion, type Variants } from 'framer-motion'
import type { ReactNode } from 'react'

// Spring config for natural feel
const spring = { type: 'spring' as const, stiffness: 260, damping: 20 }

// Page transition — fade + slight slide up
export const pageVariants: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15, ease: 'easeIn' } },
}

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

// Scroll reveal — fades in on scroll with configurable delay
const revealVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: 'easeOut', delay: i * 0.05 },
  }),
}

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

// Stagger container — animates children sequentially
const staggerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.05 },
  },
}

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

// Press effect — subtle scale on tap
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

// Fade in on mount (for KPI cards, stats, etc.)
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
