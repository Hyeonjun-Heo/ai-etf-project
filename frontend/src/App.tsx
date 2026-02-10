import { Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Portfolio from './pages/Portfolio'
import Backtest from './pages/Backtest'
import Simulation from './pages/Simulation'
import Settings from './pages/Settings'
import Login from './pages/Login'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Dashboard />} />
      <Route path="/portfolio" element={<Portfolio />} />
      <Route path="/backtest" element={<Backtest />} />
      <Route path="/simulation" element={<Simulation />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
