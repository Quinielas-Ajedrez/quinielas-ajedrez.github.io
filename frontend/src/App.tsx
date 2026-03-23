import { useEffect, useState } from 'react'
import { AuthPage } from './AuthPage'
import { LeaderboardPage } from './LeaderboardPage'
import { TournamentDetail } from './TournamentDetail'
import { UsersPage } from './UsersPage'
import { api, clearToken, getToken } from './api'

const API_URL = import.meta.env.VITE_API_URL ?? '/api'

async function checkGate(): Promise<boolean> {
  const res = await fetch(`${API_URL}/auth/site-gate`, {
    credentials: 'include',
  })
  return res.ok
}

async function submitGate(password: string): Promise<boolean> {
  const res = await fetch(`${API_URL}/auth/site-gate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ password }),
  })
  return res.ok
}

function GatePage({ onPass }: { onPass: () => void }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const ok = await submitGate(password)
      if (ok) {
        onPass()
      } else {
        setError('Incorrect password')
      }
    } catch {
      setError('Connection error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 320, margin: '4rem auto', fontFamily: 'system-ui' }}>
      <h1 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>Quiniela</h1>
      <p style={{ color: '#666', marginBottom: '1.5rem' }}>
        Enter the password to continue.
      </p>
      <form onSubmit={handleSubmit}>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          autoFocus
          disabled={loading}
          style={{
            width: '100%',
            padding: '0.5rem 0.75rem',
            fontSize: '1rem',
            marginBottom: '0.5rem',
            border: '1px solid #ccc',
            borderRadius: 4,
          }}
        />
        {error && (
          <p style={{ color: '#c00', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: '0.5rem',
            fontSize: '1rem',
            border: '1px solid #333',
            borderRadius: 4,
            background: '#333',
            color: '#fff',
          }}
        >
          {loading ? 'Checking…' : 'Continue'}
        </button>
      </form>
    </div>
  )
}

type AppView =
  | 'list'
  | { type: 'tournament'; id: number }
  | { type: 'leaderboard'; tournamentId: number; tournamentName: string }
  | 'users'

function TournamentList({
  onSelect,
  onLogout,
  onManageUsers,
  user,
}: {
  onSelect: (id: number) => void
  onLogout: () => void
  onManageUsers?: () => void
  user: { name: string; username: string; is_super_admin: boolean }
}) {
  const [tournaments, setTournaments] = useState<{ id: number; name: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.tournaments
      .list()
      .then(setTournaments)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div style={{ maxWidth: 640, margin: '4rem auto', fontFamily: 'system-ui' }}>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <h1 style={{ fontSize: '1.5rem', margin: 0, flex: 1 }}>Quiniela</h1>
        {onManageUsers && user.is_super_admin && (
          <button
            type="button"
            onClick={onManageUsers}
            style={{
              padding: '0.25rem 0.5rem',
              fontSize: '0.875rem',
              border: '1px solid #999',
              borderRadius: 4,
              background: 'transparent',
              cursor: 'pointer',
            }}
          >
            Manage users
          </button>
        )}
        <button
          type="button"
          onClick={onLogout}
          style={{
            padding: '0.25rem 0.5rem',
            fontSize: '0.875rem',
            border: '1px solid #999',
            borderRadius: 4,
            background: 'transparent',
            cursor: 'pointer',
          }}
        >
          Sign out
        </button>
      </div>
      <p style={{ color: '#666', marginBottom: '1.5rem' }}>
        Welcome, {user.name}. Choose a tournament to make predictions.
      </p>

      <h2 style={{ fontSize: '1.125rem', marginBottom: '0.75rem' }}>Tournaments</h2>
      {loading && <p style={{ color: '#666' }}>Loading…</p>}
      {error && <p style={{ color: '#c00' }}>{error}</p>}
      {!loading && !error && tournaments.length === 0 && (
        <p style={{ color: '#666' }}>No tournaments yet.</p>
      )}
      {!loading && !error && tournaments.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {tournaments.map((t) => (
            <li
              key={t.id}
              role="button"
              tabIndex={0}
              onClick={() => onSelect(t.id)}
              onKeyDown={(e) => e.key === 'Enter' && onSelect(t.id)}
              style={{
                padding: '0.75rem 1rem',
                marginBottom: '0.5rem',
                border: '1px solid #e5e4e7',
                borderRadius: 4,
                background: '#fff',
                cursor: 'pointer',
              }}
            >
              {t.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function AppContent({
  user,
  onLogout,
}: {
  user: { name: string; username: string; is_admin: boolean; is_super_admin: boolean }
  onLogout: () => void
}) {
  const [view, setView] = useState<AppView>('list')

  if (view === 'list') {
    return (
      <TournamentList
        user={user}
        onLogout={onLogout}
        onSelect={(id) => setView({ type: 'tournament', id })}
        onManageUsers={() => setView('users')}
      />
    )
  }

  if (view === 'users') {
    return (
      <UsersPage
        onBack={() => setView('list')}
        onLogout={onLogout}
      />
    )
  }

  if (view.type === 'tournament') {
    return (
      <TournamentDetail
        tournamentId={view.id}
        isAdmin={user.is_admin}
        onBack={() => setView('list')}
        onLeaderboard={() => {
          api.tournaments.get(view.id).then((t) =>
            setView({ type: 'leaderboard', tournamentId: view.id, tournamentName: t.name })
          )
        }}
        onLogout={onLogout}
      />
    )
  }

  return (
    <LeaderboardPage
      tournamentId={view.tournamentId}
      tournamentName={view.tournamentName}
      onBack={() => setView({ type: 'tournament', id: view.tournamentId })}
      onLogout={onLogout}
    />
  )
}

function App() {
  const [pastGate, setPastGate] = useState<boolean | null>(null)
  const [user, setUser] = useState<{ name: string; username: string; is_admin: boolean; is_super_admin: boolean } | null>(null)
  const [authLoading, setAuthLoading] = useState(true)

  useEffect(() => {
    checkGate().then(setPastGate)
  }, [])

  useEffect(() => {
    if (!pastGate) return
    const token = getToken()
    if (!token) {
      setAuthLoading(false)
      return
    }
    api.auth
      .me()
      .then((u) => setUser(u))
      .catch(() => setUser(null))
      .finally(() => setAuthLoading(false))
  }, [pastGate])

  if (pastGate === null) {
    return (
      <div style={{ margin: '4rem auto', textAlign: 'center', fontFamily: 'system-ui' }}>
        Loading…
      </div>
    )
  }

  if (!pastGate) {
    return <GatePage onPass={() => setPastGate(true)} />
  }

  if (authLoading) {
    return (
      <div style={{ margin: '4rem auto', textAlign: 'center', fontFamily: 'system-ui' }}>
        Loading…
      </div>
    )
  }

  if (!user) {
    return <AuthPage onSuccess={() => api.auth.me().then(setUser)} />
  }

  const handleLogout = () => {
    clearToken()
    setUser(null)
  }

  return <AppContent user={user} onLogout={handleLogout} />
}

export default App
