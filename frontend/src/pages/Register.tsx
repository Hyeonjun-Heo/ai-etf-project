import { type FormEvent, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import apiClient from '../api/client'
import { useAuthStore } from '../stores/authStore'
import styles from './Login.module.css'

export default function Register() {
  const navigate = useNavigate()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [usernameStatus, setUsernameStatus] = useState<'idle' | 'checking' | 'available' | 'taken'>('idle')

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  const handleCheckUsername = async () => {
    if (username.length < 3) return
    setUsernameStatus('checking')
    try {
      const { data } = await apiClient.get(`/auth/check-username?username=${encodeURIComponent(username)}`)
      setUsernameStatus(data.available ? 'available' : 'taken')
    } catch {
      setUsernameStatus('idle')
    }
  }

  const handleUsernameChange = (value: string) => {
    setUsername(value)
    setUsernameStatus('idle')
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setIsLoading(true)
    try {
      await apiClient.post('/auth/register', { username, password })
      navigate('/login', { state: { registered: true } })
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || 'Registration failed.'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <button type="button" className={styles.closeBtn} onClick={() => navigate('/')}>&#10005;</button>
        <div className={styles.icon}>&#128100;</div>
        <h1 className={styles.title}>Create Account</h1>
        <p className={styles.subtitle}>Sign up to get started</p>

        <div className={styles.inputGroup}>
          <label className={styles.label} htmlFor="username">
            Username
          </label>
          <input
            id="username"
            className={styles.input}
            type="text"
            placeholder="3-50 characters"
            value={username}
            onChange={(e) => handleUsernameChange(e.target.value)}
            autoComplete="username"
            minLength={3}
            maxLength={50}
            required
          />
          <button
            type="button"
            className={styles.checkBtn}
            onClick={handleCheckUsername}
            disabled={username.length < 3 || usernameStatus === 'checking'}
          >
            {usernameStatus === 'checking' ? 'Checking...' : 'Check availability'}
          </button>
          {usernameStatus === 'taken' && (
            <p className={styles.fieldError}>This ID is already in use.</p>
          )}
          {usernameStatus === 'available' && (
            <p className={styles.fieldSuccess}>This ID is available.</p>
          )}
        </div>

        <div className={styles.inputGroup}>
          <label className={styles.label} htmlFor="password">
            Password
          </label>
          <input
            id="password"
            className={styles.input}
            type="password"
            placeholder="At least 4 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            minLength={4}
            maxLength={100}
            required
          />
        </div>

        <div className={styles.inputGroup}>
          <label className={styles.label} htmlFor="confirmPassword">
            Confirm Password
          </label>
          <input
            id="confirmPassword"
            className={styles.input}
            type="password"
            placeholder="Re-enter password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            minLength={4}
            maxLength={100}
            required
          />
        </div>

        <button className={styles.button} type="submit" disabled={isLoading}>
          {isLoading ? 'Creating account...' : 'Sign up'}
        </button>

        {error && <p className={styles.error}>{error}</p>}

        <p className={styles.link}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  )
}
