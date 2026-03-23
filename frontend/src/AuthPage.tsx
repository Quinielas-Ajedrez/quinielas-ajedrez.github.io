import { useState } from 'react'
import { api, setToken } from './api'

const inputStyle = {
  width: '100%',
  padding: '0.5rem 0.75rem',
  fontSize: '1rem',
  marginBottom: '0.5rem',
  border: '1px solid #ccc',
  borderRadius: 4,
  boxSizing: 'border-box' as const,
}

const buttonStyle = {
  width: '100%',
  padding: '0.5rem',
  fontSize: '1rem',
  border: '1px solid #333',
  borderRadius: 4,
  background: '#333',
  color: '#fff',
  cursor: 'pointer' as const,
}

const tabStyle = {
  padding: '0.5rem 1rem',
  border: 'none',
  background: 'transparent',
  cursor: 'pointer' as const,
  fontSize: '1rem',
}

type Tab = 'login' | 'register'

interface AuthPageProps {
  onSuccess: () => void
}

export function AuthPage({ onSuccess }: AuthPageProps) {
  const [tab, setTab] = useState<Tab>('login')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')

  const [regName, setRegName] = useState('')
  const [regUsername, setRegUsername] = useState('')
  const [regPassword, setRegPassword] = useState('')

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { access_token } = await api.auth.login(loginUsername, loginPassword)
      setToken(access_token)
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.auth.register(regName, regUsername, regPassword)
      const { access_token } = await api.auth.login(regUsername, regPassword)
      setToken(access_token)
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 360, margin: '4rem auto', fontFamily: 'system-ui' }}>
      <h1 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>Quiniela</h1>
      <p style={{ color: '#666', marginBottom: '1.5rem' }}>
        Sign in or create an account.
      </p>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <button
          type="button"
          style={{
            ...tabStyle,
            borderBottom: tab === 'login' ? '2px solid #333' : '2px solid transparent',
            fontWeight: tab === 'login' ? 600 : 400,
          }}
          onClick={() => {
            setTab('login')
            setError('')
          }}
        >
          Login
        </button>
        <button
          type="button"
          style={{
            ...tabStyle,
            borderBottom: tab === 'register' ? '2px solid #333' : '2px solid transparent',
            fontWeight: tab === 'register' ? 600 : 400,
          }}
          onClick={() => {
            setTab('register')
            setError('')
          }}
        >
          Register
        </button>
      </div>

      {tab === 'login' && (
        <form onSubmit={handleLogin}>
          <input
            type="text"
            value={loginUsername}
            onChange={(e) => setLoginUsername(e.target.value)}
            placeholder="Username"
            autoFocus
            disabled={loading}
            required
            style={inputStyle}
          />
          <input
            type="password"
            value={loginPassword}
            onChange={(e) => setLoginPassword(e.target.value)}
            placeholder="Password"
            disabled={loading}
            required
            style={inputStyle}
          />
          {error && (
            <p style={{ color: '#c00', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
              {error}
            </p>
          )}
          <button type="submit" disabled={loading} style={buttonStyle}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      )}

      {tab === 'register' && (
        <form onSubmit={handleRegister}>
          <input
            type="text"
            value={regName}
            onChange={(e) => setRegName(e.target.value)}
            placeholder="Name"
            autoFocus
            disabled={loading}
            required
            style={inputStyle}
          />
          <input
            type="text"
            value={regUsername}
            onChange={(e) => setRegUsername(e.target.value)}
            placeholder="Username"
            disabled={loading}
            required
            style={inputStyle}
          />
          <input
            type="password"
            value={regPassword}
            onChange={(e) => setRegPassword(e.target.value)}
            placeholder="Password"
            disabled={loading}
            required
            style={inputStyle}
          />
          {error && (
            <p style={{ color: '#c00', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
              {error}
            </p>
          )}
          <button type="submit" disabled={loading} style={buttonStyle}>
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>
      )}
    </div>
  )
}
