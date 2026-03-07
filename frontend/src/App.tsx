import { useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import ProtectedRoute from './components/common/ProtectedRoute'
import RightSidebar from './components/common/RightSidebar'
import TopNav from './components/common/TopNav'
import Backtest from './pages/Backtest'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import Portfolio from './pages/Portfolio'
import Settings from './pages/Settings'
import Simulation from './pages/Simulation'
import StockDetail from './pages/StockDetail'
import { useAuthStore } from './stores/authStore'

const AUTH_ROUTES = ['/login', '/register']

export default function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth)
  const { pathname } = useLocation()
  const showNav = !AUTH_ROUTES.includes(pathname)

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  return (
    <>
      {showNav && <TopNav />}
      <div style={showNav ? { paddingRight: '52px' } : undefined}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<Dashboard />} />
          <Route path="/stock/:symbol" element={<StockDetail />} />
          <Route path="/portfolio" element={<ProtectedRoute><Portfolio /></ProtectedRoute>} />
          <Route path="/backtest" element={<ProtectedRoute><Backtest /></ProtectedRoute>} />
          <Route path="/simulation" element={<ProtectedRoute><Simulation /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
      {showNav && <RightSidebar />}
    </>
  )
}
