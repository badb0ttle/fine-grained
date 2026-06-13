import { lazy, Suspense, useEffect } from 'react'
import { useNavigate, useLocation, useRoutes } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Header, Footer } from './components/Layout'
import { PageTransition } from './components/Animations'
import { ReadingProgress } from './components/ReadingProgress'
import { BackToTop } from './components/BackToTop'
import { ToastProvider } from './components/Toast'
import { AdminGate } from './components/AdminGate'
import ParticleBackground from './components/ParticleBackground'
import { ThemeProvider } from './components/ThemeToggle'

// Lazy-load all pages for code splitting
const HomePage        = lazy(() => import('./pages/HomePage').then(m => ({ default: m.HomePage })) as any)
const DashboardPage   = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })) as any)
const LeaderboardPage = lazy(() => import('./pages/LeaderboardPage').then(m => ({ default: m.LeaderboardPage })) as any)
const TimelinePage    = lazy(() => import('./pages/TimelinePage').then(m => ({ default: m.TimelinePage })) as any)
const ClustersPage    = lazy(() => import('./pages/ClustersPage').then(m => ({ default: m.ClustersPage })) as any)
const WeeklyPage      = lazy(() => import('./pages/WeeklyPage').then(m => ({ default: m.WeeklyPage })) as any)
const WeeklyDetailPage = lazy(() => import('./pages/WeeklyDetailPage').then(m => ({ default: m.WeeklyDetailPage })) as any)
const AboutPage        = lazy(() => import('./pages/AboutPage').then(m => ({ default: m.AboutPage })) as any)

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

// Build route tree so both / and /en/ share the same pages
function buildRoutes(prefix = '') {
  return [
    { path: `${prefix}/`, element: <HomePage /> },
    { path: `${prefix}/dashboard`, element: <AdminGate><DashboardPage /></AdminGate> },
    { path: `${prefix}/leaderboard`, element: <LeaderboardPage /> },
    { path: `${prefix}/timeline`, element: <TimelinePage /> },
    { path: `${prefix}/clusters`, element: <ClustersPage /> },
    { path: `${prefix}/weekly`, element: <WeeklyPage /> },
    { path: `${prefix}/weekly/:date`, element: <WeeklyDetailPage /> },
    { path: `${prefix}/about`, element: <AboutPage /> },
  ]
}

function AppRoutes() {
  return useRoutes([
    ...buildRoutes(''),
    ...buildRoutes('/en'),
  ])
}

function AnimatedRoutes() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <PageTransition key={location.pathname}>
        <SpaRedirect />
        <Suspense fallback={<PageFallback />}>
          <AppRoutes />
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
