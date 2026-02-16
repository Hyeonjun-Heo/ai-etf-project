import { type FormEvent, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import styles from './Login.module.css'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const registered = (location.state as { registered?: boolean })?.registered
  const { isAuthenticated, isLoading, error, login } = useAuthStore()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await login({ username, password })
      navigate('/', { replace: true })
    } catch {
      // error is set in the store
    }
  }

  return (
    <div className={styles.container}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <button type="button" className={styles.closeBtn} onClick={() => navigate('/')}>&#10005;</button>
        <div className={styles.icon}>&#128274;</div>
        <h1 className={styles.title}>AI ETF Investment Assistant</h1>
        <p className={styles.subtitle}>Sign in to continue</p>

        <div className={styles.inputGroup}>
          <label className={styles.label} htmlFor="username">
            Username
          </label>
          <input
            id="username"
            className={styles.input}
            type="text"
            placeholder="Enter username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </div>

        <div className={styles.inputGroup}>
          <label className={styles.label} htmlFor="password">
            Password
          </label>
          <input
            id="password"
            className={styles.input}
            type="password"
            placeholder="Enter password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>

        <button className={styles.button} type="submit" disabled={isLoading}>
          {isLoading ? 'Signing in...' : 'Sign in'}
        </button>

        {error && <p className={styles.error}>{error}</p>}
        {registered && <p className={styles.success}>Account created! Please sign in.</p>}

        <p className={styles.link}>
          Don&apos;t have an account? <Link to="/register">Sign up</Link>
        </p>
      </form>
    </div>
  )
}
