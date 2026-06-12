import { useEffect } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import { Header, Footer } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { DashboardPage } from './pages/DashboardPage'
import { LeaderboardPage } from './pages/LeaderboardPage'
import { TimelinePage } from './pages/TimelinePage'
import { ClustersPage } from './pages/ClustersPage'
import { WeeklyPage } from './pages/WeeklyPage'

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

export default function App() {
  return (
    <div className="min-h-dvh flex flex-col">
      <Header />
      <main className="flex-1 mx-auto w-full max-w-6xl px-4 pt-20 pb-8">
        <SpaRedirect />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="/timeline" element={<TimelinePage />} />
          <Route path="/clusters" element={<ClustersPage />} />
          <Route path="/weekly" element={<WeeklyPage />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
