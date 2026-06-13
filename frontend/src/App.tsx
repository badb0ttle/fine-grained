import { lazy, Suspense, useEffect } from 'react'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Header, Footer } from './components/Layout'
import { PageTransition } from './components/Animations'
import { ReadingProgress } from './components/ReadingProgress'
import { BackToTop } from './components/BackToTop'
import { ToastProvider } from './components/Toast'
import { AdminGate } from './components/AdminGate'
import ParticleBackground from './components/ParticleBackground'
import { ThemeProvider } from './components/ThemeToggle'

// Lazy-load all pages for code splitting (named exports via .then)
const HomePage        = lazy(() => import('./pages/HomePage').then(m => ({ default: m.HomePage })) as any)
const DashboardPage   = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })) as any)
const LeaderboardPage = lazy(() => import('./pages/LeaderboardPage').then(m => ({ default: m.LeaderboardPage })) as any)
const TimelinePage    = lazy(() => import('./pages/TimelinePage').then(m => ({ default: m.TimelinePage })) as any)
const ClustersPage    = lazy(() => import('./pages/ClustersPage').then(m => ({ default: m.ClustersPage })) as any)
const WeeklyPage      = lazy(() => import('./pages/WeeklyPage').then(m => ({ default: m.WeeklyPage })) as any)
const WeeklyDetailPage = lazy(() => import('./pages/WeeklyDetailPage').then(m => ({ default: m.WeeklyDetailPage })) as any)
const AboutPage = lazy(() => import('./pages/AboutPage').then(m => ({ default: m.AboutPage })) as any)

function PageFallback() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function SpaRedirect() {
  const navigate = useNavigate()

  useEffect(() => {
    const redirect = sessionStorage.getItem('redirect')
    if (redirect) {
      sessionStorage.removeItem('redirect')
      navigate(redirect, { replace: true })
    }
  }, [navigate])

  return null
}

// Inline routes — React Router v7 requires <Route> or <React.Fragment> as direct children of <Routes>
function PageRoutes({ prefix = '' }: { prefix?: string }) {
  return (
    <>
      <Route path={`${prefix}/`} element={<HomePage />} />
      <Route path={`${prefix}/dashboard`} element={<AdminGate><DashboardPage /></AdminGate>} />
      <Route path={`${prefix}/leaderboard`} element={<LeaderboardPage />} />
      <Route path={`${prefix}/timeline`} element={<TimelinePage />} />
      <Route path={`${prefix}/clusters`} element={<ClustersPage />} />
      <Route path={`${prefix}/weekly`} element={<WeeklyPage />} />
      <Route path={`${prefix}/weekly/:date`} element={<WeeklyDetailPage />} />
      <Route path={`${prefix}/about`} element={<AboutPage />} />
    </>
  )
}

function AnimatedRoutes() {
  const location = useLocation()

  return (
    <AnimatePresence mode="wait">
      <PageTransition key={location.pathname}>
        <SpaRedirect />
        <Suspense fallback={<PageFallback />}>
          <Routes location={location}>
            <PageRoutes prefix="" />
            <PageRoutes prefix="/en" />
          </Routes>
        </Suspense>
      </PageTransition>
    </AnimatePresence>
  )
}

export default function App() {
  return (
    <ThemeProvider>
    <ToastProvider>
      <div className="min-h-dvh flex flex-col relative">
        <ParticleBackground />
        <ReadingProgress />
        <Header />
        <main className="flex-1 mx-auto w-full max-w-6xl px-4 pt-20 pb-8 relative z-10">
          <AnimatedRoutes />
        </main>
        <Footer />
        <BackToTop />
      </div>
    </ToastProvider>
    </ThemeProvider>
  )
}
