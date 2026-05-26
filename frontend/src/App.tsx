import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useStore }           from './store/useStore'
import { NavBar }             from './components/NavBar'
import { ParticleBackground } from './components/ParticleBackground'
import { LoginPage }          from './pages/LoginPage'
import { DashboardPage }      from './pages/DashboardPage'
import { HistoryPage }        from './pages/HistoryPage'
import { FanPage }            from './pages/FanPage'
import { AlertsPage }         from './pages/AlertsPage'
import { AIChatPage }         from './pages/AIChatPage'
import { SystemFlowPage }     from './pages/SystemFlowPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  const token    = useStore((s) => s.token)
  const location = useLocation()

  return (
    <>
      {token && <ParticleBackground />}
      {token && <NavBar />}
      <Routes location={location} key={location.pathname}>
        <Route path="/login"   element={<LoginPage />} />
        <Route path="/"        element={<RequireAuth><DashboardPage /></RequireAuth>} />
        <Route path="/history" element={<RequireAuth><HistoryPage /></RequireAuth>} />
        <Route path="/fan"     element={<RequireAuth><FanPage /></RequireAuth>} />
        <Route path="/alerts"  element={<RequireAuth><AlertsPage /></RequireAuth>} />
        <Route path="/ai"      element={<RequireAuth><AIChatPage /></RequireAuth>} />
        <Route path="/system"  element={<RequireAuth><SystemFlowPage /></RequireAuth>} />
        <Route path="*"        element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}
